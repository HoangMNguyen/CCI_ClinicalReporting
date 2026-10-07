"""CCI Automation's window: a sidebar with its three workflow pages.

The workflows are replaced by stand-ins here (they have their own tests in
``tests/unit/test_cci_workflows.py``); these tests check what the window asks
for and what it hands them.
"""

from datetime import date

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

import cci_automation.dsmb.DSMB as dsmb
import cci_automation.enrollment_log.EnrollmentLog as enrollment
import cci_automation.format_tools.change_type as format_tool
from cci_automation import app as cci_app
from clinical_reporting.workflow import OutputFile

ZIP = "C:/Downloads/Core_Listings_15420_x_2026_01_31.zip"


@pytest.fixture
def window(tool_window):
    return tool_window(cci_app)


def _recorder(calls, name="Report 260101_000000.xlsx"):
    def run(source, **options):
        calls.append((source, options))
        return OutputFile(name, b"PK workbook")

    return run


def test_the_three_workflows_are_pages_in_the_sidebar(window):
    shell = window.shell

    assert window.windowTitle() == "CCI Automation"
    assert shell.sidebar is not None
    assert [
        shell.page(key).title()
        for key in (cci_app.ENROLLMENT, cci_app.DSMB, cci_app.FORMAT)
    ] == [
        "Enrollment log",
        "DSMB report",
        "Format tools",
    ]
    assert shell.current() == cci_app.ENROLLMENT
    assert window.focusWidget() is window.enrollment.corelisting.button


def test_a_study_page_lists_its_studies_and_takes_one_from_the_zip(window):
    page = window.dsmb
    studies = [page.study.itemText(i) for i in range(page.study.count())]

    page.corelisting.set_path(ZIP)

    assert studies == list(dsmb.SUPPORTED_STUDIES)
    assert page.study.currentText() == "15420"
    assert page.file_name.placeholderText() == "15420 DSMB Report"


def test_the_cut_off_date_shows_and_counts_only_when_switched_on(window):
    page = window.enrollment
    row = page.rows["Cut-off date"]
    hidden = row.isHidden()

    page.use_cut_off.setChecked(True)
    page.cut_off.setDate(QDate(2026, 1, 31))

    assert hidden and not row.isHidden()
    assert page.cut_off_date() == date(2026, 1, 31)
    page.use_cut_off.setChecked(False)
    assert page.cut_off_date() is None


@pytest.mark.parametrize(
    ("page_name", "module", "run"),
    [
        ("enrollment", enrollment, "run_enrollment_log"),
        ("dsmb", dsmb, "run_dsmb_report"),
    ],
)
def test_a_study_report_gets_what_was_chosen(
    window, monkeypatch, tmp_path, settle, page_name, module, run
):
    calls = []
    monkeypatch.setattr(module, "run", _recorder(calls))
    page = getattr(window, page_name)
    page.corelisting.set_path(ZIP)
    page.use_cut_off.setChecked(True)
    page.cut_off.setDate(QDate(2026, 1, 31))
    page.output_folder.set_path(str(tmp_path))

    page.run_button.click()
    settle(window.task_runner)

    assert calls == [
        (
            ZIP,
            {
                "study": "15420",
                "cut_off_date": date(2026, 1, 31),
                "file_name": module.default_file_name("15420"),
            },
        )
    ]
    assert page.banner.kind() == "success"
    assert (tmp_path / "Report 260101_000000.xlsx").exists()


def test_the_format_tool_gets_the_file_and_suggests_its_name(
    window, monkeypatch, tmp_path, settle
):
    calls = []
    monkeypatch.setattr(format_tool, "run", _recorder(calls))
    window.format_source.set_path("C:/Downloads/labs.csv")
    window.format.output_folder.set_path(str(tmp_path))

    window.format.run_button.click()
    settle(window.task_runner)

    assert window.format.file_name.placeholderText() == "labs_formatted"
    assert calls == [("C:/Downloads/labs.csv", {"file_name": "labs_formatted"})]


def test_run_says_what_to_choose_first(window):
    window.enrollment.run_button.click()
    window.format.run_button.click()

    assert window.enrollment.banner.text() == "Choose a Corelisting ZIP first."
    assert window.format.banner.text() == "Choose a CSV or Excel file first."


def test_a_zip_named_for_an_unlisted_study_is_flagged(window):
    page = window.dsmb
    before = page.study.currentText()

    page.corelisting.set_path("C:/Downloads/Core_Listings_30425_x.zip")

    assert page.study.currentText() == before
    assert page.banner.kind() == "warning"
    assert "isn't set up for study 30425" in page.banner.text()
    page.corelisting.set_path("C:/Downloads/export.zip")  # Names no study.
    assert page.banner.text() == ""


def test_run_with_a_zip_but_no_folder_asks_for_one(window):
    """The old window crashed here (its output folder was never set)."""
    window.enrollment.corelisting.set_path(ZIP)
    window.enrollment.output_folder.clear()

    window.enrollment.run_button.click()

    assert window.enrollment.banner.text() == "Choose an output folder first."


def test_the_first_size_fits_a_page_with_the_cut_off_and_a_message(window):
    page = window.enrollment
    page.use_cut_off.setChecked(True)
    page.warn(
        "The Corelisting export has no submitted Demographics (DM) forms up to "
        "the cut-off date, so there's no DSMB report to make."
    )
    QApplication.processEvents()
    QApplication.processEvents()

    assert page.scroll_area.verticalScrollBar().maximum() == 0
