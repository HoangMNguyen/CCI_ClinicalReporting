import zipfile

import pandas as pd

from clinical_reporting.services.util import load_tabular_file, read_data_dict_zip_corelisting


def test_load_tabular_file_preserves_literal_na(tmp_path):
    input_path = tmp_path / "additional.csv"
    input_path.write_text(
        "Subject,Value,Blank\n"
        "001,NA,\n"
        "002,N/A,text\n",
        encoding="utf-8",
    )

    df = load_tabular_file(str(input_path))

    assert df.loc[0, "Value"] == "NA"
    assert pd.isna(df.loc[0, "Blank"])
    assert pd.isna(df.loc[1, "Value"])


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
    assert df.loc[0, "Value"] == "NA"
    assert pd.isna(df.loc[1, "Value"])
