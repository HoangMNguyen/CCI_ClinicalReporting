"""Pieces several pages share."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QComboBox

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


class CellComboBox(QComboBox):
    """A combo box in a table cell that ignores the wheel unless it has focus.

    Scrolling the table over it must not pick another entry by the way.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
