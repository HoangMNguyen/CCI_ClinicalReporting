import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import numpy as np
import os
import math
import zipfile
from typing import Optional, List, Dict, Tuple, Union
import pandas as pd


# TODO: implement type hints for all functions


def format_timedelta(td: timedelta) -> str:
    """
    Format a timedelta object into a human-readable string.

    Args:
        timedelta_obj (timedelta): The timedelta object to format.

    Returns:
        str: A formatted string representing the timedelta.
    """
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


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
                    df = pd.read_csv(f)
                    # check if df has Event Date column and none of the data is blank
                    if (
                        "Event Date" in df.columns
                        and df["Event Date"].isnull().sum() != len(df["Event Date"])
                    ) or "EOS" in file_name_noCSV.split("_")[-1]:
                        df["Event Date"] = pd.to_datetime(df["Event Date"])
                        # if cut_off_date is not None, then filter the data based on the cut_off_date
                        if (
                            cut_off_date is not None
                            and "EOS" not in file_name_noCSV.split("_")[-1]
                        ):
                            df = df[df["Event Date"] <= cut_off_date]
                        elif (
                            cut_off_date is not None
                            and "EOS" in file_name_noCSV.split("_")[-1]
                        ):
                            # find the column header that contains "End of Study Date"
                            column_name = df.columns[
                                df.columns.str.contains("End of Study Date", case=False)
                            ][0]
                            # Convert the relevant column to datetime
                            df[column_name] = pd.to_datetime(df[column_name])
                            # filter out the data that is after the cut off date. If the date is null, keep it
                            df = df[
                                (df[column_name] <= cut_off_date)
                                | (df[column_name].isnull())
                            ]

                    # Remove all columns if the column names contains "_RAW"
                    df = df.loc[:, ~df.columns.str.contains("_RAW")]

                    # Replace '100-' prefix with an empty string
                    df["Subject"] = df["Subject"].str.replace("^100-", "", regex=True)
                    # only get data that is submitted status
                    df = df[df["Form Status"] == "Submitted"]
                    # only get data that is not ILB status
                    df = df[df["Form ILB Status"] == False]
                data[file_name_noCSV.split("_")[-1]] = df

    return data


def add_rename_column_corelisting(
    current_df,
    input_data,
    form_name,
    column_name,
    new_column_name,
    key1="Subject",
    key2=None,
):
    """Adding a new column (merge left) to the current dataframe with an updated new name from the data of corelisting

    Args:
        current_df (dataframe): current dataframe with subject ID list
        input_data (dict): dictionary of dataframe, with keys are form names
        form_name (string): form name
        column_name (string): exact column name in corelisting
        new_column_name (string): the name of the column that would be updated
        key (string): usually it's subject ID of the

    Returns:
        new_df (dataframe): the new dataframe that is added with the new column and renamed
    """
    if key2 == None:
        df = input_data[form_name][[key1, "Form ILB Status", column_name]].copy()
    elif key2 != None:
        df = input_data[form_name][[key1, key2, "Form ILB Status", column_name]].copy()
    df = df[df["Form ILB Status"] == False]
    new_col_name = {column_name: new_column_name}
    df = df.rename(columns=new_col_name)
    df = df.drop(columns=["Form ILB Status"])
    if key2 == None:
        new_df = pd.merge(current_df, df, on=key1, how="left")
    elif key2 != None:
        new_df = pd.merge(current_df, df, on=[key1, key2], how="left")
    return new_df


def add_rename_column_df(
    current_df,
    input_df,
    form_name,
    column_name,
    new_column_name,
    key1="Subject",
    key2=None,
):
    """Adding a new column (merge left) to the current dataframe with an updated new name from the data of corelisting

    Args:
        current_df (dataframe): current dataframe with subject ID list
        input_df (dataframe):dataframe, with keys are form names
        form_name (string): form name
        column_name (string): exact column name in corelisting
        new_column_name (string): the name of the column that would be updated
        key (string): usually it's subject ID of the

    Returns:
        new_df (dataframe): the new dataframe that is added with the new column and renamed
    """
    if key2 == None:
        df = input_df[[key1, column_name]].copy()
    elif key2 != None:
        df = input_df[[key1, key2, column_name]].copy()
    # df = df[df['Form ILB Status'] == False]
    # df = df[df['Form Status'] != 'Blank']
    new_col_name = {column_name: new_column_name}
    df = df.rename(columns=new_col_name)
    # df = df.drop(columns = ['Form ILB Status'])
    if key2 == None:
        new_df = pd.merge(current_df, df, on=key1, how="left")
    elif key2 != None:
        new_df = pd.merge(current_df, df, on=[key1, key2], how="left")
    return new_df


def get_stats_df(column, *dfs):
    """
    Compute and aggregate statistical measures for a specified column across multiple DataFrames.

    This function calculates various statistical measures for a given column name that is present
    across multiple pandas DataFrames. The statistics are calculated for each DataFrame and then aggregated.

    Args:
        column (str): The name of the column for which statistical measures are to be calculated.
        *dfs (tuple of DataFrame): Variable number of DataFrame objects on which statistics are to be computed.

    Returns:
        DataFrame: A pandas DataFrame aggregating the calculated statistical measures from each input DataFrame.
    """
    # Initialize an empty DataFrame
    main_df = pd.DataFrame()

    for i, df in enumerate(dfs):
        # Calculate the mean, standard deviation, median, and range of 'Age at Consent'
        df.loc[:, column] = pd.to_numeric(df[column], errors="coerce")
        mean = df[column].mean()
        std = df[column].std()
        median = df[column].median()
        minimum = df[column].min()
        maximum = df[column].max()

        if np.isnan(std):
            std = 0

        # Create a DataFrame for the current stats if non of the stats are NaN
        if (
            not np.isnan(mean)
            and not np.isnan(median)
            and not np.isnan(minimum)
            and not np.isnan(maximum)
        ):
            # Format the mean and standard deviation
            if mean < 100:
                mean_std = f"{mean:.2f} ({std:.2f})"
            else:
                mean_std = f"{convert_float_2_sci_notation(int(mean))} ({convert_float_2_sci_notation(int(std))})"
            if median > 100:
                median = f"{convert_float_2_sci_notation(int(median))}"
            if minimum < 100 and maximum < 100:
                range = f"{minimum:.2f} - {maximum:.2f}"
            else:
                range = f"{convert_float_2_sci_notation(int(minimum))} - {convert_float_2_sci_notation(int(maximum))}"
            stats_df = pd.DataFrame(
                {"Mean ± SD": mean_std, "Median": median, "Range": range}, index=[i]
            )
        else:
            stats_df = pd.DataFrame(index=[i])
        # Append the stats DataFrame to the main DataFrame if it is not empty
        main_df = pd.concat([main_df, stats_df])
    # Transpose the DataFrame to switch the axes
    main_df = main_df.T
    return main_df


def get_stats_perc_df(column, *dfs):
    """
    Compute and aggregate percentage-based statistical measures for a specified column across multiple DataFrames.

    This function calculates statistics related to the percentage distribution of values for a given column
    that exists across multiple pandas DataFrames. It computes these statistics for each DataFrame individually
    and then aggregates the results.

    Args:
        column (str): The name of the column for which percentage-based statistical measures are to be calculated.
        *dfs (tuple of DataFrame): A variable number of DataFrame objects for which the statistics are to be computed.

    Returns:
        DataFrame: A pandas DataFrame aggregating the percentage-based statistical measures from each input DataFrame.
    """
    # Initialize an empty DataFrame
    main_df = pd.DataFrame()

    for i, df in enumerate(dfs):
        # Calculate the mean, standard deviation, median, and range of 'Age at Consent'
        df.loc[:, column] = pd.to_numeric(df[column], errors="coerce")
        mean = df[column].mean()
        std = df[column].std()
        median = df[column].median()
        minimum = df[column].min()
        maximum = df[column].max()

        if np.isnan(std):
            std = 0

        # Create a DataFrame for the current stats if non of the stats are NaN
        if (
            not np.isnan(mean)
            and not np.isnan(median)
            and not np.isnan(minimum)
            and not np.isnan(maximum)
        ):
            # Format the mean and standard deviation
            if mean < 100:
                mean_std = f"{mean:.2f}% ({std:.2f}%)"
            else:
                mean_std = f"{convert_float_2_sci_notation(int(mean))}% ({convert_float_2_sci_notation(int(std))}%)"
            if median > 100:
                median = f"{convert_float_2_sci_notation(int(median))}%"
            else:
                median = f"{median:.2f}%"
            if minimum < 100 and maximum < 100:
                range = f"{minimum:.2f}% - {maximum:.2f}%"
            else:
                range = f"{convert_float_2_sci_notation(int(minimum))}% - {convert_float_2_sci_notation(int(maximum))}%"
            stats_df = pd.DataFrame(
                {"Mean ± SD": mean_std, "Median": median, "Range": range}, index=[i]
            )
        else:
            stats_df = pd.DataFrame(index=[i])
        # Append the stats DataFrame to the main DataFrame if it is not empty
        main_df = pd.concat([main_df, stats_df])
    # Transpose the DataFrame to switch the axes
    main_df = main_df.T
    return main_df


def convert_float_2_sci_notation(n):
    """
    Convert a floating-point number to its scientific notation as a string.

    This function takes a floating-point number and converts it into a string that represents its scientific notation.
    Scientific notation expresses the number as a mantissa multiplied by 10 raised to an exponent. The mantissa is
    rounded to two decimal places unless it is an integer. If the input number is 0, it simply returns '0'.

    Args:
        n (float): The floating-point number to be converted into scientific notation.

    Returns:
        string: A string representing the scientific notation of the input number. The mantissa is formatted to
                have two decimal places unless it is an integer, followed by 'x10' and the exponent.
    """
    if n == 0:
        return "0"
    else:
        exponent = int(math.floor(math.log10(abs(n))))
        mantissa = n / 10**exponent
        if mantissa.is_integer():
            mantissa = int(mantissa)
            return f"{mantissa}x10^{exponent}"
        else:
            return f"{mantissa:.2f}x10^{exponent}"


def convert_sci_notation_2_float(s):
    """
    Convert a string representing a number in scientific notation to a floating-point number.

    This function takes a string in the format 'mantissax10^exponent', where the mantissa and exponent are
    separated by 'x10^', and converts it into a floating-point number. If the string is not in the correct format
    or contains values that cannot be converted to floats, the function handles the error and returns NaN.

    Args:
        s (str): A string representing a number in scientific notation.

    Returns:
        float: The floating-point equivalent of the input string. If the string is not properly formatted or
               contains invalid values, NaN (Not a Number) is returned.
    """
    try:
        parts = s.split("x10^")
        if len(parts) != 2:
            return np.nan
        mantissa = float(parts[0])
        exponent = float(parts[1])
        return mantissa * 10**exponent

    except ValueError:
        return np.nan


def convert_integers_to_strings(df, column_name):
    """
    This function takes a dataframe and a column name as input.
    It converts all integers in the specified column to strings, while keeping strings unchanged.

    :param df: Pandas DataFrame
    :param column_name: Name of the column to process
    :return: DataFrame with the updated column
    """
    # Check if column exists in dataframe
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' does not exist in the dataframe")

    # Convert integers to strings, if the value is an integer, else return Nan
    df[column_name] = df[column_name].apply(
        lambda x: str(x) if isinstance(x, int) else np.NaN
    )

    return df


def get_data_from_dict(data: dict, input_dict: dict, *exclude) -> pd.DataFrame:
    """
    Retrieves and processes data from a dictionary based on specified keys.
    Subject and Event Date columns are always included in the output DataFrame.
    For each subject, only the row with the latest 'Event Date' is kept.

    Args:
        data (dict): A dictionary containing the data.
        input_dict (dict): A dictionary specifying the keys to retrieve from `data`.

    Returns:
        pandas.DataFrame: A DataFrame containing the collected and processed data.

    """
    # Convert dict_keys to a list to use index method
    keys_list = list(input_dict.keys())

    # Convert exclude to a list
    exclude = list(exclude)

    for key in input_dict.keys():
        if key in data:
            input_keys = ["Subject", "Event Date"] + list(input_dict[key].keys())
            collected_data = data[key][input_keys].copy()
            collected_data.rename(columns=input_dict[key], inplace=True)
            # input_key is not within the exclude list
            if key not in exclude:
                # if there are more than one row for the same subject, keep the one with the last 'Event Date'
                collected_data = collected_data.sort_values(
                    ["Subject", "Event Date"]
                ).drop_duplicates(subset=["Subject"], keep="last")
            # check if value contains 'Date' in the column name, then convert to datetime
            for col in collected_data.columns:
                if "Date" in col:
                    collected_data[col] = pd.to_datetime(
                        collected_data[col], errors="coerce"
                    )
            # drop 'Event Date' column
            collected_data = collected_data.drop("Event Date", axis=1)
            # merge dataframes
            if keys_list.index(key) == 0:
                merged_df = collected_data
            else:
                merged_df = pd.merge(
                    merged_df, collected_data, on="Subject", how="left"
                )

    return merged_df


def get_data_from_dict_first(data: dict, input_dict: dict) -> pd.DataFrame:
    """
    Retrieves and processes data from a dictionary based on specified keys.
    Subject and Event Date columns are always included in the output DataFrame.
    For each subject, only the row with the earliest 'Event Date' is kept for infusion CRF for primary treatment (Day 0).

    Args:
        data (dict): A dictionary containing the data.
        input_dict (dict): A dictionary specifying the keys to retrieve from `data`.

    Returns:
        pandas.DataFrame: A DataFrame containing the collected and processed data.

    """
    # Convert dict_keys to a list to use index method
    keys_list = list(input_dict.keys())

    for key in input_dict.keys():
        if key in data:
            input_keys = ["Subject", "Event Date"] + list(input_dict[key].keys())
            collected_data = data[key][input_keys].copy()
            collected_data.rename(columns=input_dict[key], inplace=True)
            # if there are more than one row for the same subject, keep the one with the last 'Event Date'
            collected_data = collected_data.sort_values(
                ["Subject", "Event Date"]
            ).drop_duplicates(subset=["Subject"], keep="first")
            # check if value contains 'Date' in the column name, then convert to datetime
            for col in collected_data.columns:
                if "Date" in col:
                    collected_data[col] = pd.to_datetime(
                        collected_data[col], errors="coerce"
                    )
            # drop 'Event Date' column
            collected_data = collected_data.drop("Event Date", axis=1)
            # merge dataframes
            if keys_list.index(key) == 0:
                merged_df = collected_data
            else:
                merged_df = pd.merge(
                    merged_df, collected_data, on="Subject", how="left"
                )
    return merged_df


def age_calculation(merged_df, output_column, DOB: str, CS1: str, CS2: str = ""):
    """Calculate the age based on the given date of birth (DOB) and two columns (CS1 and CS2).

    Args:
        merged_df (DataFrame): The merged dataframe containing the data.
        output_column (str): The name of the column to store the calculated age.
        DOB (str): The name of the column containing the date of birth.
        CS1 (str): The name of the first column to use for age calculation.
        CS2 (str, optional): The name of the second column to use for age calculation. Defaults to ''.

    Returns:
        DataFrame: The merged dataframe with the calculated age in the specified output column.
    """
    # check if the two columns CS1 and DOB are not empty
    if (DOB in merged_df) and (CS1 in merged_df) and (not merged_df[DOB].empty):
        if not merged_df[CS1].empty:
            # find mask for non-NaT values in the two columns
            mask = ~merged_df[[CS1, DOB]].isnull().any(axis=1)
            # apply relativedelta only to rows with non-NaT values in both columns
            merged_df.loc[mask, output_column] = merged_df[mask].apply(
                lambda x: relativedelta(x[CS1], x[DOB]).years, axis=1
            )
        if (CS2 in merged_df) and CS2 != "":
            # for rows that CS1 isnull but CS2 is not null, then use CS2 instead to calculate age
            if not merged_df[CS2].empty:
                merged_df.loc[
                    (merged_df[CS1].isnull() & merged_df[CS2].notnull()), output_column
                ] = merged_df.loc[
                    (merged_df[CS1].isnull() & merged_df[CS2].notnull())
                ].apply(lambda x: relativedelta(x[CS2], x[DOB]).years, axis=1)
    return merged_df


def get_excel_formats(workbook):
    """
    Returns a dictionary of formatting options for Excel workbooks.

    Args:
        workbook: The xlsxwriter workbook object

    Returns:
        dict: Dictionary containing formatting options
    """
    return {
        "bold_11_format": workbook.add_format(
            {
                "bg_color": "#FFFFFF",
                "text_wrap": True,
                "valign": "vcenter",
                "align": "center",
                "bold": True,
                "font_name": "Calibri",
                "font_size": 11,
                "border": 1,
            }
        ),
        "bold_12_format": workbook.add_format(
            {
                "bg_color": "#FFFFFF",
                "text_wrap": False,
                "valign": "vcenter",
                "align": "center",
                "bold": True,
                "font_name": "Calibri",
                "font_size": 12,
                "border": 1,
            }
        ),
        "bold_12_wrap_format": workbook.add_format(
            {
                "bg_color": "#FFFFFF",
                "text_wrap": True,
                "valign": "vcenter",
                "align": "center",
                "bold": True,
                "font_name": "Calibri",
                "font_size": 12,
                "border": 1,
            }
        ),
        "bold_11_wrap_format": workbook.add_format(
            {
                "bg_color": "#FFFFFF",
                "text_wrap": True,
                "valign": "vcenter",
                "align": "center",
                "bold": True,
                "font_name": "Calibri",
                "font_size": 11,
                "border": 1,
            }
        ),
        "normal_data_format": workbook.add_format(
            {
                "bg_color": "#FFFFFF",
                "text_wrap": False,
                "valign": "vcenter",
                "align": "center",
                "bold": False,
                "font_name": "Calibri",
                "font_size": 11,
                "border": 1,
            }
        ),
        "normal_data_wrap_format": workbook.add_format(
            {
                "bg_color": "#FFFFFF",
                "text_wrap": True,
                "valign": "vcenter",
                "align": "center",
                "bold": False,
                "font_name": "Calibri",
                "font_size": 11,
                "border": 1,
            }
        ),
    }


def apply_static_filter(df, item, operator, value):
    """
    Apply a static filter to a dataframe.

    Args:
        df (DataFrame): The dataframe to filter
        item (str): The column name to filter on
        operator (str): The operator to use ('=', '!=', '>', '>=', '<', '<=', 'Contains', 'Does not contain', 'In', 'Not in')
        value (str): The value to compare against

    Returns:
        DataFrame: The filtered dataframe
    """
    # Handle None or empty dataframe
    if df is None or df.empty:
        return df

    # Check if the column exists
    if item not in df.columns:
        return df

    # Try to convert to numeric first
    is_numeric = False
    try:
        numeric_value = pd.to_numeric(value)
        numeric_column = pd.to_numeric(df[item], errors="coerce")
        is_numeric = True
    except:
        # If conversion fails, treat as strings
        pass

    # Apply filters with appropriate handling for numeric vs string data
    if operator == "=":
        if is_numeric:
            return df[numeric_column == numeric_value]
        else:
            # Case-insensitive string comparison
            return df[df[item].astype(str).str.lower() == str(value).lower()]
    elif operator == "!=":
        if is_numeric:
            return df[numeric_column != numeric_value]
        else:
            # Case-insensitive string comparison
            return df[df[item].astype(str).str.lower() != str(value).lower()]
    elif operator == ">":
        if is_numeric:
            return df[numeric_column > numeric_value]
        else:
            # For strings, use the original case-sensitive comparison
            return df[df[item] > value]
    elif operator == ">=":
        if is_numeric:
            return df[numeric_column >= numeric_value]
        else:
            return df[df[item] >= value]
    elif operator == "<":
        if is_numeric:
            return df[numeric_column < numeric_value]
        else:
            return df[df[item] < value]
    elif operator == "<=":
        if is_numeric:
            return df[numeric_column <= numeric_value]
        else:
            return df[df[item] <= value]
    elif operator == "Contains":
        # Already case insensitive with case=False
        return df[df[item].astype(str).str.contains(str(value), case=False, na=False)]
    elif operator == "Does not contain":
        # Already case insensitive with case=False
        return df[~df[item].astype(str).str.contains(str(value), case=False, na=False)]
    elif operator == "In":
        # Split the value by commas and strip whitespace
        value_list = [v.strip() for v in str(value).split(",")]
        if is_numeric:
            try:
                numeric_list = [pd.to_numeric(v) for v in value_list]
                return df[numeric_column.isin(numeric_list)]
            except:
                pass
        # Case-insensitive check for string values
        return df[
            df[item].astype(str).str.lower().isin([v.lower() for v in value_list])
        ]
    elif operator == "Not in":
        value_list = [v.strip() for v in str(value).split(",")]
        if is_numeric:
            try:
                numeric_list = [pd.to_numeric(v) for v in value_list]
                return df[~numeric_column.isin(numeric_list)]
            except:
                pass
        # Case-insensitive check for string values
        return df[
            ~df[item].astype(str).str.lower().isin([v.lower() for v in value_list])
        ]
    else:
        return df


def apply_dynamic_filter(df, item1, operator, item2):
    """
    Apply a dynamic filter to a dataframe, comparing two columns.

    Args:
        df (DataFrame): The dataframe to filter
        item1 (str): The first column name
        operator (str): The operator to use ('=', '!=', '>', '>=', '<', '<=')
        item2 (str): The second column name

    Returns:
        DataFrame: The filtered dataframe
    """
    # Handle None or empty dataframe
    if df is None or df.empty:
        return df

    # Ensure both columns exist
    if item1 not in df.columns or item2 not in df.columns:
        print(f"Warning: Columns '{item1}' or '{item2}' not found in dataframe.")
        return df

    # Create a copy to avoid modifying the original
    df_copy = df.copy()

    # Check if column names contain 'Date' which is a good indicator that they might be dates
    date_columns = False
    if (
        "Date" in item1
        or "date" in item1
        or "DATE" in item1
        or "Date" in item2
        or "date" in item2
        or "DATE" in item2
    ):
        date_columns = True

    # First try to convert columns to datetime if they might be dates
    if date_columns:
        try:
            # Try to convert both columns to datetime
            df_copy[item1] = pd.to_datetime(df_copy[item1], errors="coerce")
            df_copy[item2] = pd.to_datetime(df_copy[item2], errors="coerce")
            print(f"Converted columns {item1} and {item2} to datetime for comparison")
        except Exception as e:
            print(f"Could not convert columns to datetime: {str(e)}")
            date_columns = False  # Reset flag if conversion failed

    # Check if columns are predominantly numeric before attempting conversion
    numeric_columns = False
    if not date_columns:
        # Check if columns appear to be numeric by sampling non-null values
        sample1 = df_copy[item1].dropna().head(10)
        sample2 = df_copy[item2].dropna().head(10)

        # Try to determine if columns are numeric without forcing conversion
        try:
            is_numeric1 = all(
                isinstance(x, (int, float))
                or (isinstance(x, str) and x.replace(".", "", 1).isdigit())
                for x in sample1
                if x is not None and pd.notna(x)
            )
            is_numeric2 = all(
                isinstance(x, (int, float))
                or (isinstance(x, str) and x.replace(".", "", 1).isdigit())
                for x in sample2
                if x is not None and pd.notna(x)
            )

            if is_numeric1 and is_numeric2:
                try:
                    df_copy[item1] = pd.to_numeric(df_copy[item1], errors="coerce")
                    df_copy[item2] = pd.to_numeric(df_copy[item2], errors="coerce")
                    print(
                        f"Converted columns {item1} and {item2} to numeric for comparison"
                    )
                    numeric_columns = True
                except Exception as e:
                    print(f"Could not convert columns to numeric: {str(e)}")
        except Exception as e:
            print(f"Error checking if columns are numeric: {str(e)}")

    # Apply filter based on operator
    print(f"Applying filter: {item1} {operator} {item2}")

    # Get initial row count for validation
    initial_rows = len(df_copy)

    # Check if we're dealing with string columns (not dates or numbers)
    string_columns = not date_columns and not numeric_columns

    if operator == "=":
        if string_columns:
            # Case-insensitive equality for strings
            result = df_copy[
                df_copy[item1].astype(str).str.lower().str.strip()
                == df_copy[item2].astype(str).str.lower().str.strip()
            ]
        else:
            result = df_copy[df_copy[item1] == df_copy[item2]]
    elif operator == "!=":
        if string_columns:
            # Case-insensitive inequality for strings
            result = df_copy[
                df_copy[item1].astype(str).str.lower().str.strip()
                != df_copy[item2].astype(str).str.lower().str.strip()
            ]
        else:
            result = df_copy[df_copy[item1] != df_copy[item2]]
    elif operator == ">":
        if string_columns:
            # For string columns, use direct comparison
            result = df_copy[df_copy[item1] > df_copy[item2]]
        else:
            result = df_copy[df_copy[item1] > df_copy[item2]]
    elif operator == ">=":
        if string_columns:
            # For string columns, use direct comparison
            result = df_copy[df_copy[item1] >= df_copy[item2]]
        else:
            result = df_copy[df_copy[item1] >= df_copy[item2]]
    elif operator == "<":
        if string_columns:
            # For string columns, use direct comparison
            result = df_copy[df_copy[item1] < df_copy[item2]]
        else:
            result = df_copy[df_copy[item1] < df_copy[item2]]
    elif operator == "<=":
        if string_columns:
            # For string columns, use direct comparison
            result = df_copy[df_copy[item1] <= df_copy[item2]]
        else:
            result = df_copy[df_copy[item1] <= df_copy[item2]]
    else:
        result = df_copy

    # Print how many rows were filtered
    filtered_rows = len(result)
    print(f"Dynamic filter reduced rows from {initial_rows} to {filtered_rows}")

    return result


def join_dataframes(left_df, right_df, join_items, join_type="left"):
    """
    Join two dataframes based on specified join items and join type.

    Args:
        left_df (DataFrame): The left dataframe
        right_df (DataFrame): The right dataframe
        join_items (list): The columns to join on
        join_type (str): The type of join ('left', 'right', 'inner', 'outer')

    Returns:
        DataFrame: The joined dataframe
    """
    # Handle None or empty dataframes
    if left_df is None or left_df.empty:
        return right_df
    if right_df is None or right_df.empty:
        return left_df

    # Ensure join items exist in both dataframes
    valid_join_items = [
        item
        for item in join_items
        if item in left_df.columns and item in right_df.columns
    ]

    if not valid_join_items:
        return left_df  # If no valid join items, return left dataframe

    # Perform the join
    return pd.merge(left_df, right_df, on=valid_join_items, how=join_type)
