"""Export reports as styled XLSX files, XLSX bytes, or CSV files."""

from __future__ import annotations

import io
from datetime import date, datetime

import numpy as np
import pandas as pd

DEFAULT_SHEET_NAME = "Report"


def to_short_date_string(value):
    """Convert a datetime-like value to an ``m/d/yyyy`` string."""
    if isinstance(value, (pd.Timestamp, datetime, date, np.datetime64)):
        timestamp = pd.Timestamp(value)
        return (
            ""
            if pd.isna(timestamp)
            else f"{timestamp.month}/{timestamp.day}/{timestamp.year}"
        )
    return value


def get_excel_formats(workbook, worksheet, dataframe):
    """Apply the standard header, border, alignment, and sizing styles."""
    base_format = {
        "font_name": "Calibri",
        "font_size": 11,
        "border": 1,
        "align": "left",
        "valign": "vcenter",
    }
    data_format = workbook.add_format(base_format)
    header_format = workbook.add_format(
        {**base_format, "bold": True, "text_wrap": True}
    )

    column_count = len(dataframe.columns)
    if column_count:
        worksheet.set_column(0, column_count - 1, None, data_format)
    for col_index, column_name in enumerate(dataframe.columns):
        worksheet.write(0, col_index, str(column_name), header_format)
    worksheet.autofit()


def prepare_export_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Copy a dataframe and render datetime-like cells as short dates."""
    export_df = df.copy()
    for col in export_df.columns:
        series = export_df[col]
        if pd.api.types.is_datetime64_any_dtype(series) or series.dtype == object:
            export_df[col] = series.apply(to_short_date_string)
    return export_df


def _write_styled_excel(export_df: pd.DataFrame, target, sheet_name: str) -> None:
    with pd.ExcelWriter(target, engine="xlsxwriter") as writer:
        export_df.to_excel(writer, index=False, sheet_name=sheet_name)
        get_excel_formats(writer.book, writer.sheets[sheet_name], export_df)


def write_xlsx(
    df: pd.DataFrame, path: str, *, sheet_name: str = DEFAULT_SHEET_NAME
) -> str:
    """Write a dataframe to a styled XLSX file and return its path."""
    _write_styled_excel(prepare_export_dataframe(df), path, sheet_name)
    return path


def dataframe_to_xlsx_bytes(
    df: pd.DataFrame, *, sheet_name: str = DEFAULT_SHEET_NAME
) -> bytes:
    """Render a dataframe to styled XLSX bytes."""
    buffer = io.BytesIO()
    _write_styled_excel(prepare_export_dataframe(df), buffer, sheet_name)
    return buffer.getvalue()


def write_csv(df: pd.DataFrame, path: str) -> str:
    """Write a short-date-formatted dataframe to CSV and return its path."""
    prepare_export_dataframe(df).to_csv(path, index=False)
    return path


__all__ = [
    "DEFAULT_SHEET_NAME",
    "dataframe_to_xlsx_bytes",
    "get_excel_formats",
    "prepare_export_dataframe",
    "to_short_date_string",
    "write_csv",
    "write_xlsx",
]
