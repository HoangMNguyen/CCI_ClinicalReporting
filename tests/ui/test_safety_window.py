"""Safety Automation's window: one workflow page on the cci_ui kit.

The workflow itself is replaced by a stand-in here (it has its own tests in
``tests/unit/test_safety_listing.py``); these tests check what the window
asks for, runs, saves and says.
"""

import pytest
from PySide6.QtWidgets import QApplication

import safety_automation.ae_corelisting.AECoreListing as listing
from cci_ui.theme.tokens import LAYOUT
from clinical_reporting.workflow import OutputFile, UnsupportedStudyError
from safety_automation import app as safety_app

ZIP = "C:/Downloads/Core_Listings_16321_x_2026_01_31.zip"


@pytest.fixture
def window(tool_window):
    return tool_window(safety_app)


def _workbook(path, *, file_name=""):
    return OutputFile(f"{file_name} 260131_101500.xlsx", b"PK workbook")


def test_it_is_the_mockups_single_page(window):
    page = window.page

    assert window.windowTitle() == "Safety Automation"
    assert window.shell.sidebar is None
    assert window.shell.status_bar.isHidden()
    assert page.title() == "AE & DLT listing"
    assert page.run_button.text() == "Run"


def test_choosing_a_zip_suggests_a_file_name_with_its_study(window):
    window.corelisting.set_path(ZIP)

    assert window.page.file_name.placeholderText() == "16321 AE DLT"
    footnote = window.page.files.footnote_label.text()
    assert footnote.startswith("Saved as 16321 AE DLT ")


@pytest.mark.parametrize(
    ("path", "suggested"),
    [
        ("C:/Downloads/Core_Listings_12423-TmCD19-IL18_2025_08_27.zip", "12423 AE DLT"),
        ("C:/Downloads/Core_Listings_163211_x.zip", ""),  # Six digits: no study.
    ],
)
def test_the_suggested_name_reads_a_hyphenated_study_and_skips_six_digits(
    window, path, suggested
):
    window.corelisting.set_path(path)

    assert window.page.file_name.placeholderText() == suggested


def test_a_keyboard_user_starts_on_the_zips_choose_button(window):
    assert window.focusWidget() is window.corelisting.button


def test_run_says_what_to_choose_first(window):
    window.page.run_button.click()
    no_zip = window.page.banner.text()
    window.corelisting.set_path(ZIP)
    window.page.output_folder.clear()
    window.page.run_button.click()

    assert no_zip == "Choose a Corelisting ZIP first."
    assert window.page.banner.text() == "Choose an output folder first."
    assert window.page.banner.kind() == "warning"


def test_a_run_saves_the_workbook_in_the_folder(window, monkeypatch, tmp_path, settle):
    monkeypatch.setattr(listing, "run", _workbook)
    window.corelisting.set_path(ZIP)
    window.page.output_folder.set_path(str(tmp_path))
    window.page.file_name.setText("Weekly")

    window.page.run_button.click()
    settle(window.task_runner)

    saved = tmp_path / "Weekly 260131_101500.xlsx"
    assert saved.read_bytes() == b"PK workbook"
    assert window.page.banner.kind() == "success"
    assert window.page.banner.text() == f"Saved {saved.name} in {tmp_path}."
    assert not window.page.banner.action_button.isHidden()  # "Show in folder"


def test_a_problem_with_the_inputs_shows_as_a_warning(
    window, monkeypatch, tmp_path, settle
):
    def unsupported(path, *, file_name=""):
        raise UnsupportedStudyError(listing.WORKFLOW, "99999", ["16321"])

    monkeypatch.setattr(listing, "run", unsupported)
    window.corelisting.set_path(ZIP)
    window.page.output_folder.set_path(str(tmp_path))

    window.page.run_button.click()
    settle(window.task_runner)

    assert window.page.banner.kind() == "warning"
    assert "isn't set up for study 99999" in window.page.banner.text()
    assert window.page.banner.details() == ""
    assert list(tmp_path.iterdir()) == []


def test_an_unexpected_error_shows_with_its_details(
    window, monkeypatch, tmp_path, settle
):
    def broken(path, *, file_name=""):
        raise RuntimeError("boom")

    monkeypatch.setattr(listing, "run", broken)
    window.corelisting.set_path(ZIP)
    window.page.output_folder.set_path(str(tmp_path))

    window.page.run_button.click()
    settle(window.task_runner)

    assert window.page.banner.kind() == "error"
    assert window.page.banner.text() == "The workbook couldn't be made: boom"
    assert "RuntimeError" in window.page.banner.details()


@pytest.mark.parametrize("size", [safety_app.MIN_SIZE, (1920, 1001)])
def test_the_page_stays_a_centred_column_and_controls_keep_their_size(window, size):
    window.resize(*size)
    QApplication.processEvents()
    files = window.page.files
    left = files.mapTo(window, files.rect().topLeft()).x()
    run = window.page.run_button

    assert files.width() <= LAYOUT.form_max_w
    assert abs(left + files.width() / 2 - window.width() / 2) <= 12
    assert run.height() <= run.sizeHint().height() * 1.2
    assert run.width() <= run.sizeHint().width() * 1.2
