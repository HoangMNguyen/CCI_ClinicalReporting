"""Safety Automation's AE & DLT listing as a plain function (made-up data)."""

import io
import zipfile

import pandas as pd
import pytest
from openpyxl import load_workbook

from clinical_reporting.workflow import UnsupportedStudyError, WorkflowInputError
from safety_automation.ae_corelisting import AECoreListing as listing

AE_16321 = [
    "Subject",
    "AE or SAE? (ig_AE2.AESEV)",
    "T-cell Attribution (ig_AE1.AEREL)",
    "T-cell Expectedness (ig_AE1.AETRTINTP)",
    "Specify Other Attribution (ig_AE1.AERELSPOTH)",
    "Other Attribution (ig_AE1.AERELOTH)",
    "Other Expectedness (ig_AE1.AETRTINTPOTH)",
    "CTCAE Category (ig_AE1.AECAT)",
    "Derived Toxicity (ig_AE1.AETOXDV)",
    "Toxicity (ig_AE1.AETOX)",
    "Grade (ig_AE1.AETOXGR)",
    "Start Date (ig_AE1.AESTDAT)",
    "Stop Date (ig_AE1.AEENDAT)",
    "Event Onset (ig_AE1.AEONSET)",
    "Additional Toxicity Details (ig_AE1.AETOXTERM)",
    "Event Ongoing (ig_AE1.AEONGO)",
]


def _form(rows):
    df = pd.DataFrame(rows)
    df["Form Status"] = "Submitted"
    df["Form ILB Status"] = False
    return df


def _export_16321(forms=("AE", "DSCA", "EXINF")) -> bytes:
    """A made-up Corelisting export for study 16321, as ZIP bytes."""
    ae = {column: ["", ""] for column in AE_16321}
    ae.update(
        {
            "Subject": ["100-16321-01", "100-16321-02"],
            "AE or SAE? (ig_AE2.AESEV)": ["AE", "SAE"],
            "CTCAE Category (ig_AE1.AECAT)": ["General", "Investigations"],
            "Derived Toxicity (ig_AE1.AETOXDV)": ["Fatigue", "Alt increased"],
            "Toxicity (ig_AE1.AETOX)": ["Fatigue", "ALT increased"],
            "Grade (ig_AE1.AETOXGR)": ["1", "3"],
            "Start Date (ig_AE1.AESTDAT)": ["2026-01-05", "2026-01-20"],
            "Stop Date (ig_AE1.AEENDAT)": ["2026-01-09", ""],
        }
    )
    tables = {
        "AE": _form(ae),
        "DSCA": _form(
            {
                "Subject": ["100-16321-01", "100-16321-02"],
                "Cohort Assignment (ig_DSCA1.CACHASCOD)": ["Cohort 1", "Cohort 2"],
            }
        ),
        "EXINF": _form(
            {
                "Subject": ["100-16321-01", "100-16321-02"],
                "Study Treatment Date (ig_EXINF1.INFDAT)": ["2026-01-02", "2026-01-15"],
                "Study Day (ig_EXINF1.CL_NS_NH_STUDYDAY_cl_NS_STUYDAY1)": ["Day 0"] * 2,
            }
        ),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in forms:
            archive.writestr(
                f"Core_Listings_{name}.csv", tables[name].to_csv(index=False)
            )
    return buffer.getvalue()


def _upload(data: bytes, name: str) -> io.BytesIO:
    """*data* as an uploaded file: a file-like object with a name."""
    upload = io.BytesIO(data)
    upload.name = name
    return upload


def test_it_returns_the_workbook_with_a_dated_name():
    export = _upload(_export_16321(), "Core_Listings_16321_x_2026_01_31.zip")

    output = listing.run(export, file_name="16321 AE DLT")

    assert output.name.startswith("16321 AE DLT ")
    assert output.name.endswith(".xlsx")
    workbook = load_workbook(io.BytesIO(output.data))
    assert workbook.sheetnames == [
        "Reformated AE Report",
        "AE Corelisting",
        "DSCA Corelisting",
        "EXINF Corelisting",
    ]
    report = workbook["Reformated AE Report"]
    assert report.max_row == 3  # the header and the two events


def test_an_empty_file_name_uses_the_study():
    export = _upload(_export_16321(), "Core_Listings_16321_x.zip")

    assert listing.run(export).name.startswith("16321 AE DLT ")


def test_a_study_it_isnt_set_up_for_says_which_ones_it_is():
    export = _upload(_export_16321(), "Core_Listings_99999_x.zip")

    with pytest.raises(UnsupportedStudyError) as raised:
        listing.run(export)

    assert "isn't set up for study 99999" in str(raised.value)
    assert "16321" in str(raised.value)


def test_a_file_name_without_a_study_number_says_so():
    with pytest.raises(
        UnsupportedStudyError, match="study number isn't in the file name"
    ):
        listing.run(_upload(_export_16321(), "export.zip"))


@pytest.mark.parametrize(
    "name",
    [
        "UPCC16321_CoreListing_20260901.zip",  # A date, not a study.
        "Core_Listings_163211_x.zip",  # Six digits.
        "Core_Listings_16321abc_x.zip",
    ],
)
def test_a_name_whose_third_part_isnt_a_study_number_says_so(name):
    with pytest.raises(
        UnsupportedStudyError, match="study number isn't in the file name"
    ):
        listing.run(_upload(_export_16321(), name))


@pytest.mark.parametrize(
    ("name", "study"),
    [
        ("Core_Listings_16321 (1).zip", "16321"),  # A browser's second download.
        ("Core_Listings_12423-TmCD19-IL18_2025_08_27_14_00_EDT.zip", "12423"),
    ],
)
def test_the_study_is_read_from_a_copied_or_hyphenated_name(name, study):
    output = listing.run(_upload(_export_for(study), name))

    assert output.name.startswith(f"{study} AE DLT ")


def test_an_export_without_the_ae_form_says_so():
    export = _upload(
        _export_16321(forms=("DSCA", "EXINF")), "Core_Listings_16321_x.zip"
    )

    with pytest.raises(WorkflowInputError, match="no AE form"):
        listing.run(export)


def test_a_zip_that_is_gone_says_so(tmp_path):
    with pytest.raises(WorkflowInputError, match="Couldn't find"):
        listing.run(str(tmp_path / "Core_Listings_16321_x.zip"))


def test_it_reads_a_path_too(tmp_path):
    path = tmp_path / "Core_Listings_16321_x.zip"
    path.write_bytes(_export_16321())

    assert listing.run(str(path)).data[:2] == b"PK"  # an xlsx is a ZIP


# ---------------------------------------------------------------------------
# Every supported study, from the listing's own column lists


def _blank():
    """A listing object only for asking its per-study column lists."""
    return listing.AECoreListing.__new__(listing.AECoreListing)


def _value(column: str, subject: str):
    """A made-up value for a column, by what its name says it holds."""
    name = column.split(" (")[0]
    if column == "Subject":
        return subject
    if name in ("Start Date", "Infusion Date", "Study Treatment Date"):
        return "2026-01-05" if name == "Start Date" else "2026-01-02"
    if name == "Stop Date":
        return "2026-01-09"
    if name in ("Study Day", "Event Group Label", "Event Label"):
        return "Day 0"
    if name == "CAR T Cell Dose Administered":
        return 1
    if name == "x 10 to the power of":
        return 6
    if name in ("Toxicity", "Derived Toxicity"):
        return "Fatigue"
    return "x"


def _export_for(study: str, extra_forms=()) -> bytes:
    """A one-subject export for *study*, built from the listing's column lists."""
    blank = _blank()
    keys = listing.AECoreListing.STUDY_KEY_MAP.get(study, {})
    subject = f"100-{study}-01"
    tables = {}

    def add(form, columns, first_values=None):
        row = {column: _value(column, subject) for column in columns}
        row.update(first_values or {})
        tables[form] = _form({column: [value] for column, value in row.items()})

    add(keys.get("AE", "AE"), blank.get_AE_header_list(study))
    exinf = list(blank.get_EXINF_header_list(study))
    dla_columns = blank.get_DSDLA_header_list(study)
    if dla_columns:
        exinf += [c for c in blank.get_EXINF_DLA_header_list(study) if c not in exinf]
        assignment = next(iter(blank.get_dose_level_assignment_value_dict(study)))
        add(keys.get("DSDLA", "DSDLA"), dla_columns, {dla_columns[1]: assignment})
    add(keys.get("EXINF", "EXINF"), exinf)
    cohort_columns = blank.get_DSCA_header_list(study)
    if cohort_columns:
        cohort = next(iter(blank.get_cohort_value_dict(study)))
        add(keys.get("DSCA", "DSCA"), cohort_columns, {cohort_columns[1]: cohort})
    for form in extra_forms:
        add(form, ["Subject", "Cohort Assignment (made.up)"])

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, table in tables.items():
            archive.writestr(f"Core_Listings_{name}.csv", table.to_csv(index=False))
    return buffer.getvalue()


@pytest.mark.parametrize("study", listing.SUPPORTED_STUDIES)
def test_every_supported_study_builds_its_listing(study):
    export = _upload(_export_for(study), f"Core_Listings_{study}_x.zip")

    workbook = load_workbook(io.BytesIO(listing.run(export).data))

    assert workbook.sheetnames[0] == "Reformated AE Report"
    assert workbook["Reformated AE Report"].max_row == 2  # the header and the event


@pytest.mark.parametrize("study", ["10325", "11823"])
def test_a_cohort_form_the_study_has_no_columns_for_is_left_out(study):
    export = _upload(_export_for(study, ["DSCA"]), f"Core_Listings_{study}_x.zip")

    report = load_workbook(io.BytesIO(listing.run(export).data))["Reformated AE Report"]

    headers = [cell.value for cell in report[1]]
    assert "Cohort" not in headers
