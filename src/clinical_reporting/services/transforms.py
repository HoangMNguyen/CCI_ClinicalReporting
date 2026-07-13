"""DataFrame filtering transforms used by the reporting engine.

The operator string literals here are the canonical definitions of the filter
semantics; the matching labels offered in the UI live in
:class:`clinical_reporting.core.constants.Operator`.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def apply_static_filter(df, item, operator, value):
    """
    Apply a static filter to a dataframe.

    Args:
        df (DataFrame): The dataframe to filter
        item (str): The column name to filter on
        operator (str): The operator to use ('=', '!=', '>', '>=', '<', '<=', 'Contains', 'Does not contain', 'In', 'Not in', 'is Null', 'is not Null')
        value (str): The value to compare against (not used for 'is Null' and 'is not Null' operators)

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
        return df[df[item].astype(str).str.lower().isin([v.lower() for v in value_list])]
    elif operator == "Not in":
        value_list = [v.strip() for v in str(value).split(",")]
        if is_numeric:
            try:
                numeric_list = [pd.to_numeric(v) for v in value_list]
                return df[~numeric_column.isin(numeric_list)]
            except:
                pass
        # Case-insensitive check for string values
        return df[~df[item].astype(str).str.lower().isin([v.lower() for v in value_list])]
    elif operator == "is Null":
        # Return rows where the column is null
        return df[df[item].isnull()]
    elif operator == "is not Null":
        # Return rows where the column is not null
        return df[~df[item].isnull()]
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
        logger.warning("Columns '%s' or '%s' not found in dataframe.", item1, item2)
        return df

    # Create a copy to avoid modifying the original
    df_copy = df.copy()

    # Check if column names contain 'Date' which is a good indicator that they might be dates
    date_columns = False
    if "Date" in item1 or "date" in item1 or "DATE" in item1 or "Date" in item2 or "date" in item2 or "DATE" in item2:
        date_columns = True

    # First try to convert columns to datetime if they might be dates
    if date_columns:
        try:
            # Try to convert both columns to datetime
            df_copy[item1] = pd.to_datetime(df_copy[item1], errors="coerce")
            df_copy[item2] = pd.to_datetime(df_copy[item2], errors="coerce")
            logger.debug("Converted columns %s and %s to datetime for comparison", item1, item2)
        except Exception as e:
            logger.debug("Could not convert columns to datetime: %s", e)
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
                isinstance(x, (int, float)) or (isinstance(x, str) and x.replace(".", "", 1).isdigit())
                for x in sample1
                if x is not None and pd.notna(x)
            )
            is_numeric2 = all(
                isinstance(x, (int, float)) or (isinstance(x, str) and x.replace(".", "", 1).isdigit())
                for x in sample2
                if x is not None and pd.notna(x)
            )

            if is_numeric1 and is_numeric2:
                try:
                    df_copy[item1] = pd.to_numeric(df_copy[item1], errors="coerce")
                    df_copy[item2] = pd.to_numeric(df_copy[item2], errors="coerce")
                    logger.debug("Converted columns %s and %s to numeric for comparison", item1, item2)
                    numeric_columns = True
                except Exception as e:
                    logger.debug("Could not convert columns to numeric: %s", e)
        except Exception as e:
            logger.debug("Error checking if columns are numeric: %s", e)

    # Apply filter based on operator
    logger.debug("Applying filter: %s %s %s", item1, operator, item2)

    # Get initial row count for validation
    initial_rows = len(df_copy)

    # Check if we're dealing with string columns (not dates or numbers)
    string_columns = not date_columns and not numeric_columns

    if operator == "=":
        if string_columns:
            # Case-insensitive equality for strings
            result = df_copy[
                df_copy[item1].astype(str).str.lower().str.strip() == df_copy[item2].astype(str).str.lower().str.strip()
            ]
        else:
            result = df_copy[df_copy[item1] == df_copy[item2]]
    elif operator == "!=":
        if string_columns:
            # Case-insensitive inequality for strings
            result = df_copy[
                df_copy[item1].astype(str).str.lower().str.strip() != df_copy[item2].astype(str).str.lower().str.strip()
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

    # Log how many rows were filtered
    filtered_rows = len(result)
    logger.debug("Dynamic filter reduced rows from %s to %s", initial_rows, filtered_rows)

    # Change the date columns of result back to the original format
    for col in result.select_dtypes(include=[np.datetime64]).columns:
        result.loc[:, col] = result[col].dt.strftime("%m-%d-%Y")

    return result
