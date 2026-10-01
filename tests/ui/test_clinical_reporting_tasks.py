"""The Clinical Reporting window runs its slow work in the background.

These drive the real window with synthetic data: the ZIP reader is replaced
by one that waits for the test's go-ahead, so the tests can check what the
window does while the work is still running. The window is shown and
active, so focus changes (which make the cut-off date field commit and
start a reload) happen as they do for a user. Every status message the
window shows is recorded, and each must carry a ``feedback`` kind.
"""

import datetime
import threading

import pandas as pd
import pytest
import shiboken6
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from cci_ui.widgets.shell import SIDEBAR_SHORTCUT
from clinical_reporting import feedback
from clinical_reporting.ui import run_save_tab, settings_tab
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
def window(qapp, monkeypatch, tmp_path):
    zip_path = str(tmp_path / ZIP_NAME)
    monkeypatch.setattr(
        settings_tab.QFileDialog,
        "getOpenFileName",
        lambda *_args: (zip_path, "Zip files (*.zip)"),
    )
    widget = Widget()
    widget.shown_messages = []
    show_message = widget._set_label_text

    def record(label, message):
        widget.shown_messages.append(message)
        show_message(label, message)

    # Recorded rather than asserted here: a failure inside a Qt callback
    # would only reach sys.excepthook.
    widget._set_label_text = record
    widget.show()
    widget.activateWindow()
    QApplication.processEvents()
    yield widget
    widget.close()
    widget.task_runner.wait(5000)
    untagged = [
        message
        for message in widget.shown_messages
        if message and not isinstance(message, feedback.Message)
    ]
    # Deleted now: with no event loop running, deleteLater would never run and
    # the window would keep listening to the global theme signal.
    shiboken6.delete(widget)
    assert untagged == []


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
    assert window.ui.pathPicker_input_file.path().endswith(ZIP_NAME)
    assert window.ui.listWidget_form_available.count() == 2


def test_an_unreadable_zip_keeps_the_loaded_report(opened, reader, settle):
    loaded = opened.report
    reader.error = OSError("File is not a zip file")

    opened.click_input_file()
    settle(opened.task_runner)

    problem = f"Could not read {ZIP_NAME}: File is not a zip file"
    outcome = "Nothing was loaded; the report is unchanged."
    assert opened.report is loaded
    assert opened.ui.banner_input_file.text() == f"{problem}\n{outcome}"
    assert opened.ui.banner_input_file.kind() == "error"
    assert opened.ui.pathPicker_input_file.path().endswith(ZIP_NAME)
    status_bar = opened.ui.shell.status_bar
    assert status_bar.message() == f"{problem}. {outcome}"
    assert status_bar.message_kind() == "error"


def test_a_failed_reload_is_reported_once_not_retried_in_a_loop(opened, reader, settle):
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
    reported = [m for m in opened.shown_messages if "was not applied" in (m or "")]
    assert len(reported) == 1 and reported[0].kind == "error"


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


def test_keys_do_nothing_while_a_page_change_reloads_the_data(opened, reader, settle):
    _edit_the_date(opened)
    reader.go.clear()
    shell = opened.ui.shell

    # Hiding the Source data page commits the date, which starts the reload.
    QTest.mouseClick(shell.sidebar.item("additional"), Qt.MouseButton.LeftButton)
    assert opened.task_runner.busy and shell.current() == "additional"
    focused = QApplication.focusWidget()
    collapsed = shell.is_sidebar_collapsed()
    QTest.keyClick(focused, Qt.Key.Key_Tab)
    QTest.keyClick(focused, Qt.Key.Key_Down)
    QTest.keySequence(focused, QKeySequence(SIDEBAR_SHORTCUT))
    QTest.keyClick(focused, Qt.Key.Key_PageDown, Qt.KeyboardModifier.ControlModifier)

    assert shell.current() == "additional" and QApplication.focusWidget() is focused
    assert shell.is_sidebar_collapsed() is collapsed
    reader.go.set()
    settle(opened.task_runner)


def test_the_source_step_stays_done_after_a_cut_off_reload(opened):
    QApplication.processEvents()
    item = opened.ui.shell.sidebar.item("source")

    assert opened._applied_cut_off_date is not None  # The fixture reloaded.
    assert item.state().value == "done" and item.toolTip().endswith(ZIP_NAME)


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


def test_a_preview_that_fails_shows_the_error_with_its_traceback(
    opened, monkeypatch, settle
):
    def broken_build(_report):
        raise RuntimeError("boom")

    monkeypatch.setattr(run_save_tab, "build_report", broken_build)
    _select_dm_age(opened)

    opened.preview_report()
    settle(opened.task_runner)

    shown = opened.shown_messages[-1]
    assert shown == "Error generating preview: boom"
    assert shown.kind == "error" and "RuntimeError: boom" in shown.details


def test_a_date_picked_in_the_calendar_applies_the_cut_off(opened, reader, settle):
    calendar = opened.ui.cutoff_dateEdit.calendarWidget()

    calendar.clicked.emit(QDate(2020, 5, 5))  # As a click on a day in the popup.
    settle(opened.task_runner)

    assert reader.calls[-1][1] == datetime.date(2020, 5, 5)
    assert opened._applied_cut_off_date == datetime.date(2020, 5, 5)
