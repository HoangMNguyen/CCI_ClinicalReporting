"""Excel rendering helpers used by the report exporter.

Provides the short-date conversion applied to datetime cells and the standard
worksheet styling (bold wrapped headers, thin borders, auto-fitted columns).
"""

from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd


def to_short_date_string(value):
    """Convert a datetime-like value to a short ``m/d/yyyy`` string.

    Used when exporting reports so Excel renders dates as plain short dates
    instead of auto-formatting them as full datetimes. Non-datetime values
    (strings, numbers, NaN) are returned unchanged, which keeps the other
    entries of mixed object-dtype columns (e.g. ``"D+28"``) intact.

    Args:
        value: The cell value to convert.

    Returns:
        A ``m/d/yyyy`` string for datetime-like values (empty string for NaT),
        otherwise the original value unchanged.
    """
    if isinstance(value, (pd.Timestamp, datetime, date, np.datetime64)):
        timestamp = pd.Timestamp(value)
        return "" if pd.isna(timestamp) else f"{timestamp.month}/{timestamp.day}/{timestamp.year}"
    return value


def get_excel_formats(workbook, worksheet, dataframe):
    """Apply the standard report styling to an exported xlsxwriter worksheet.

    Styling applied:
        * every cell is left- and middle-aligned with a thin (1px) border,
        * the header row is bold and wraps multi-line headers,
        * each column is auto-fitted to the width of its header and data.

    Args:
        workbook: The xlsxwriter workbook, used to create cell formats.
        worksheet: The xlsxwriter worksheet to style.
        dataframe: The DataFrame that was written to ``worksheet`` with
            ``index=False``; its column labels are used to rewrite the header
            row with the header format.
    """
    base_format = {
        "font_name": "Calibri",
        "font_size": 11,
        "border": 1,  # thin border on all four sides
        "align": "left",
        "valign": "vcenter",  # middle aligned, not bottom
    }
    data_format = workbook.add_format(base_format)
    header_format = workbook.add_format({**base_format, "bold": True, "text_wrap": True})

    column_count = len(dataframe.columns)
    if column_count:
        # Make the data format the column default; cells pandas wrote without an
        # explicit format inherit it. Width is left unset (None) so autofit can
        # size each column afterwards.
        worksheet.set_column(0, column_count - 1, None, data_format)

    # Rewrite the header row so it uses the bold, wrapped header format instead
    # of the default one pandas applied.
    for col_index, column_name in enumerate(dataframe.columns):
        worksheet.write(0, col_index, str(column_name), header_format)

    # Let xlsxwriter size every column to fit its contents (this measures the
    # rendered string width and respects wrapped multi-line headers).
    worksheet.autofit()
