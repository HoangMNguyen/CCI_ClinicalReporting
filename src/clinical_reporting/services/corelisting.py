"""Corelisting-specific data loading.

Reads a Corelisting export ZIP into a ``{form_name: DataFrame}`` dictionary,
applying the clinical-reporting business rules (cut-off date, submitted/non-ILB
filtering, subject-id normalisation, ``_RAW`` column removal).
"""

from __future__ import annotations

import zipfile

import pandas as pd

from clinical_reporting.services.tabular import _READ_TABULAR_KWARGS


def read_data_dict_zip_corelisting(input_dir: str, cut_off_date=None) -> dict:
    """Read all data from csv files within the corelisting from a zip file into a dictionary of dataframes

    - Apply the cut off date if it's not None
    - Convert the subject ID to the format of 12345-67 instead of 100-12345-67
    - Filtered data to only submitted status
    - Filtered data to only non-ILB status
    - Remove all columns with "_RAW" in their names

    Args:
        input_dir (string): string of input directory of the zip file
        cut_off_date (datetime): the cut off date for the data

    Returns:
        data (dict) : the dictionary of dataframe, with keys are form names

    """

    data: dict = {}
    if cut_off_date is not None:
        cut_off_date = pd.to_datetime(cut_off_date)

    # Open the zip file
    with zipfile.ZipFile(input_dir, "r") as z:
        for file_name in z.namelist():
            if file_name.endswith(".csv"):
                file_name_noCSV = file_name.split(".")[0]

                # Load the CSV file into a Pandas data frame
                with z.open(file_name) as f:
                    df = pd.read_csv(f, **_READ_TABULAR_KWARGS)
                    # An EOS (End of Study) form is filtered on its end-of-study date.
                    # "EOSTCONF" contains "EOS" as a substring but is not an EOS form,
                    # so exclude it. Compute the flag once so the outer check and the
                    # branch selection below stay consistent.
                    last_token = file_name_noCSV.split("_")[-1]
                    is_eos = "EOS" in last_token and "EOSTCONF" not in last_token
                    # check if df has Event Date column and none of the data is blank
                    if (
                        "Event Date" in df.columns and df["Event Date"].isnull().sum() != len(df["Event Date"])
                    ) or is_eos:
                        df["Event Date"] = pd.to_datetime(df["Event Date"])
                        # if cut_off_date is not None, then filter the data based on the cut_off_date
                        if cut_off_date is not None and not is_eos:
                            df = df[df["Event Date"] <= cut_off_date]
                        elif cut_off_date is not None and is_eos:
                            # find the column header that contains "End of Study Date"
                            column_name = df.columns[df.columns.str.contains("End of Study Date", case=False)][0]
                            # Convert the relevant column to datetime date only
                            df[column_name] = pd.to_datetime(df[column_name]).dt.date
                            # filter out the data that is after the cut off date. If the date is null, keep it
                            # (compare date-to-date; cut_off_date is a Timestamp)
                            df = df[(df[column_name] <= cut_off_date.date()) | (df[column_name].isnull())]

                    # Remove all columns if the column names contains "_RAW"
                    df = df.loc[:, ~df.columns.str.contains("_RAW")]

                    # Replace '100-' prefix with an empty string
                    df["Subject"] = df["Subject"].str.replace("^100-", "", regex=True)
                    # only get data that is submitted status
                    df = df[df["Form Status"] == "Submitted"]
                    # only get data that is not ILB status
                    df = df[df["Form ILB Status"] == False]
                if file_name_noCSV.split("_")[-1] != "2":
                    data[file_name_noCSV.split("_")[-1]] = df
                else:
                    data[file_name_noCSV.split("_")[-2] + "_" + file_name_noCSV.split("_")[-1]] = df

    return data
