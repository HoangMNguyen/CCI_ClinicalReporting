"""The small tools' page and window (cci_ui.widgets.workflow_page, tool_window)."""

import errno

import pytest
import shiboken6
from PySide6.QtWidgets import QApplication, QLineEdit, QScrollArea

from cci_ui.files import save_output
from cci_ui.theme.tokens import LAYOUT
from cci_ui.tool_window import ToolWindow, show_tool
from cci_ui.widgets import workflow_page
from cci_ui.widgets.toggle import ToggleSwitch
from cci_ui.widgets.workflow_page import WorkflowPage


class _Output:
    name = "Weekly 260101_000000.xlsx"
    data = b"workbook"


@pytest.fixture
def tool(make_manager, ini_settings, settle):
    """A tool window with one workflow page, shown."""
    theme = make_manager()
    theme.apply()
    window = ToolWindow(theme, title="Test tool")
    window.page = WorkflowPage(
        "Workflow",
        inputs=[("Input", QLineEdit())],
        options=[("A switch", ToggleSwitch())],
        name_preview=lambda name: f"{name} 260101_000000.xlsx",
        expected_errors=(ValueError,),
        settings=ini_settings,
    )
    window.shell.add_page("workflow", window.page, title="Workflow")
    window.resize(680, 540)
    window.show()
    QApplication.processEvents()
    yield window
    window.close()
    settle(window.task_runner)
    shiboken6.delete(window)


def test_a_long_file_name_wraps_instead_of_widening_the_page(tool):
    tool.resize(LAYOUT.small_min_window[0], 540)  # The narrowest window.
    tool.page.file_name.setText("Weekly_DSMB_Final_Listings_For_The_Quarterly_Meeting")
    QApplication.processEvents()
    scroll = tool.page.findChild(QScrollArea)

    assert scroll.widget().width() <= scroll.viewport().width()
    assert not scroll.horizontalScrollBar().isVisible()


def test_every_row_is_kept_by_its_label(tool):
    assert list(tool.page.rows) == ["Input", "Output folder", "File name", "A switch"]
    assert tool.page.options is not None


def test_the_saved_as_line_shows_once_there_is_a_name(tool):
    footnote = tool.page.files.footnote_label
    before = footnote.text()

    tool.page.suggest_file_name("Weekly")

    assert before == ""
    assert footnote.text() == (
        "Saved as Weekly 260101_000000.xlsx (date and time of the run)"
    )
    tool.page.file_name.setText("Typed")
    assert footnote.text().startswith("Saved as Typed ")


def test_the_output_folder_used_last_time_comes_back(ini_settings, tmp_path):
    ini_settings.setValue("folders/output", str(tmp_path))
    page = WorkflowPage("Workflow", settings=ini_settings)
    ini_settings.setValue("folders/output", str(tmp_path / "gone"))
    page_after_it_went = WorkflowPage("Workflow", settings=ini_settings)
    try:
        assert page.output_folder.path() == str(tmp_path)
        assert page_after_it_went.output_folder.path() == ""
    finally:
        shiboken6.delete(page)
        shiboken6.delete(page_after_it_went)


def test_a_run_saves_what_the_job_returns(tool, tmp_path, settle):
    tool.page.output_folder.set_path(str(tmp_path))

    started = tool.page.start(tool, _Output, message="Working…")
    settle(tool.task_runner)

    assert started
    assert (tmp_path / _Output.name).read_bytes() == b"workbook"
    assert tool.page.banner.kind() == "success"


def test_a_folder_that_went_away_is_reported_before_running(tool, tmp_path):
    ran = []
    tool.page.output_folder.set_path(str(tmp_path / "gone"))

    started = tool.page.start(tool, lambda: ran.append(True), message="Working…")

    assert not started and ran == []
    assert tool.page.banner.kind() == "warning"
    assert "isn't there any more" in tool.page.banner.text()


def test_a_workbook_that_cant_be_saved_says_it_was_made(
    tool, tmp_path, monkeypatch, settle
):
    def refuse(output, folder):
        raise PermissionError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(workflow_page, "save_output", refuse)
    tool.page.output_folder.set_path(str(tmp_path))

    tool.page.start(tool, _Output, message="Working…")
    settle(tool.task_runner)

    assert tool.page.banner.kind() == "warning"
    assert tool.page.banner.text() == (
        f"The workbook was made, but it couldn't be saved in {tmp_path}: "
        "Permission denied."
    )


def test_an_expected_error_is_a_warning_and_others_are_errors(tool, tmp_path, settle):
    tool.page.output_folder.set_path(str(tmp_path))

    def expected():
        raise ValueError("Choose another file.")

    def unexpected():
        raise RuntimeError("boom")

    tool.page.start(tool, expected, message="Working…")
    settle(tool.task_runner)
    warning = (tool.page.banner.kind(), tool.page.banner.details())
    tool.page.start(tool, unexpected, message="Working…")
    settle(tool.task_runner)

    assert warning == ("warning", "")
    assert tool.page.banner.kind() == "error"
    assert "RuntimeError" in tool.page.banner.details()


def test_show_tool_opens_the_window_at_its_first_size(make_manager, ini_settings):
    window = ToolWindow(None, title="Test tool")
    try:
        show_tool(
            window,
            app_id="test-tool",
            first_size=(680, 540),
            min_size=(560, 440),
            settings=ini_settings,
        )
        QApplication.processEvents()

        assert (window.minimumWidth(), window.minimumHeight()) == (560, 440)
        assert (window.width(), window.height()) == (680, 540)
    finally:
        window.close()
        shiboken6.delete(window)


def test_saving_writes_the_bytes_under_the_name(tmp_path):
    path = save_output(_Output, tmp_path)

    assert path == tmp_path / _Output.name
    assert path.read_bytes() == b"workbook"


def test_saving_never_replaces_a_file(tmp_path):
    (tmp_path / _Output.name).write_bytes(b"old")
    (tmp_path / "Weekly 260101_000000 (2).xlsx").write_bytes(b"older")

    path = save_output(_Output, tmp_path)

    assert path.name == "Weekly 260101_000000 (3).xlsx"
    assert (tmp_path / _Output.name).read_bytes() == b"old"


def test_saving_keeps_to_the_folder_and_says_when_it_is_missing(tmp_path):
    class Sneaky:
        name = "../outside.xlsx"
        data = b"x"

    assert save_output(Sneaky, tmp_path) == tmp_path / "outside.xlsx"
    with pytest.raises(FileNotFoundError, match="isn't there any more"):
        save_output(_Output, tmp_path / "gone")
