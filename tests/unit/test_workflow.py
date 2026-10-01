"""What the automation tools' workflows return and how they report problems.

(Saving the output in a folder is the desktop's part: tests/ui/test_workflow_page.py.)
"""

import io
import zipfile

import pytest

from clinical_reporting.workflow import (
    UnsupportedStudyError,
    WorkflowInputError,
    input_name,
    missing_forms_error,
    read_corelisting,
    reading_input,
)


def test_an_unsupported_study_says_which_ones_are():
    error = UnsupportedStudyError("the listing", "99999", ["16321", "03325"])

    assert str(error) == (
        "The listing isn't set up for study 99999. It supports 03325, 16321."
    )
    assert isinstance(error, WorkflowInputError)


def test_a_missing_study_number_says_it_isnt_in_the_file_name():
    error = UnsupportedStudyError("the listing", None, ["16321"])

    assert str(error) == (
        "The study number isn't in the file name, so the listing can't tell which "
        "study this is. It supports 16321."
    )


def test_missing_forms_are_named():
    error = missing_forms_error("the listing", {"EXINF", "AE"})

    assert str(error) == (
        "The Corelisting export has no AE or EXINF form, which the listing needs."
    )


class _Upload:
    name = "Core_Listings_16321_x.zip"


def test_the_input_name_comes_from_a_path_or_an_upload():
    assert input_name("C:/data/Core_Listings_16321_x.zip").endswith("16321_x.zip")
    assert input_name(_Upload()) == "Core_Listings_16321_x.zip"
    assert input_name(io.BytesIO(b"")) == ""


def test_a_corelisting_that_is_gone_or_not_a_zip_says_so(tmp_path):
    not_a_zip = tmp_path / "Core_Listings_16321_x.zip"
    not_a_zip.write_text("hello")

    with pytest.raises(WorkflowInputError, match="Couldn't find gone.zip"):
        read_corelisting(str(tmp_path / "gone.zip"))
    with pytest.raises(WorkflowInputError, match="isn't a Corelisting export"):
        read_corelisting(str(not_a_zip))


def test_a_zip_without_the_corelisting_columns_isnt_an_export():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("notes.csv", "a,b\n1,2\n")

    with pytest.raises(WorkflowInputError, match="isn't a Corelisting export"):
        read_corelisting(buffer)


def test_an_input_that_cant_be_opened_says_so(tmp_path):
    path = tmp_path / "Core_Listings_16321_x.zip"

    with pytest.raises(WorkflowInputError, match="Couldn't open Core_Listings_16321"):
        with reading_input(str(path), "a Corelisting export"):
            raise PermissionError(13, "Permission denied", str(path))


def test_a_bad_date_in_a_good_export_is_not_called_an_unreadable_file():
    rows = "Subject,Event Date,Form Status,Form ILB Status\n"
    rows += (
        "100-1-01,2026-01-01,Submitted,False\n100-1-02,UN JAN 2026,Submitted,False\n"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Core_Listings_AE.csv", rows)

    with pytest.raises(ValueError) as raised:
        read_corelisting(buffer)

    assert not isinstance(raised.value, WorkflowInputError)


def test_a_message_the_reading_raises_itself_passes_as_is():
    with pytest.raises(WorkflowInputError, match="^Pick another file.$"):
        with reading_input("x.zip", "a Corelisting export"):
            raise WorkflowInputError("Pick another file.")
