import math
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pandas as pd

# TODO: implement type hints for all functions


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


def get_stats_percentage(column, *args):
    """
    Compute the percentage of each category in a specified column across multiple DataFrames.
    If the sum of the counts for a category is 0, the percentage is 0.0%.
    No
    Returns:
        dataframe: merged dataframe for stats
    """
    if column == "Legal Sex":
        groupby = ["Male", "Female", "X (Nonbinary)", "Not Reported"]
    elif column == "Race":
        groupby = [
            "African American",
            "Alaska Native",
            "American Indian",
            "Asian",
            "Caucasian",
            "Multiple Races",
            "Pacific Islander",
            "Other",
            "Unknown",
        ]
    elif column == "Ethnicity":
        groupby = ["Hispanic", "Non-Hispanic", "Unknown"]
    elif column == "AE":
        groupby = ["Y", "N"]
    elif column == "SAE":
        groupby = ["Y", "N"]
    # NHL
    elif column == "PET-Based Response" or column == "PET-Based ORR":
        groupby = [
            "Complete Metabolic Response (CMR)",
            "Partial Metabolic Response (PMR)",
            "No Metabolic Response (NMR)",
            "Indeterminate Response (IR)",
            "Progressive Metabolic Disease (PMD)",
            "Not Reported",
        ]
    elif column == "CT-Based Response" or column == "CT-Based ORR":
        groupby = [
            "Complete Radiologic Response (CR)",
            "Partial Response (PR)",
            "Stable Disease (SD)",
            "Indeterminate Response (IR)",
            "Progressive Disease (PD)",
            "Not Reported",
        ]
    # CLL
    elif column == "OV-Best Response" or column == "Overall Response":
        groupby = [
            "Complete Remission (CR)",
            "Complete Remission with Incomplete Marrow Recovery (CRi)",
            "Partial Remission (PR)",
            "Stable Disease (SD)",
            "Progressive Disease (PD)",
            "Not Reported",
        ]
    elif column == "BM-Best Response" or column == "Bone Marrow Response":
        groupby = [
            "Complete Remission (CR)",
            "Partial Remission (PR)",
            "Progressive Disease (PD)",
            "Stable Disease (SD)",
            "Not Reported",
        ]
    # ALL
    elif column == "Best Overall Response" or column == "OV ORR":
        groupby = [
            "Complete Remission (CR)",
            "Complete Remission with Incomplete Blood Count Recovery (CRi)",
            "Complete Remission with Residual Mediastinal Disease (CRu)",
            "Treatment Failure (TF)",
            "Relapsed Disease (RD)",
            "Not Reported",
        ]
    elif column == "Best ED Response" or column == "ED ORR":
        groupby = [
            "Complete Remission (CR)",
            "Partial Remission (PR)",
            "Stable Disease (SD)",
            "Indeterminate Response",
            "Progressive Disease (PD)",
            "Not Reported",
        ]
    else:
        groupby = None
    # create a dataframe to store the stats
    main_df = pd.DataFrame()

    for arg in args:
        if groupby is not None:
            temp_df = (
                arg.groupby(column)
                .agg({"Subject": "count"})
                .reindex(groupby, fill_value=0)
            )
        else:
            temp_df = arg.groupby(column).agg({"Subject": "count"})
        # combine the percentage and count column into 1 column for variables different than 0
        temp_df = temp_df.apply(
            lambda x: (
                x.astype(str)
                + " ("
                + (x / sum(x)).apply(lambda y: "{:.1%}".format(y))
                + ")"
                if x.sum() != 0
                else x.astype(str) + " (0.0%)"
            )
        )
        # merge the temp_df to the main df
        main_df = pd.concat([main_df, temp_df], axis=1)
    return main_df


def get_stats_percentage2(
    column: str, groupby: list, *args: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate the percentage of each unique value in a specified column of a DataFrame, grouped by another column.

    This function takes a column name, a groupby column name, and one or more DataFrames. It returns a new DataFrame
    containing the unique values in the specified column, their corresponding percentages of the total count within
    each group defined by the groupby column.

    Args:
        column (str): The name of the column for which to calculate the percentages.
        groupby (list): The unique values in the groupby column to group the data by.
        *args (pd.DataFrame): One or more DataFrames containing the data.

    Returns:
        pd.DataFrame: A DataFrame with three columns: 'Group', 'Value', and 'Percentage'. The 'Group' column
                      contains the unique values from the groupby column, the 'Value' column contains the unique
                      values from the specified column, and the 'Percentage' column contains the percentage of each
                      value relative to the total count within each group.
    """
    # Your function implementation here

    # create a dataframe to store the stats
    main_df = pd.DataFrame()

    for arg in args:
        if groupby is not None:
            temp_df = (
                arg.groupby(column)
                .agg({"Subject": "count"})
                .reindex(groupby, fill_value=0)
            )
        else:
            temp_df = arg.groupby(column).agg({"Subject": "count"})
        # combine the percentage and count column into 1 column for variables different than 0
        temp_df = temp_df.apply(
            lambda x: (
                x.astype(str)
                + " ("
                + (x / sum(x)).apply(lambda y: "{:.1%}".format(y))
                + ")"
                if x.sum() != 0
                else x.astype(str) + " (0.0%)"
            )
        )
        # merge the temp_df to the main df
        main_df = pd.concat([main_df, temp_df], axis=1)
    return main_df


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
        if df.count()[column] != 0:
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
                    mean_std = f"{convert_float_2_sci_notation(mean)} ({convert_float_2_sci_notation(int(std))})"
                if median > 100:
                    median = f"{convert_float_2_sci_notation(median)}"
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
        else:
            # if the column is empty, fill the stats with '0 (0.0)'
            stats_df = pd.DataFrame(
                {"Mean ± SD": "0 (0.0)", "Median": 0, "Range": "0 - 0"}, index=[i]
            )
            # Append the stats DataFrame to the main DataFrame if it is not empty
            main_df = pd.concat([main_df, stats_df])
    # Transpose the DataFrame to switch the axes
    main_df = main_df.T
    # if NaN, replace with '0 (0.0)'
    main_df = main_df.fillna("0 (0.0)")
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
                mean_std = f"{convert_float_2_sci_notation(mean)}% ({convert_float_2_sci_notation(std)}%)"
            if median > 100:
                median = f"{convert_float_2_sci_notation(median)}%"
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


# If you want round half up behavior (the usual "schoolbook rounding"), you should use the decimal module with ROUND_HALF_UP.
def convert_float_2_sci_notation(n):
    """
    Convert a floating-point number to scientific notation,
    rounding mantissa to 2 decimals using ROUND_HALF_UP
    and dropping trailing zeros.
    """
    if n == 0:
        return "0"
    else:
        exponent = int(math.floor(math.log10(abs(n))))

        # Convert to Decimal BEFORE dividing to avoid float precision issues
        n_decimal = Decimal(str(n))
        mantissa = n_decimal / (Decimal("10") ** exponent)

        # Round mantissa to 2 decimals (ROUND_HALF_UP)
        mantissa_str = (
            str(mantissa.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            .rstrip("0")
            .rstrip(".")
        )

        return f"{mantissa_str}x10^{exponent}"
