"""Pieces several pages share."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtWidgets import QAbstractItemView

from cci_ui.widgets.tables import ColumnSpec, configure_columns, style_table
from cci_ui.widgets.views import PlaceholderTableWidget


def make_table(
    headers: Sequence[str],
    columns: Sequence[ColumnSpec],
    *,
    placeholder: str = "",
    row_numbers: bool = False,
    selection: QAbstractItemView.SelectionMode = (
        QAbstractItemView.SelectionMode.SingleSelection
    ),
) -> PlaceholderTableWidget:
    """A styled table with *headers* and one column rule per header.

    *row_numbers* shows row numbers, for tables whose messages refer to rows
    ("Static filter 2 must have an item").
    """
    table = PlaceholderTableWidget(placeholder)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    style_table(table, row_numbers=row_numbers, selection=selection)
    configure_columns(table, columns)
    return table
