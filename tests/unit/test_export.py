from datetime import datetime

import numpy as np
import openpyxl
import pandas as pd

from clinical_reporting.export import get_excel_formats, to_short_date_string


def test_to_short_date_string_converts_datetime_like_values():
    assert to_short_date_string(datetime(2025, 11, 11)) == "11/11/2025"
    assert to_short_date_string(pd.Timestamp("2025-01-05")) == "1/5/2025"
    assert to_short_date_string(np.datetime64("2025-01-05")) == "1/5/2025"
    # NaT-like values become an empty string.
    assert to_short_date_string(pd.NaT) == ""
    # Non-datetime values pass through unchanged.
    assert to_short_date_string("N/A") == "N/A"
    assert to_short_date_string(1) == 1
    assert to_short_date_string(None) is None


def test_object_dtype_dates_export_as_text_not_datetimes(tmp_path):
    """Regression: a "D+28"-style object column holding datetime objects must be
    written to Excel as plain short-date text, not native datetime cells."""
    df = pd.DataFrame(
        {
            "Subject": ["001", "002", "003"],
            # object dtype: datetime objects mixed with a non-date value
            "D+28": pd.Series(
                [datetime(2025, 11, 11), "N/A", datetime(2025, 1, 5)], dtype=object
            ),
        }
    )

    # Mirror the export conversion in export.prepare_export_dataframe.
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series) or series.dtype == object:
            df[col] = series.apply(to_short_date_string)

    out_path = tmp_path / "report.xlsx"
    df.to_excel(out_path, index=False, sheet_name="Report")

    worksheet = openpyxl.load_workbook(out_path).active
    d28_cells = [worksheet.cell(row=r, column=2) for r in (2, 3, 4)]

    # All values are plain strings ("s"), none are native Excel datetimes ("d").
    assert [c.value for c in d28_cells] == ["11/11/2025", "N/A", "1/5/2025"]
    assert all(c.data_type == "s" for c in d28_cells)
    assert all(c.number_format == "General" for c in d28_cells)


def _has_thin_border(cell):
    sides = (cell.border.left, cell.border.right, cell.border.top, cell.border.bottom)
    return all(side.style == "thin" for side in sides)


def test_get_excel_formats_styles_worksheet(tmp_path):
    """get_excel_formats: bold/wrapped/bordered header, bordered middle-left data,
    and auto-fitted column widths."""
    df = pd.DataFrame(
        {
            "Subject": ["001", "002"],
            # Multi-line header that should wrap and drive the column width.
            "D+28 \n(based on FIRST infusion)": ["11/11/2025", "N/A"],
        }
    )

    out_path = tmp_path / "styled.xlsx"
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
        get_excel_formats(writer.book, writer.sheets["Report"], df)

    worksheet = openpyxl.load_workbook(out_path).active
    header_cells = [worksheet.cell(row=1, column=c) for c in (1, 2)]
    data_cells = [worksheet.cell(row=2, column=c) for c in (1, 2)]

    # Header: bold, wrapped, bordered, left + middle aligned.
    assert all(c.font.bold for c in header_cells)
    assert all(c.alignment.wrap_text for c in header_cells)
    assert all(_has_thin_border(c) for c in header_cells)
    assert all(
        c.alignment.horizontal == "left" and c.alignment.vertical == "center"
        for c in header_cells
    )

    # Data: not bold, bordered, left + middle aligned.
    assert not any(c.font.bold for c in data_cells)
    assert all(_has_thin_border(c) for c in data_cells)
    assert all(
        c.alignment.horizontal == "left" and c.alignment.vertical == "center"
        for c in data_cells
    )

    # autofit set explicit (non-default) widths on every column.
    assert worksheet.column_dimensions["A"].width is not None
    assert worksheet.column_dimensions["B"].width is not None
