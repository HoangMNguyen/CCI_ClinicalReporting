"""Reading Corelisting exports and additional inputs (clinical_reporting.data)."""

import io
import zipfile

import pandas as pd
import pytest

from clinical_reporting import data
from clinical_reporting.data import (
    load_tabular_file,
    read_data_dict_zip_corelisting,
    try_load_tabular_files,
)


def test_load_tabular_file_preserves_literal_na(tmp_path):
    input_path = tmp_path / "additional.csv"
    input_path.write_text(
        "Subject,Value,Blank\n001,NA,\n002,N/A,text\n",
        encoding="utf-8",
    )

    df = load_tabular_file(str(input_path))

    # Literal "NA" and "N/A" are meaningful clinical values and must be kept as
    # text; only a truly blank cell is treated as missing.
    assert df.loc[0, "Value"] == "NA"
    assert pd.isna(df.loc[0, "Blank"])
    assert df.loc[1, "Value"] == "N/A"


def test_read_data_dict_zip_corelisting_preserves_literal_na(tmp_path):
    input_path = tmp_path / "corelisting.zip"
    csv_content = (
        "Subject,Form Status,Form ILB Status,Value\n"
        "100-001,Submitted,False,NA\n"
        "100-002,Submitted,False,N/A\n"
        "100-003,Draft,False,NA\n"
        "100-004,Submitted,True,NA\n"
    )
    with zipfile.ZipFile(input_path, "w") as zip_file:
        zip_file.writestr("Study_DM.csv", csv_content)

    data = read_data_dict_zip_corelisting(str(input_path))

    df = data["DM"].reset_index(drop=True)
    assert df.loc[0, "Subject"] == "001"
    # Both "NA" and "N/A" are preserved as literal text rather than parsed as NaN.
    assert df.loc[0, "Value"] == "NA"
    assert df.loc[1, "Value"] == "N/A"


def test_read_data_dict_zip_corelisting_filters_submitted_non_ilb_and_cutoff(tmp_path):
    df = pd.DataFrame(
        {
            "Subject": ["100-15420-01", "100-15420-02", "100-15420-03", "100-15420-04"],
            "Event Date": ["2024-01-01", "2024-02-01", "2024-01-10", "2024-01-15"],
            "Form Status": ["Submitted", "Submitted", "Draft", "Submitted"],
            "Form ILB Status": [False, False, False, True],
            "Value": ["keep", "after cutoff", "draft", "ilb"],
        }
    )
    zip_path = tmp_path / "core_listing.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("Core_Listings_DM.csv", df.to_csv(index=False))

    result = read_data_dict_zip_corelisting(str(zip_path), cut_off_date="2024-01-31")

    expected = pd.DataFrame(
        {
            "Subject": ["15420-01"],
            "Event Date": [pd.Timestamp("2024-01-01")],
            "Form Status": ["Submitted"],
            "Form ILB Status": [False],
            "Value": ["keep"],
        }
    )
    pd.testing.assert_frame_equal(result["DM"].reset_index(drop=True), expected)


def test_one_unreadable_additional_file_does_not_stop_the_others(tmp_path):
    good = tmp_path / "labs.csv"
    good.write_text("Subject,Hb\n001,12\n", encoding="utf-8")
    bad = tmp_path / "notes.txt"
    bad.write_text("not a table", encoding="utf-8")

    loaded, failures = try_load_tabular_files([str(good), str(bad)])

    assert list(loaded) == [str(good)]
    assert list(loaded[str(good)].columns) == ["Subject", "Hb"]
    assert list(failures) == [str(bad)] and failures[str(bad)]


def test_load_tabular_file_accepts_an_open_file_with_a_name():
    upload = io.BytesIO(b"Subject,Result\n01,N/A\n")

    df = load_tabular_file(upload, name="labs.csv")

    assert df["Result"].tolist() == ["N/A"]


def test_load_tabular_file_rejects_unknown_upload_types():
    with pytest.raises(ValueError):
        load_tabular_file(io.BytesIO(b"x"), name="notes.txt")


def test_an_additional_file_without_a_form_name_is_named_after_the_file():
    names = data.additional_form_names(
        ["/x/lab_results.csv", "/x/pk.csv", "/x/ae.csv"],
        {"/x/pk.csv": "PK", "/x/ae.csv": ""},
    )

    assert names == {
        "/x/lab_results.csv": "lab_results.csv",
        "/x/pk.csv": "PK",
        "/x/ae.csv": "ae.csv",
    }
