"""CCI Automation's workflows as plain functions (made-up data)."""

import importlib.util
import io
import logging
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

import cci_automation.dsmb.DSMB as dsmb
import cci_automation.enrollment_log.EnrollmentLog as enrollment
import cci_automation.format_tools.change_type as format_tool
from clinical_reporting.workflow import UnsupportedStudyError, WorkflowInputError

SUBJECT = "100-03325-01"


def _form(columns):
    df = pd.DataFrame(columns)
    df["Form Status"] = "Submitted"
    df["Form ILB Status"] = False
    return df


def _export_03325(dm_status: str = "Submitted") -> io.BytesIO:
    """A made-up 03325 export with the forms its enrollment log reads."""
    forms = {
        "DM": _form(
            {
                "Subject": [SUBJECT],
                "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": ["Race"],
                "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": [
                    "Ethnicity"
                ],
                "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": [
                    "Sex"
                ],
                "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": ["Legal"],
                "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": ["2000-01-01"],
                "Main Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)": ["2025-01-01"],
            }
        ),
        "EXCHEMO": _form(
            {
                "Subject": [SUBJECT, SUBJECT],
                "Event Group Label": ["Cycle 1 Day 1", "Cycle 1 Day 3-5"],
                "Event Date": ["2026-01-20", "2026-01-22"],
                "Was rituximab administered? "
                "(IG_NS_NA_EXCHMO2.CL_NS_NH_RITUADM_CL_YS_YNNRPP)": ["Yes", ""],
                "Rituximab Administration Date (IG_NS_NA_EXCHMO2.DT_NS_NH_RITUADMDT)": [
                    "2026-01-19",
                    "",
                ],
                **{
                    f"{drug} Dose #{n} Administration Date "
                    f"(IG_NS_NA_EXCHMO{group}.DT_NS_NH_{code}D{n}DT)": [
                        "",
                        "2026-01-21" if n == 1 else "",
                    ]
                    for drug, group, code in (
                        ("Fludarabine", 3, "FLUD"),
                        ("Cyclophosphamide", 4, "CYCL"),
                    )
                    for n in (1, 2, 3)
                },
            }
        ),
        "EXINF2": _form(
            {
                "Subject": [SUBJECT],
                "Event Group Label": ["Cycle 1 Day 8"],
                "Event Date": ["2026-01-28"],
                "Cycle Number (IG_NS_NA_EXINF21.CL_YS_NH_CNUM_cl_NS_CNUM)": ["Cycle 1"],
                "Were CART-EGFR-IL13Ra2 cells administered? "
                "(IG_NS_NA_EXINF21.CL_NS_NH_INFADMIN2_cl_YS_YN1)": ["Yes"],
                "Cell Product Administration Date (IG_NS_NA_EXINF21.DT_NS_NH_INFDAT)": [
                    "2026-01-27"
                ],
            }
        ),
    }
    forms["DM"]["Form Status"] = dm_status
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, form in forms.items():
            archive.writestr(f"Core_Listings_{name}.csv", form.to_csv(index=False))
    buffer.seek(0)
    buffer.name = "Core_Listings_03325_x_2026_01_31.zip"
    return buffer


def test_the_enrollment_log_is_a_dated_workbook_of_the_study():
    output = enrollment.run(_export_03325(), study="03325")

    assert output.name.startswith("03325 Enrollment Log ")
    sheet = load_workbook(io.BytesIO(output.data))["Enrollment Log 03325"]
    assert sheet.max_row == 2  # the header and the one subject


def _column(output, name):
    sheet = load_workbook(io.BytesIO(output.data)).active
    headers = [cell.value for cell in sheet[1]]
    return [
        row[headers.index(name)] for row in sheet.iter_rows(min_row=2, values_only=True)
    ]


def test_a_cut_off_date_leaves_later_rows_out():
    infusion = "Initial CAR T cell Administration Date"

    everything = enrollment.run(_export_03325(), study="03325")
    before_infusion = enrollment.run(
        _export_03325(), study="03325", cut_off_date=date(2026, 1, 25)
    )

    assert _column(everything, infusion)[0]  # The infusion visit, 2026-01-28.
    assert not _column(before_infusion, infusion)[0]


def test_a_zip_named_for_another_study_is_refused():
    with pytest.raises(WorkflowInputError, match="is an export of study 03325"):
        enrollment.run(_export_03325(), study="15420")


@pytest.mark.parametrize(
    ("workflow", "study", "dm_status"),
    # 11823's DSMB module builds its report from this made-up export.
    [(enrollment, "03325", "Submitted"), (dsmb, "11823", "Draft")],
)
def test_an_export_named_with_a_description_after_its_study_is_checked_too(
    workflow, study, dm_status
):
    export = _renamed(_export_03325(dm_status=dm_status), "12423-TmCD19-IL18")

    with pytest.raises(WorkflowInputError, match="is an export of study 12423"):
        workflow.run(export, study=study)


@pytest.mark.parametrize(
    ("workflow", "module"),
    [(enrollment, "EnrollmentLog"), (dsmb, "DSMB")],
)
def test_every_listed_study_has_its_module(workflow, module):
    package = workflow.__name__.rsplit(".", 1)[0]

    missing = [
        study
        for study in workflow.SUPPORTED_STUDIES
        if importlib.util.find_spec(f"{package}.{module}{study}") is None
    ]

    assert missing == []


@pytest.mark.parametrize("workflow", [enrollment, dsmb])
def test_a_study_without_the_report_says_which_have_one(workflow):
    with pytest.raises(UnsupportedStudyError, match="isn't set up for study 99999"):
        workflow.run(_export_03325(), study="99999")


def test_the_dsmb_report_comes_back_as_bytes_from_a_temporary_folder(monkeypatch):
    folders = []

    def write(self, output_dir, output_file_name):
        folders.append(Path(output_dir))
        (Path(output_dir) / f"{output_file_name}.xlsx").write_bytes(b"PK report")

    monkeypatch.setattr(dsmb.DSMB, "write", write)

    output = dsmb.run(_export_03325(), study="03325", file_name="Board")

    assert output.data == b"PK report"
    assert output.name.startswith("Board ")
    assert not folders[0].exists()  # The temporary folder is gone.


def test_a_csv_is_formatted_into_a_workbook():
    source = io.BytesIO(
        b"Lab Range,Visit Date,Visit Date.1\n10-20,03/05/2026,04/06/2026\n"
    )
    source.name = "labs.csv"

    output = format_tool.run(source)

    sheet = load_workbook(io.BytesIO(output.data))["Sheet1"]
    assert output.name.startswith("labs_formatted ")
    assert [cell.value for cell in sheet[1]] == [
        "Lab Range",
        "Visit Date",
        "Visit Date",
    ]
    assert [cell.value for cell in sheet[2]] == ["10-20", "3/5/2026", "4/6/2026"]


def test_the_format_tool_reads_csv_and_xlsx_only():
    with pytest.raises(WorkflowInputError, match="isn't a CSV or Excel"):
        source = io.BytesIO(b"x")
        source.name = "notes.txt"
        format_tool.run(source)


def test_a_file_that_is_gone_says_so(tmp_path):
    with pytest.raises(WorkflowInputError, match="Couldn't find labs.csv"):
        format_tool.run(str(tmp_path / "labs.csv"))


@pytest.mark.parametrize("study", ["03325", "10325", "16321"])
def test_a_dsmb_module_that_writes_nothing_says_why(study):
    """These modules report only subjects with a submitted DM form."""
    export = _renamed(_export_03325(dm_status="Draft"), study)
    with pytest.raises(WorkflowInputError, match="no submitted Demographics"):
        dsmb.run(export, study=study)


def test_a_dsmb_export_without_demographics_says_so():
    export = _export_03325()
    with zipfile.ZipFile(export) as archive:
        kept = {
            name: archive.read(name) for name in archive.namelist() if "DM" not in name
        }
    without_dm = io.BytesIO()
    with zipfile.ZipFile(without_dm, "w") as archive:
        for name, data in kept.items():
            archive.writestr(name, data)
    without_dm.seek(0)
    without_dm.name = export.name

    with pytest.raises(WorkflowInputError, match="has no DM form"):
        dsmb.run(without_dm, study="03325")


def test_a_failing_dsmb_module_leaves_no_temporary_folder(monkeypatch):
    folders = []

    def fail(self, data, study_name):
        folders.append(Path(self.output_dir))
        (Path(self.output_dir) / "half.xlsx").write_bytes(b"PK")
        raise RuntimeError("boom")

    monkeypatch.setattr(dsmb.DSMB, "data_analysis", fail)

    with pytest.raises(RuntimeError, match="boom"):
        dsmb.run(_export_03325(), study="03325")
    assert not folders[0].exists()


def _csv(data: bytes, name: str = "labs.csv") -> io.BytesIO:
    source = io.BytesIO(data)
    source.name = name
    return source


def test_a_csv_saved_by_excel_on_windows_is_read():
    source = _csv("Lab,Visit Date\nCaf\u00e9,03/05/2026\n".encode("cp1252"))

    sheet = load_workbook(io.BytesIO(format_tool.run(source).data))["Sheet1"]

    assert [cell.value for cell in sheet[2]] == ["Caf\u00e9", "3/5/2026"]


def test_an_empty_csv_says_so():
    with pytest.raises(WorkflowInputError, match="isn't a CSV file"):
        format_tool.run(_csv(b""))


def test_only_pandas_suffixes_are_dropped_from_column_names():
    source = _csv(b"pH 7.4,Visit,Visit.1\n7,a,b\n")

    sheet = load_workbook(io.BytesIO(format_tool.run(source).data))["Sheet1"]

    assert [cell.value for cell in sheet[1]] == ["pH 7.4", "Visit", "Visit"]


def test_a_date_column_the_format_tool_cant_convert_is_logged_without_its_values(
    caplog, capsys
):
    # Mixed UTC offsets make pandas raise even with errors="coerce".
    source = _csv(b"Visit Date\n01/05/2024 08:00+01:00\n01/06/2024 09:00+05:00\n")

    with caplog.at_level(logging.WARNING, logger="cci_automation"):
        format_tool.run(source)

    assert [record.getMessage() for record in caplog.records] == [
        "Could not process date column 'Visit Date' (ValueError)"
    ]
    assert "2024" not in caplog.text
    assert capsys.readouterr().out == ""


def _renamed(export: io.BytesIO, study: str) -> io.BytesIO:
    export.name = f"Core_Listings_{study}_x_2026_01_31.zip"
    return export


@pytest.mark.parametrize("study", ["03821", "11823"])
def test_a_real_dsmb_module_hands_back_its_workbook(study):
    output = dsmb.run(_renamed(_export_03325(dm_status="Draft"), study), study=study)

    assert output.name.startswith(f"{study} DSMB Report ")
    assert load_workbook(io.BytesIO(output.data)).sheetnames


def test_a_zip_named_for_a_study_without_a_dsmb_report_says_so():
    export = _renamed(_export_03325(), "30425")

    with pytest.raises(UnsupportedStudyError, match="isn't set up for study 30425"):
        dsmb.run(export, study="03325")


def test_a_file_named_xlsx_that_isnt_a_workbook_says_so():
    with pytest.raises(WorkflowInputError, match="isn't an Excel workbook"):
        format_tool.run(_csv(b"hello", "labs.xlsx"))
