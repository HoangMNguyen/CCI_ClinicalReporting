"""The format tool: one of CCI Automation's workflows.

:func:`run` reads a CSV or Excel file and returns it as a workbook
(:class:`clinical_reporting.workflow.OutputFile`) where lab ranges such as
10-20 stay text, dates lose their leading zeros (03/05/2026 becomes
3/5/2026, as text, in columns whose name says "date"), and the ".1" pandas
adds to a repeated column name is dropped. Nothing here touches Qt or a
folder.
"""

import io
import logging
import os
import re
import zipfile

import pandas as pd

from clinical_reporting.workflow import (
    OutputFile,
    WorkflowInputError,
    file_name_of,
    input_name,
    named_output,
    reading_input,
)

logger = logging.getLogger(__name__)

#: What the messages call this workflow (in the middle of a sentence).
WORKFLOW = "the format tool"
#: The files it reads.
EXTENSIONS = (".csv", ".xlsx")


# Function to check if any cell in the column matches the specific pattern
def has_range_pattern(series):
    return series.apply(lambda x: bool(re.match(r"\d+-\d+", str(x)))).any()


# Function to format dates without leading zeros for Windows compatibility
def format_date_without_leading_zeros(date_obj):
    if pd.notnull(date_obj):
        month = date_obj.month
        day = date_obj.day
        year = date_obj.year
        return f"{month}/{day}/{year}"
    return date_obj


def default_file_name(source) -> str:
    """The file name to suggest (the run adds the date and time): "<name>_formatted"."""
    stem = os.path.splitext(os.path.basename(input_name(source)))[0]
    return f"{stem}_formatted" if stem else "formatted"


def run(source, *, file_name: str = "") -> OutputFile:
    """Format a CSV or Excel file and return the result as a workbook.

    *source* is the file's path or a file-like object with a ``name`` (its
    extension says how to read it). The workbook is named *file_name* (or
    :func:`default_file_name`) plus the date and time. Raises
    :class:`~clinical_reporting.workflow.WorkflowInputError` when the file is
    gone, can't be read, or isn't a CSV or .xlsx file.
    """
    extension = os.path.splitext(input_name(source))[1].lower()
    if extension not in EXTENSIONS:
        raise WorkflowInputError(
            f"{file_name_of(source, 'The file')} isn't a CSV or Excel (.xlsx) file, "
            f"which {WORKFLOW} reads."
        )
    if extension == ".csv":
        # pandas' ValueError (not text, empty, not a table) can only mean
        # that here: nothing is parsed as a date while reading.
        with reading_input(source, "a CSV file", unreadable=(KeyError, ValueError)):
            # Stored as a dictionary with a single entry for consistency
            all_data = {"Sheet1": _read_csv(source)}
    else:
        with reading_input(
            source,
            "an Excel workbook (.xlsx)",
            unreadable=(zipfile.BadZipFile, KeyError, ValueError, ImportError),
            damage="damaged or password-protected",
        ):
            all_data = pd.read_excel(source, sheet_name=None)
    buffer = io.BytesIO()
    write_formatted(all_data, buffer)
    return named_output(
        buffer.getvalue(), file_name=file_name, default_name=default_file_name(source)
    )


def _read_csv(source):
    """A CSV as UTF-8, or else as Windows' own encoding (CSV saved by Excel)."""
    try:
        return pd.read_csv(source)
    except UnicodeDecodeError:
        if hasattr(source, "seek"):
            source.seek(0)
        return pd.read_csv(source, encoding="cp1252")


def _without_pandas_suffixes(columns):
    """*columns* without the ".1", ".2" pandas adds to a repeated name.

    Only where the name before the suffix is an earlier column, so a name such
    as "pH 7.4" keeps its number.
    """
    names = []
    for index, column in enumerate(columns):
        base = re.sub(r"\.\d+$", "", column) if isinstance(column, str) else column
        names.append(base if base in list(columns[:index]) else column)
    return names


def write_formatted(all_data, target):
    """Clean each sheet of *all_data* and write them to *target* (path or file)."""
    # Clean column names and process date columns for each sheet/dataframe
    for sheet_name, df in all_data.items():
        # Remove the ".#" suffix pandas gives a repeated column name
        all_data[sheet_name].columns = _without_pandas_suffixes(df.columns)

        # Process date columns (by position: a name can now repeat)
        for col_index, col_name in enumerate(df.columns):
            if "date" in str(col_name).lower():
                column = df.iloc[:, col_index]
                # Convert column to string for pattern matching
                date_strings = column.astype(str)

                # Check if any values match patterns with leading zeros in month or
                # day (mm/dd/yyyy format)
                has_leading_zeros = date_strings.str.match(r"^0\d/|/0\d/").any()

                if has_leading_zeros:
                    try:
                        # First convert to datetime if not already
                        if not pd.api.types.is_datetime64_any_dtype(column):
                            column = pd.to_datetime(column, errors="coerce")
                        dates = column.apply(format_date_without_leading_zeros)
                        df.isetitem(col_index, dates)
                    except Exception as e:
                        # If conversion fails, keep original data
                        logger.warning(
                            "Could not process date column %r (%s)",
                            col_name,
                            type(e).__name__,
                        )

    # Create a Pandas Excel writer using XlsxWriter as the engine
    writer = pd.ExcelWriter(
        target,
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_numbers": True}},
    )

    # Process each sheet
    for sheet_name, df in all_data.items():
        # Convert the dataframe to an XlsxWriter Excel object
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # Create a format to set matched columns to text type
        text_format = workbook.add_format({"num_format": "@"})

        # Apply formatting to columns based on their content
        for col_num in range(len(df.columns)):
            if has_range_pattern(df.iloc[:, col_num]):
                worksheet.set_column(col_num, col_num, None, text_format)

    # Close the Pandas Excel writer and output the Excel file
    writer.close()
