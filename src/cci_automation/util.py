import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dateutil.relativedelta import relativedelta

# TODO: implement type hints for all functions

# Clockify credentials are read from the environment first, then (when running
# from source) from an optional git-ignored clockify.json beside this module.
# The built executable never bundles that file, so it needs the variables.
CLOCKIFY_API_KEY_ENV = "CCI_CLOCKIFY_API_KEY"
CLOCKIFY_WORKSPACE_ID_ENV = "CCI_CLOCKIFY_WORKSPACE_ID"
_CLOCKIFY_CONFIG_PATH = Path(__file__).resolve().with_name("clockify.json")


def clockify_sort_tasks(clockify_df, template_df):
    """sorting tasks of clockify df based on the template df

    Args:
        clockify_df (_type_): clockify dataframe
        template_df (_type_): template dataframe

    Returns:
        dataframe : sorted dataframe
    """
    # Create a dictionary mapping task names to their position in the template list
    template_order = {task: i for i, task in enumerate(template_df["Task"])}

    # Define a custom sorting function that uses the template order
    def sort_key(task_name):
        """
        Custom sorting function for task names.

        Args:
            task_name (str): The name of the task to be sorted.

        Returns:
            int: The sorting index for the given task name.
        """
        if task_name in template_order:
            return template_order[task_name]
        else:
            return float("inf")

    # Compute the sort order using the custom sorting function
    sort_order = clockify_df["Task ID"].map(sort_key).argsort()

    # Sort the Clockify DataFrame using the computed sort order
    sorted_df = clockify_df.iloc[sort_order]

    return sorted_df


def clockify_get_task_df(api_key, workspace_id, project_name):
    """
    Retrieve a DataFrame of tasks from Clockify.

    Returns:
        DataFrame: A pandas DataFrame containing Clockify tasks data.
    """
    projects = clockify_get_dict_projects(api_key, workspace_id)
    project_id = projects[project_name]

    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    params = {"is-active": "true"}

    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks"

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        tasks = response.json()
        task_names = [task["name"] for task in tasks]
        df = pd.DataFrame({"Task ID": task_names})
        return df
    else:
        print(f"Error: {response.status_code}, {response.text}")


def clockify_get_project_id(api_key, workspace_id, project_name):
    """
    Fetch the project ID from Clockify.

    Returns:
       str: The project ID.
    """
    projects = clockify_get_dict_projects(api_key, workspace_id)
    project_id = projects[project_name]
    return project_id


def clockify_get_dict_projects(api_key, workspace_id):
    """
    Retrieve a dictionary of projects from Clockify.

    Returns:
        dict: A dictionary where keys are project names and values are project details.
    """
    headers = {"content-type": "application/json", "X-Api-Key": api_key}
    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/projects"

    response = requests.get(url, headers=headers)
    projects_data = response.json()

    # Create a dictionary mapping project names to project IDs
    projects_dict = {project["name"]: project["id"] for project in projects_data}

    return projects_dict


def clockify_get_list_projects(api_key, workspace_id):
    """
    Fetch a list of projects from Clockify.

    Returns:
        list: A list of projects.
    """
    headers = {"content-type": "application/json", "X-Api-Key": api_key}
    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/projects"

    params = {"archived": "false"}
    response = requests.get(url, headers=headers, params=params)
    projects_data = response.json()

    # Create a dictionary mapping project names to project IDs
    projects_list = [project["name"] for project in projects_data if not project["archived"]]

    return projects_list


def _bundled_clockify_configuration() -> dict:
    """Read the optional clockify.json beside this module (runs from source)."""
    try:
        configuration = json.loads(_CLOCKIFY_CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(configuration, dict):
            return configuration
    except Exception:
        pass
    return {}


def _clockify_configuration_value(env_name: str, config_key: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    bundled = _bundled_clockify_configuration().get(config_key, "")
    if isinstance(bundled, str) and bundled.strip():
        return bundled.strip()
    raise RuntimeError(
        f"Clockify is not configured: set the {env_name} environment variable "
        f'(running from source, "{config_key}" in {_CLOCKIFY_CONFIG_PATH.name} '
        "next to cci_automation/util.py also works)."
    )


def clockify_get_api_key():
    """
    Retrieve the API key for Clockify access.

    Returns:
        str: The API key.
    """
    return _clockify_configuration_value(CLOCKIFY_API_KEY_ENV, "api_key")


def clockify_get_workplace_id():
    """
    Obtain the workplace ID from Clockify.

    Returns:
        str: The workplace ID.
    """
    return _clockify_configuration_value(CLOCKIFY_WORKSPACE_ID_ENV, "workspace_id")


def clockify_get_detailed_report(api_key, workspace_id, project_name):
    """
    Generate a detailed report from Clockify data.

    Returns:
        DataFrame: A pandas DataFrame containing the detailed report.
    """
    headers = {"content-type": "application/json", "X-Api-Key": api_key}
    url = f"https://reports.api.clockify.me/v1/workspaces/{workspace_id}/reports/detailed"

    # Set the start date to the earliest possible date and the end date to today
    start_date = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    end_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    project_id = None
    project_id = clockify_get_project_id(clockify_get_api_key(), clockify_get_workplace_id(), project_name)

    data = {
        "dateRangeEnd": end_date,
        "dateRangeStart": start_date,
        "detailedFilter": {"pageSize": 400},
        "projects": {"contains": "CONTAINS_ONLY", "ids": [project_id]},
        "exportType": "JSON",
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    report_data = response.json()

    # Print the report data for debugging purposes
    # print(report_data)

    # Convert the report data into a pandas DataFrame
    report_df = pd.json_normalize(report_data["timeentries"])
    if "tags" in report_df.columns:
        report_df = report_df[
            [
                "projectName",
                "taskName",
                "userName",
                "tags",
                "timeInterval.start",
                "timeInterval.end",
            ]
        ]
        report_df["tags"] = report_df["tags"].apply(
            lambda x: (
                x[0]["name"]
                if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict) and "name" in x[0]
                else None
            )
        )
    else:
        report_df = report_df[
            [
                "projectName",
                "taskName",
                "userName",
                "timeInterval.start",
                "timeInterval.end",
            ]
        ]
        report_df["tags"] = np.nan
    # print(report_df['tags'].dtypes)
    report_df["timeInterval.start"] = pd.to_datetime(report_df["timeInterval.start"])
    report_df["timeInterval.end"] = pd.to_datetime(report_df["timeInterval.end"])
    report_df["Duration (decimal)"] = (report_df["timeInterval.end"] - report_df["timeInterval.start"]) / pd.Timedelta(
        hours=1
    )  # type: ignore

    report_df["Duration (h)"] = pd.to_timedelta(report_df["Duration (decimal)"], unit="h").apply(format_timedelta)
    report_df["Duration (decimal)"] = report_df["Duration (decimal)"].round(2)
    new_report_columns_name = {
        "projectName": "Project",
        "taskName": "Task",
        "userName": "User",
        "tags": "Tags",
    }
    report_df = report_df.rename(columns=new_report_columns_name)
    report_df = report_df.drop("timeInterval.end", axis=1)
    report_df = report_df.drop("timeInterval.start", axis=1)
    return report_df


def format_timedelta(td):
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
    if key2 is None:
        df = input_data[form_name][[key1, "Form ILB Status", column_name]].copy()
    else:
        df = input_data[form_name][[key1, key2, "Form ILB Status", column_name]].copy()
    df = df[df["Form ILB Status"] == False]  # noqa: E712
    new_col_name = {column_name: new_column_name}
    df = df.rename(columns=new_col_name)
    df = df.drop(columns=["Form ILB Status"])
    if key2 is None:
        new_df = pd.merge(current_df, df, on=key1, how="left")
    else:
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
    if key2 is None:
        df = input_df[[key1, column_name]].copy()
    else:
        df = input_df[[key1, key2, column_name]].copy()
    # df = df[df['Form ILB Status'] == False]
    # df = df[df['Form Status'] != 'Blank']
    new_col_name = {column_name: new_column_name}
    df = df.rename(columns=new_col_name)
    # df = df.drop(columns = ['Form ILB Status'])
    if key2 is None:
        new_df = pd.merge(current_df, df, on=key1, how="left")
    else:
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
        numeric_column = pd.to_numeric(df[column], errors="coerce")
        mean = numeric_column.mean()
        std = numeric_column.std()
        median = numeric_column.median()
        minimum = numeric_column.min()
        maximum = numeric_column.max()

        if np.isnan(std):
            std = 0

        # Create a DataFrame for the current stats if non of the stats are NaN
        if not np.isnan(mean) and not np.isnan(median) and not np.isnan(minimum) and not np.isnan(maximum):
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
            stats_df = pd.DataFrame({"Mean ± SD": mean_std, "Median": median, "Range": range}, index=[i])
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
        numeric_column = pd.to_numeric(df[column], errors="coerce")
        mean = numeric_column.mean()
        std = numeric_column.std()
        median = numeric_column.median()
        minimum = numeric_column.min()
        maximum = numeric_column.max()

        if np.isnan(std):
            std = 0

        # Create a DataFrame for the current stats if non of the stats are NaN
        if not np.isnan(mean) and not np.isnan(median) and not np.isnan(minimum) and not np.isnan(maximum):
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
            stats_df = pd.DataFrame({"Mean ± SD": mean_std, "Median": median, "Range": range}, index=[i])
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
    It converts all numeric values in the specified column to strings, while keeping strings unchanged.

    :param df: Pandas DataFrame
    :param column_name: Name of the column to process
    :return: DataFrame with the updated column
    """
    # Check if column exists in dataframe
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' does not exist in the dataframe")

    # Convert numeric values to strings, while keeping strings and missing values unchanged.
    df[column_name] = df[column_name].apply(stringify_numeric)

    return df


def stringify_numeric(value):
    if pd.isna(value):
        return value
    if isinstance(value, (bool, np.bool_)):
        return value
    if isinstance(value, (int, np.integer)):
        return str(value)
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return str(value)
    return value


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
                collected_data = collected_data.sort_values(["Subject", "Event Date"]).drop_duplicates(
                    subset=["Subject"], keep="last"
                )
            # check if value contains 'Date' in the column name, then convert to datetime
            for col in collected_data.columns:
                if "Date" in col:
                    collected_data[col] = pd.to_datetime(collected_data[col], errors="coerce")
            # drop 'Event Date' column
            collected_data = collected_data.drop("Event Date", axis=1)
            # merge dataframes
            if keys_list.index(key) == 0:
                merged_df = collected_data
            else:
                merged_df = pd.merge(merged_df, collected_data, on="Subject", how="left")

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
            collected_data = collected_data.sort_values(["Subject", "Event Date"]).drop_duplicates(
                subset=["Subject"], keep="first"
            )
            # check if value contains 'Date' in the column name, then convert to datetime
            for col in collected_data.columns:
                if "Date" in col:
                    collected_data[col] = pd.to_datetime(collected_data[col], errors="coerce")
            # drop 'Event Date' column
            collected_data = collected_data.drop("Event Date", axis=1)
            # merge dataframes
            if keys_list.index(key) == 0:
                merged_df = collected_data
            else:
                merged_df = pd.merge(merged_df, collected_data, on="Subject", how="left")
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
                merged_df.loc[(merged_df[CS1].isnull() & merged_df[CS2].notnull()), output_column] = merged_df.loc[
                    (merged_df[CS1].isnull() & merged_df[CS2].notnull())
                ].apply(lambda x: relativedelta(x[CS2], x[DOB]).years, axis=1)
    return merged_df


def remove_leading_zeros_from_dates(df):
    """
    Process date columns in the dataframe to remove leading zeros for Windows compatibility.

    This function:
    1. Detects columns with 'date' in their name
    2. Checks if values have leading zeros in month or day (mm/dd/yyyy format)
    3. Reformats dates to remove leading zeros

    Args:
        df (DataFrame): The input dataframe to process

    Returns:
        DataFrame: The dataframe with date columns reformatted
    """
    # Create a copy of the dataframe to avoid modifying the original
    df_copy = df.copy()

    # Iterate through all columns
    for col_name in df_copy.columns:
        if "date" in str(col_name).lower():
            try:
                # First convert to datetime if not already
                if not pd.api.types.is_datetime64_any_dtype(df_copy[col_name]):
                    df_copy[col_name] = pd.to_datetime(df_copy[col_name], errors="coerce")

                # Apply formatting to remove leading zeros if it's not ""
                df_copy[col_name] = df_copy[col_name].apply(
                    lambda date_obj: format_date_without_leading_zeros_util(date_obj)
                )
            except Exception as e:
                # If conversion fails, keep original data
                print(f"Could not process date column '{col_name}': {e}")

    return df_copy


def format_date_without_leading_zeros_util(date_obj):
    """
    Format dates without leading zeros for Windows compatibility.

    Args:
        date_obj: A datetime object or NaT

    Returns:
        str or original: Formatted date string (M/D/YYYY) or original value if NaT
    """
    # if date_obj does not have
    if pd.isna(date_obj):
        return ""
    elif pd.notnull(date_obj):
        month = date_obj.month
        day = date_obj.day
        year = date_obj.year
        return f"{month}/{day}/{year}"
    return date_obj
