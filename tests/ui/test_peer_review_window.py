"""Peer Review Automation's window: one workflow page on the cci_ui kit.

The review itself is replaced by a stand-in here (it has its own tests in
``tests/unit/test_sds_review.py``); these tests check what the window asks
for and what it hands the review.
"""

import pytest
from PySide6.QtWidgets import QApplication

from clinical_reporting.workflow import OutputFile
from peer_review_automation import app as review_app
from peer_review_automation import sds

SDS = "C:/Downloads/STUDY01-SDS v3.xlsx"


@pytest.fixture
def window(tool_window):
    return tool_window(review_app)


def test_it_is_one_page_with_the_naming_check_as_an_option(window):
    assert window.windowTitle() == "Peer Review Automation"
    assert window.shell.sidebar is None
    assert window.page.title() == "SDS peer review"
    assert list(window.page.rows) == [
        "SDS workbook",
        "Validation report",
        "Output folder",
        "File name",
        "Check naming conventions",
    ]
    assert window.focusWidget() is window.sds_file.button


def test_choosing_the_sds_suggests_a_file_name(window):
    window.sds_file.set_path(SDS)

    assert window.page.file_name.placeholderText() == (
        "STUDY01 Peer Review Automation Output"
    )


def test_run_asks_for_the_sds_first(window):
    window.page.run_button.click()

    assert window.page.banner.text() == "Choose the SDS workbook first."


@pytest.mark.parametrize("with_validation", [False, True])
def test_a_run_hands_the_review_what_was_chosen(
    window, monkeypatch, tmp_path, settle, with_validation
):
    calls = []

    def review(path, **options):
        calls.append((path, options))
        return OutputFile("Review 260101_000000.xlsx", b"PK review")

    monkeypatch.setattr(sds, "run", review)
    window.sds_file.set_path(SDS)
    if with_validation:
        window.validation_file.set_path("C:/Downloads/validation.csv")
    window.check_naming.setChecked(True)
    window.page.output_folder.set_path(str(tmp_path))

    window.page.run_button.click()
    settle(window.task_runner)

    assert calls == [
        (
            SDS,
            {
                "validation": "C:/Downloads/validation.csv"
                if with_validation
                else None,
                "check_naming": True,
                "file_name": "STUDY01 Peer Review Automation Output",
            },
        )
    ]
    assert (tmp_path / "Review 260101_000000.xlsx").read_bytes() == b"PK review"
    assert window.page.banner.kind() == "success"


def test_the_first_size_fits_the_page_and_a_message(
    window, monkeypatch, tmp_path, settle
):
    """Even a three-line message: the saved file in a long, deep folder."""
    folder = tmp_path / "Dropbox" / "Current Work" / "Studies" / "STUDY01" / "Reviews"
    folder.mkdir(parents=True)
    monkeypatch.setattr(
        sds,
        "run",
        lambda path, **options: OutputFile(
            "STUDY01 Peer Review Automation Output 260101_000000.xlsx", b"PK"
        ),
    )
    window.sds_file.set_path(SDS)
    window.page.output_folder.set_path(str(folder))
    window.page.run_button.click()
    settle(window.task_runner)
    QApplication.processEvents()
    QApplication.processEvents()

    assert window.page.scroll_area.verticalScrollBar().maximum() == 0
