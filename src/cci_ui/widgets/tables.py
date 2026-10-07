"""Table setup shared by every table: column rules, row height, and +/− buttons.

Instead of computing column widths by hand on every resize, each column gets
a rule (:class:`ColumnSpec`) and Qt's header keeps it: ``stretch`` columns
share the spare width, ``contents`` columns fit their text, ``fixed``
columns keep a width, and ``interactive`` columns start at a width the user
can drag. Row height follows the density.
"""

from __future__ import annotations

import weakref
from dataclasses import dataclass
from typing import Optional, Sequence

import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.theme.manager import current, repolish, theme_events
from cci_ui.theme.qss import register_qss
from cci_ui.widgets.buttons import button_group, icon_button
from cci_ui.widgets.labels import text_label

register_qss(
    """
QTableView[rowLines="true"]::item {
    border-bottom: 1px solid ${separator};
}
"""
)

MODES = ("stretch", "contents", "fixed", "interactive")
_SINGLE_SELECTION = QAbstractItemView.SelectionMode.SingleSelection
_RESIZE_MODES = {
    "stretch": QHeaderView.ResizeMode.Stretch,
    "contents": QHeaderView.ResizeMode.ResizeToContents,
    "fixed": QHeaderView.ResizeMode.Fixed,
    "interactive": QHeaderView.ResizeMode.Interactive,
}


@dataclass(frozen=True)
class ColumnSpec:
    """How one column uses width; ``width`` applies to fixed/interactive."""

    mode: str = "stretch"
    width: Optional[int] = None

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(
                f"Unknown column mode {self.mode!r}; expected one of {MODES}"
            )
        if self.mode in ("fixed", "interactive") and not self.width:
            raise ValueError(f"A {self.mode} column needs a width")


def configure_columns(view: QTableView, specs: Sequence[ColumnSpec]) -> None:
    """Apply one :class:`ColumnSpec` per column, in order.

    Call it after the columns exist (``setColumnCount`` or a model is set);
    resize rules on columns that don't exist yet are silently dropped by Qt.
    """
    header = view.horizontalHeader()
    if len(specs) > header.count():
        raise ValueError(
            f"{len(specs)} column rules for {header.count()} columns; "
            "set the columns before configuring them"
        )
    header.setStretchLastSection(False)
    for column, spec in enumerate(specs):
        header.setSectionResizeMode(column, _RESIZE_MODES[spec.mode])
        if spec.width:
            header.resizeSection(column, spec.width)


# Tables whose row height follows the density; weak so deleted tables drop out.
_styled_tables: "weakref.WeakSet[QTableView]" = weakref.WeakSet()
_following_density = False


def _apply_row_height(view: QTableView) -> None:
    row_h = current().metrics.row_h
    rows = view.verticalHeader()
    rows.setMinimumSectionSize(row_h)
    rows.setDefaultSectionSize(row_h)


def _refresh_row_heights() -> None:
    for view in list(_styled_tables):
        if shiboken6.isValid(view):  # Python may outlive a deleted table.
            _apply_row_height(view)
        else:
            _styled_tables.discard(view)


def style_table(
    view: QTableView,
    *,
    row_lines: bool = True,
    alternating: bool = False,
    row_numbers: bool = False,
    selection: QAbstractItemView.SelectionMode = _SINGLE_SELECTION,
    embedded: bool = False,
) -> None:
    """Give *view* the standard look: left headers, row lines, density rows.

    *row_numbers* keeps the vertical header (e.g. filters, whose messages say
    "Static filter 2"). *embedded* drops the view's own border when it sits
    inside a card.
    """
    view.setShowGrid(False)
    view.setProperty("rowLines", row_lines)
    view.setAlternatingRowColors(alternating)
    view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    view.setSelectionMode(selection)
    view.setWordWrap(False)
    view.setTextElideMode(Qt.TextElideMode.ElideRight)
    view.verticalHeader().setVisible(row_numbers)
    header = view.horizontalHeader()
    header.setDefaultAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    header.setHighlightSections(False)
    if embedded:
        view.setProperty("cciRole", "embedded")
    repolish(view)
    _apply_row_height(view)
    global _following_density
    if not _following_density:
        theme_events().changed.connect(_refresh_row_heights)
        _following_density = True
    _styled_tables.add(view)


def table_card(view: QAbstractItemView) -> QFrame:
    """Put *view* (a table or list) in a rounded card; views can't round corners."""
    card = QFrame()
    card.setProperty("cciRole", "card")
    view.setProperty("cciRole", "embedded")
    repolish(view)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(1, 1, 1, 1)
    layout.addWidget(view)
    return card


class TableToolbar(QWidget):
    """Joined +/− buttons under a table, then a caption."""

    def __init__(
        self,
        *,
        add_tooltip: str = "Add",
        remove_tooltip: str = "Remove selected",
        caption: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.add_button = icon_button(IconName.ADD, add_tooltip, variant="secondary")
        self.remove_button = icon_button(
            IconName.REMOVE, remove_tooltip, variant="secondary"
        )

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)
        self._layout.addWidget(button_group(self.add_button, self.remove_button))
        self.caption_label = text_label(caption, style="caption")
        self._layout.addWidget(self.caption_label)
        # Only after parenting (see cci_ui.widgets).
        self.caption_label.setVisible(bool(caption))
        self._layout.addStretch(1)


__all__ = [
    "ColumnSpec",
    "TableToolbar",
    "configure_columns",
    "style_table",
    "table_card",
]
