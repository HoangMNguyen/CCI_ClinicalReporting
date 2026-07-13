"""Report export helpers.

Extracted from the UI's run/export flow so the exact same Excel/CSV output can
be produced headlessly -- from scripts, batch jobs, tool chains, or a future
API -- without importing any Qt code.

The low-level styling and date-rendering helpers live in
:mod:`clinical_reporting.services.excel`; this module composes them into
ready-to-call export functions.
"""

from __future__ import annotations

import io

import pandas as pd

from clinical_reporting.services.excel import get_excel_formats, to_short_date_string

DEFAULT_SHEET_NAME = "Report"


def prepare_export_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with datetime-like values rendered as short dates.

    Excel auto-formats datetime cells as full datetimes; converting them to
    ``m/d/yyyy`` strings keeps the rendered output as plain short dates. Object
    dtype columns (e.g. ``"D+28"``) can hold datetime objects that
    ``select_dtypes("datetime")`` misses, so those are converted cell-by-cell
    while leaving non-date values untouched.
    """
    export_df = df.copy()
    for col in export_df.columns:
        series = export_df[col]
        if pd.api.types.is_datetime64_any_dtype(series) or series.dtype == object:
            export_df[col] = series.apply(to_short_date_string)
    return export_df


def _write_styled_excel(export_df: pd.DataFrame, target, sheet_name: str) -> None:
    """Write ``export_df`` to ``target`` (path or buffer) with standard styling."""
    with pd.ExcelWriter(target, engine="xlsxwriter") as writer:
        export_df.to_excel(writer, index=False, sheet_name=sheet_name)
        get_excel_formats(writer.book, writer.sheets[sheet_name], export_df)


def write_xlsx(df: pd.DataFrame, path: str, *, sheet_name: str = DEFAULT_SHEET_NAME) -> str:
    """Write ``df`` to a styled ``.xlsx`` file and return the path.

    Applies the standard report styling (bold wrapped headers, thin borders,
    left/middle alignment, auto-fitted columns) and renders datetime values as
    short ``m/d/yyyy`` strings.
    """
    export_df = prepare_export_dataframe(df)
    _write_styled_excel(export_df, path, sheet_name)
    return path


def dataframe_to_xlsx_bytes(df: pd.DataFrame, *, sheet_name: str = DEFAULT_SHEET_NAME) -> bytes:
    """Render ``df`` to styled ``.xlsx`` bytes.

    Useful for streaming a report back from an API or piping it to another
    program without touching the filesystem.
    """
    export_df = prepare_export_dataframe(df)
    buffer = io.BytesIO()
    _write_styled_excel(export_df, buffer, sheet_name)
    return buffer.getvalue()


def write_csv(df: pd.DataFrame, path: str) -> str:
    """Write ``df`` to a CSV file (short-date formatted) and return the path."""
    export_df = prepare_export_dataframe(df)
    export_df.to_csv(path, index=False)
    return path
