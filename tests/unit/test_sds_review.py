"""Peer Review Automation's SDS review as a plain function (made-up SDS data)."""

import io

import pandas as pd
import pytest
from openpyxl import load_workbook

from clinical_reporting.workflow import WorkflowInputError
from peer_review_automation import sds

NONE = float("nan")


def _sds_workbook() -> bytes:
    """A made-up SDS with one item and one item group, both with problems."""
    forms = pd.DataFrame(
        {
            "Form Label": ["Demographics", "Demographics"],
            "Item Group Label": ["Subject", "Subject"],
            "Label": ["Birth date", NONE],
            "Item Name": ["BIRTH_DATE_OF_THE_SUBJECT_AS_WRITTEN", NONE],
            "External ID": ["BRTHDAT", "IG_DM_X"],
            "Required": ["No", NONE],
            "Data Type": ["Date", NONE],
            "No Future Date": ["No", NONE],
            "Codelist": [NONE, NONE],
            "Control Type": ["DateTime", NONE],
            "Item Group Name": [NONE, "IG_NS_DM"],
            "Visual Group": [NONE, "No"],
            "Header Visible": [NONE, "No"],
            "Hover Help": [NONE, NONE],
            "Mask": [NONE, NONE],
            "Derived": [NONE, NONE],
            "Unit Codelist": [NONE, NONE],
        }
    )
    codelists = pd.DataFrame(
        {
            "Name": ["CL_YN"],
            "Hidden": [False],
            "Choice Code": [1],
            "Choice Label": ["Yes"],
            "Item Group Name": ["CL_YN"],
        }
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        forms.to_excel(writer, sheet_name="Form Definitions", index=False)
        codelists.to_excel(writer, sheet_name="Codelists", index=False)
    return buffer.getvalue()


def _validation_report() -> bytes:
    return (
        pd.DataFrame(
            {
                "Category": ["Form", "Form"],
                "Section": ["DM", "DM"],
                "Error Name": ["Missing label", "Multiple dynamic rules on object"],
                "Description": ["The field has no label.", "Ignored by the review."],
                "Object": ["BRTHDAT", "BRTHDAT"],
            }
        )
        .to_csv(index=False)
        .encode()
    )


def _upload(data: bytes, name: str) -> io.BytesIO:
    upload = io.BytesIO(data)
    upload.name = name
    return upload


def _findings(output):
    sheet = load_workbook(io.BytesIO(output.data))["Form Definition Review"]
    return [row[3] for row in sheet.iter_rows(min_row=2, values_only=True)]


def test_it_lists_the_problems_it_finds():
    output = sds.run(_upload(_sds_workbook(), "STUDY01-SDS v3.xlsx"))

    assert output.name.startswith("STUDY01 Peer Review Automation Output ")
    assert _findings(output) == [
        "Item Name Length",
        "Not Required",
        "Date Field - No Future Date",
        "Item Name and External ID not matching",
        "Item Group Name and External ID mismatch",
        "Item Group does not have Visual Group selected Yes",
        "Item Group does not have Header Visible selected Yes",
    ]


def test_naming_checks_are_added_when_asked_for():
    output = sds.run(_upload(_sds_workbook(), "STUDY01-SDS.xlsx"), check_naming=True)

    assert "Wrong Item Name for Date Item" in _findings(output)


def test_the_validation_report_gets_its_own_sheet_without_the_ignored_errors():
    output = sds.run(
        _upload(_sds_workbook(), "STUDY01-SDS.xlsx"),
        validation=_upload(_validation_report(), "validation.csv"),
        file_name="Mine",
    )

    workbook = load_workbook(io.BytesIO(output.data))
    errors = [
        row[2]
        for row in workbook["Validation Review"].iter_rows(min_row=2, values_only=True)
    ]
    assert output.name.startswith("Mine ")
    assert errors == ["Missing label"]


def test_a_workbook_without_the_sds_sheets_says_what_it_needs():
    buffer = io.BytesIO()
    pd.DataFrame({"a": [1]}).to_excel(buffer, sheet_name="Other", index=False)

    with pytest.raises(
        WorkflowInputError,
        match="STUDY01-SDS.xlsx has no Form Definitions or Codelists sheet",
    ):
        sds.run(_upload(buffer.getvalue(), "STUDY01-SDS.xlsx"))


def test_a_file_that_isnt_a_workbook_says_so():
    with pytest.raises(WorkflowInputError, match="isn't an SDS workbook"):
        sds.run(_upload(b"not a workbook", "STUDY01-SDS.xlsx"))


def test_a_missing_column_is_named():
    workbook = io.BytesIO(_sds_workbook())
    sheets = pd.read_excel(workbook, sheet_name=None)
    sheets["Form Definitions"] = sheets["Form Definitions"].drop(columns="Required")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        for name, sheet in sheets.items():
            sheet.to_excel(writer, sheet_name=name, index=False)

    with pytest.raises(WorkflowInputError, match='has no "Required" column'):
        sds.run(_upload(buffer.getvalue(), "STUDY01-SDS.xlsx"))


def test_a_validation_file_that_isnt_raves_report_says_so():
    other = _upload(b"Name,Value\na,1\n", "notes.csv")

    with pytest.raises(WorkflowInputError, match="notes.csv has no Category"):
        sds.run(_upload(_sds_workbook(), "STUDY01-SDS.xlsx"), validation=other)


def test_the_suggested_name_has_no_stray_spaces():
    assert sds.default_file_name("C:/x/STUDY 01 - SDS.xlsx") == (
        "STUDY 01 Peer Review Automation Output"
    )
    assert sds.default_file_name(io.BytesIO()) == "Peer Review Automation Output"


def test_a_file_that_is_gone_says_so(tmp_path):
    with pytest.raises(WorkflowInputError, match="Couldn't find STUDY01-SDS.xlsx"):
        sds.run(str(tmp_path / "STUDY01-SDS.xlsx"))


def test_it_reads_a_path_too(tmp_path):
    path = tmp_path / "STUDY01-SDS.xlsx"
    path.write_bytes(_sds_workbook())

    assert sds.run(str(path)).data[:2] == b"PK"
