"""The Clinical Reporting window as a whole (beyond its background tasks).

Most tests use the DEMO01 sample data the preview tool shows, under the real
cci_ui theme.
"""

import sys

import pytest
import shiboken6
from PySide6.QtCore import SIGNAL, QCoreApplication, QEvent
from PySide6.QtWidgets import QMessageBox, QWidget

from cci_ui.theme.manager import ThemeMode, theme_events
from clinical_reporting import feedback
from clinical_reporting.ui.pages import preview_export
from clinical_reporting.ui.preview import PAGE_KEYS
from clinical_reporting.ui.window import Widget


@pytest.fixture
def theme(make_manager):
    manager = make_manager()
    manager.apply()
    return manager


def _theme_listeners() -> int:
    return theme_events().receivers(SIGNAL("changed()"))


def test_the_window_follows_theme_changes_until_it_is_deleted(qapp, monkeypatch):
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: raised.append(args[1]))
    # A first window lets any module-wide theme listeners connect for good.
    shiboken6.delete(Widget())
    before = _theme_listeners()

    window = Widget()
    assert _theme_listeners() > before
    shiboken6.delete(window)
    theme_events().changed.emit()

    assert _theme_listeners() == before
    assert raised == []


def test_a_theme_change_only_recolors(qapp):
    window = Widget()
    shown = feedback.warning("Cannot run:\n- Static filter 1 must have an item.")
    window.label_run_confirmation.setText(shown)
    try:
        theme_events().changed.emit()

        assert window.label_run_confirmation.text() == shown
    finally:
        shiboken6.delete(window)


@pytest.mark.parametrize("mode", [ThemeMode.LIGHT, ThemeMode.DARK])
def test_every_page_shows_and_the_preview_builds(sample_window, theme, settle, mode):
    theme.set_mode(mode)
    shell = sample_window.ui.shell

    for key in PAGE_KEYS:
        shell.set_current(key)
        settle(sample_window.task_runner)
        assert shell.page(key).isVisible()

    assert shell.current() == "preview"
    rows = sample_window.ui.tableView_preview.model().rowCount()
    assert rows > 0
    caption = shell.page("preview").subtitle_label.text()
    assert caption.startswith(f"{rows:,} rows · ")


def test_the_sample_report_exports(sample_window, settle, tmp_path):
    sample_window.output_folder_name = str(tmp_path)
    sample_window.ui.lineEdit_file_name.setText("DEMO01 sample")

    sample_window.click_run()
    settle(sample_window.task_runner)

    assert [path.suffix for path in tmp_path.iterdir()] == [".xlsx"]
    assert sample_window.ui.label_run_confirmation.kind() == "success"


def test_without_the_date_and_time_the_export_has_just_its_name(
    sample_window, settle, tmp_path
):
    sample_window.output_folder_name = str(tmp_path)
    sample_window.ui.lineEdit_file_name.setText("DEMO01 DSMB.xlsx")
    sample_window.ui.checkBox_add_date_time.setChecked(False)

    sample_window.click_run()
    settle(sample_window.task_runner)

    assert [path.name for path in tmp_path.iterdir()] == ["DEMO01 DSMB.xlsx"]
    assert sample_window.ui.label_run_confirmation.kind() == "success"


def test_exporting_over_a_file_replaces_it_once_the_user_says_so(
    sample_window, settle, monkeypatch, tmp_path
):
    asked = []
    monkeypatch.setattr(
        preview_export,
        "ask_to_replace",
        lambda parent, file_name: asked.append((parent, file_name)) or True,
    )
    old = tmp_path / "DEMO01 DSMB.xlsx"
    old.write_bytes(b"old")
    sample_window.output_folder_name = str(tmp_path)
    sample_window.ui.lineEdit_file_name.setText("DEMO01 DSMB")
    sample_window.ui.checkBox_add_date_time.setChecked(False)

    sample_window.click_run()
    settle(sample_window.task_runner)

    assert asked == [(sample_window, "DEMO01 DSMB.xlsx")]
    assert old.read_bytes()[:2] == b"PK"  # A workbook now.
    assert sample_window.ui.label_run_confirmation.kind() == "success"


@pytest.mark.parametrize(
    ("click", "replaced"), [(None, False), ("Cancel", False), ("Replace", True)]
)
def test_the_replace_prompt_keeps_the_file_unless_told_to_replace_it(
    qapp, monkeypatch, click, replaced
):
    shown = {}
    window = QWidget()

    def answer(box):
        shown.update(
            parent=box.parent(),
            icon=box.icon(),
            title=box.windowTitle(),
            text=box.text(),
            question=box.informativeText(),
            buttons=[button.text() for button in box.buttons()],
            default=box.defaultButton().text(),
            escape=box.escapeButton().text(),
        )
        for button in box.buttons():
            if button.text() == click:
                button.click()
        return 0

    monkeypatch.setattr(QMessageBox, "exec", answer)

    assert preview_export.ask_to_replace(window, "DEMO01 DSMB.xlsx") is replaced
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert window.findChildren(QMessageBox) == []  # Not left behind.
    assert shown == {
        "parent": window,
        "icon": QMessageBox.Icon.Warning,
        "title": "Export to Excel",
        "text": "DEMO01 DSMB.xlsx already exists in this folder.",
        "question": "Replace it with this export?",
        "buttons": ["Replace", "Cancel"],
        "default": "Cancel",
        "escape": "Cancel",
    }
