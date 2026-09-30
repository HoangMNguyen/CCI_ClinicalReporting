"""The Clinical Reporting window runs its slow work in the background.

These drive the real window with synthetic data: the ZIP reader is replaced
by one that waits for the test's go-ahead, so the tests can check what the
window does while the work is still running. The window is shown and
active, so focus changes (which make the cut-off date field commit and
start a reload) happen as they do for a user.
"""

import datetime
import threading

import pandas as pd
import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from clinical_reporting.ui import settings_tab
from clinical_reporting.ui.window import Widget

ZIP_NAME = "Core_Listings_DEMO01_260930.zip"


def _forms():
    return {
        "DM": pd.DataFrame({"Subject": ["001", "002"], "Age": [54, 61]}),
        "AE": pd.DataFrame({"Subject": ["001", "002"], "Term": ["Nausea", "Fatigue"]}),
    }


class _GatedReader:
    """Stands in for the ZIP reader; each read waits until the test allows it."""

    def __init__(self):
        self.go = threading.Event()
        self.calls = []
        self.error = None

    def __call__(self, path, cut_off_date=None):
        self.calls.append((path, cut_off_date))
        assert self.go.wait(5)
        if self.error is not None:
            raise self.error
        return _forms()


@pytest.fixture
def reader(monkeypatch):
    gated = _GatedReader()
    monkeypatch.setattr(settings_tab, "read_data_dict_zip_corelisting", gated)
    return gated


@pytest.fixture
def warnings(monkeypatch):
    """Warning dialogs shown, as (title, text), instead of opening them."""
    shown = []
    monkeypatch.setattr(
        settings_tab.QMessageBox,
        "warning",
        lambda _parent, title, text: shown.append((title, text)),
    )
    return shown


@pytest.fixture
def window(qapp, monkeypatch, tmp_path):
    zip_path = str(tmp_path / ZIP_NAME)
    monkeypatch.setattr(
        settings_tab.QFileDialog,
        "getOpenFileName",
        lambda *_args: (zip_path, "Zip files (*.zip)"),
    )
    widget = Widget()
    widget.show()
    widget.activateWindow()
    QApplication.processEvents()
    yield widget
    widget.close()
    widget.task_runner.wait(5000)
    widget.deleteLater()


@pytest.fixture
def opened(window, reader, settle):
    """The window with the synthetic ZIP loaded and a cut-off applied."""
    reader.go.set()
    window.click_input_file()
    settle(window.task_runner)
    window.ui.cutoff_checkBox.setChecked(True)
    settle(window.task_runner)
    return window


def _select_dm_age(window):
    window.report.add_selected_form("DM")
    window.report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    window.update_all_ui()  # Fills in the join order, as picking in the lists does.


def _edit_the_date(window):
    """Focus the cut-off field and move its date on a day, without committing."""
    date_edit = window.ui.cutoff_dateEdit
    date_edit.setDate(QDate(2024, 6, 1))
    date_edit.setFocus()
    date_edit.setCurrentSection(date_edit.Section.DaySection)
    QTest.keyClick(date_edit, Qt.Key.Key_Up)
    return datetime.date(2024, 6, 2)


def test_reading_the_zip_blocks_the_window_until_it_is_done(window, reader, settle):
    window.click_input_file()

    assert window.task_runner.busy
    assert window.report.data in (None, {})  # Nothing changes until the read ends.

    reader.go.set()
    settle(window.task_runner)

    assert set(window.report.available_forms) == {"DM", "AE"}
    assert window.report.study_name == "DEMO01"
    assert window.ui.label_input_file.text().startswith("Input path: ")
    assert window.ui.listWidget_form_available.count() == 2


def test_an_unreadable_zip_keeps_the_loaded_report(opened, reader, warnings, settle):
    loaded = opened.report
    reader.error = OSError("File is not a zip file")

    opened.click_input_file()
    settle(opened.task_runner)

    problem = f"Could not read {ZIP_NAME}: File is not a zip file"
    assert opened.report is loaded
    assert opened.ui.label_input_file.text().endswith(problem)
    assert warnings == [
        (
            "Could not read the Corelisting ZIP",
            f"{problem}\n\nNothing was loaded; the report is unchanged.",
        )
    ]


def test_a_failed_reload_is_reported_once_not_retried_in_a_loop(
    opened, reader, warnings, settle
):
    reader.error = OSError("The file is locked")
    reads_before = len(reader.calls)
    applied = opened._applied_cut_off_date

    _edit_the_date(opened)
    QTest.keyClick(opened.ui.cutoff_dateEdit, Qt.Key.Key_Return)
    settle(opened.task_runner)
    QTest.keyClick(opened.ui.cutoff_dateEdit, Qt.Key.Key_Return)  # Same date again.
    settle(opened.task_runner)

    assert len(reader.calls) == reads_before + 1
    assert opened._applied_cut_off_date == applied
    assert len(warnings) == 1 and "cut-off date was not applied" in warnings[0][1]


def test_remove_input_clicked_as_the_date_commits_leaves_a_consistent_window(
    opened, reader, settle
):
    new_date = _edit_the_date(opened)
    reader.go.clear()

    # The press commits the date (starting a reload) before reaching the button.
    QTest.mouseClick(opened.ui.pushButton_remove_input, Qt.MouseButton.LeftButton)
    assert opened.task_runner.busy
    reader.go.set()
    settle(opened.task_runner)

    assert opened._input_file_path is not None
    assert opened._applied_cut_off_date == new_date
    assert set(opened.report.data) == {"DM", "AE"}
    assert opened.ui.pushButton_remove_input.isEnabled()

    QTest.mouseClick(opened.ui.pushButton_remove_input, Qt.MouseButton.LeftButton)

    assert opened._input_file_path is None and opened.report.data == {}


def test_keys_do_nothing_while_a_tab_change_reloads_the_data(opened, reader, settle):
    _edit_the_date(opened)
    reader.go.clear()
    tabs = opened.ui.tabWidget
    tab_bar = tabs.tabBar()

    # Hiding the settings page commits the date, which starts the reload.
    QTest.mouseClick(
        tab_bar, Qt.MouseButton.LeftButton, pos=tab_bar.tabRect(1).center()
    )
    assert opened.task_runner.busy and tabs.currentIndex() == 1
    focused = QApplication.focusWidget()
    QTest.keyClick(focused, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(focused, Qt.Key.Key_Tab)

    assert tabs.currentIndex() == 1 and QApplication.focusWidget() is focused
    reader.go.set()
    settle(opened.task_runner)


def test_preview_asked_for_while_busy_runs_once_the_work_is_done(
    opened, reader, settle
):
    _select_dm_age(opened)
    reader.go.clear()
    # A cut-off change is being read when the preview is asked for.
    opened.ui.cutoff_checkBox.setChecked(False)
    assert opened.task_runner.busy

    opened.preview_report()
    assert opened.ui.tableView_preview.model() is None

    reader.go.set()
    settle(opened.task_runner)

    assert reader.calls[-1][1] is None  # The cut-off change was applied first.
    assert opened.ui.tableView_preview.model().rowCount() == 2
    assert opened.label_run_confirmation.text().startswith("Preview generated")


def test_export_writes_the_file_in_the_background(opened, settle, tmp_path):
    _select_dm_age(opened)
    opened.output_folder_name = str(tmp_path)
    opened.ui.lineEdit_file_name.setText("DEMO01 report")

    opened.click_run()
    settle(opened.task_runner)

    assert [
        path.name.startswith("DEMO01 report ") for path in tmp_path.glob("*.xlsx")
    ] == [True]
    assert opened.label_run_confirmation.text().startswith("Report saved successfully")


def test_closing_during_a_reload_ignores_it_and_starts_nothing(opened, reader):
    _edit_the_date(opened)
    reader.go.clear()
    reads_before = len(reader.calls)
    applied = opened._applied_cut_off_date
    QTest.keyClick(opened.ui.cutoff_dateEdit, Qt.Key.Key_Return)

    opened.close()  # Hiding also takes the focus from the date field.
    reader.go.set()
    assert opened.task_runner.wait(5000)
    QTest.qWait(50)

    assert len(reader.calls) == reads_before + 1  # Only the Enter's reload.
    assert opened._applied_cut_off_date == applied
    assert not opened.task_runner.busy
