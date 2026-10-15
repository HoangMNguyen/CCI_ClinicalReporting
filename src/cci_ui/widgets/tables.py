"""Table setup shared by every table: column rules, row height, and +/− buttons.

Instead of computing column widths by hand on every resize, each column gets
a rule (:class:`ColumnSpec`) and Qt's header keeps it: ``stretch`` columns
share the spare width, ``contents`` columns fit their text, ``fixed``
columns keep a width, and ``interactive`` columns start at a width the user
can drag. Row height follows the density, taller in tables whose cells hold
dropdowns or fields.

A column whose cells the user can change is *editable*: its header shows a
pencil after the label (:class:`EditableColumnsHeader`). In such a column, a
plain-text cell that can be typed in opens on one click and shows an I-beam
pointer, and a cell that can't (no dropdown or field in it, not editable or
not enabled) is grey.

A cell holding a problem (:func:`mark_cell`) is drawn with a red border and
red text by a :class:`ProblemCellDelegate`, and says why in its tooltip.
"""

from __future__ import annotations

import weakref
from dataclasses import dataclass
from functools import partial
from typing import Iterable, Optional, Sequence, Set

import shiboken6
from PySide6.QtCore import (
    QEvent,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QRect,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionHeaderV2,
    QTableView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName, icon
from cci_ui.theme.manager import current, repolish, theme_events
from cci_ui.theme.palette import qcolor
from cci_ui.theme.qss import HEADER_LABEL_PX, HEADER_LABEL_WEIGHT, register_qss
from cci_ui.widgets.buttons import button_group, icon_button
from cci_ui.widgets.labels import text_label

register_qss(
    """
QTableView[rowLines="true"]::item {
    border-bottom: 1px solid ${separator};
}
/* Rows holding dropdowns or fields leave them 2px above and below (the row
   line is the last of the 2px below); a cell's text editor gets the same. */
QTableView[cciControls="true"]::item {
    padding: 2px 8px;
}
QTableView[cciControls="true"][rowLines="true"]::item {
    padding: 2px 8px 1px 8px;
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

#: Size of the pencil after an editable column's header label.
_EDIT_MARK = 12
#: Space between the label and the pencil.
_EDIT_MARK_GAP = 4
#: A cell the user can type in is both.
_TYPING = Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled
#: Ctrl- and Shift-clicks select rows; they never open a cell.
_SELECTING = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
#: The item data role holding a cell's problem (see :func:`mark_cell`).
PROBLEM_ROLE = Qt.ItemDataRole.UserRole + 100


@dataclass(frozen=True)
class ColumnSpec:
    """How one column uses width; ``width`` applies to fixed/interactive.

    ``editable`` marks a column whose cells the user can change (plain-text
    cells, dropdowns or fields).
    """

    mode: str = "stretch"
    width: Optional[int] = None
    editable: bool = False

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(
                f"Unknown column mode {self.mode!r}; expected one of {MODES}"
            )
        if self.mode in ("fixed", "interactive") and not self.width:
            raise ValueError(f"A {self.mode} column needs a width")


def _label_font(font: QFont) -> QFont:
    """The font the stylesheet gives header labels, in *font*'s family."""
    label = QFont(font)
    label.setPixelSize(HEADER_LABEL_PX)
    label.setWeight(QFont.Weight(HEADER_LABEL_WEIGHT))
    return label


class EditableColumnsHeader(QHeaderView):
    """A horizontal header with a pencil after each editable column's label.

    :func:`configure_columns` gives a table one when it has an editable
    column; a view with a header class of its own derives it from this one
    and marks its columns with :meth:`set_editable_columns`. The pencil
    follows a left-aligned label, which is shortened first to keep room for
    it; a section sized to its contents makes room for it too.
    """

    def __init__(
        self,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(orientation, parent)
        self._editable: Set[int] = set()
        self._pencil = icon(IconName.EDIT, "tertiary")
        # The pencil takes the new theme's color.
        theme_events().changed.connect(self._repaint)

    def set_editable_columns(self, columns: Iterable[int]) -> None:
        """Mark exactly *columns* (logical indexes) editable."""
        editable = set(columns)
        if editable == self._editable:
            return
        self._editable = editable
        if self.count():
            # Sections sized to their contents make room for the pencil.
            self.headerDataChanged(self.orientation(), 0, self.count() - 1)
        self.viewport().update()

    def is_column_editable(self, column: int) -> bool:
        """Whether *column* (a logical index) shows the pencil."""
        return column in self._editable

    def paintSection(self, painter, rect, logical_index) -> None:  # noqa: N802 (Qt override)
        if logical_index not in self._editable:
            super().paintSection(painter, rect, logical_index)
            return
        option = QStyleOptionHeaderV2()
        self.initStyleOption(option)
        self.initStyleOptionForIndex(option, logical_index)
        option.rect = rect
        style = self.style()
        label = style.subElementRect(QStyle.SubElement.SE_HeaderLabel, option, self)
        metrics = QFontMetrics(_label_font(self.font()))
        text = self.model().headerData(
            logical_index, self.orientation(), Qt.ItemDataRole.DisplayRole
        )
        option.text = metrics.elidedText(
            str(text or ""),
            Qt.TextElideMode.ElideRight,
            max(0, label.width() - _EDIT_MARK_GAP - _EDIT_MARK),
        )
        style.drawControl(QStyle.ControlElement.CE_Header, option, painter, self)
        x = label.left() + metrics.horizontalAdvance(option.text) + _EDIT_MARK_GAP
        if x + _EDIT_MARK <= label.right() + 1:
            mark = QRect(0, 0, _EDIT_MARK, _EDIT_MARK)
            mark.moveCenter(label.center())
            mark.moveLeft(x)
            self._pencil.paint(painter, mark)

    def sectionSizeFromContents(self, logical_index) -> QSize:  # noqa: N802 (Qt override)
        size = super().sectionSizeFromContents(logical_index)
        if logical_index in self._editable:
            size.setWidth(size.width() + _EDIT_MARK_GAP + _EDIT_MARK)
        return size

    def _repaint(self, *_args) -> None:
        self.viewport().update()


def is_editable_column(view: QTableView, column: int) -> bool:
    """Whether *view*'s *column* is editable (its header shows the pencil)."""
    header = view.horizontalHeader()
    return isinstance(header, EditableColumnsHeader) and header.is_column_editable(
        column
    )


def _editable_columns_header(view: QTableView) -> EditableColumnsHeader:
    """*view*'s header, replaced by an :class:`EditableColumnsHeader` if need be.

    The new header keeps the old one's state: section sizes and resize
    modes, alignment, and whether it shows.
    """
    header = view.horizontalHeader()
    if isinstance(header, EditableColumnsHeader):
        return header
    state = header.saveState()
    hidden = header.isHidden()
    replacement = EditableColumnsHeader(Qt.Orientation.Horizontal, view)
    view.setHorizontalHeader(replacement)  # Deletes the old header.
    replacement.restoreState(state)
    replacement.setHidden(hidden)
    return replacement


def _takes_typing(index: QModelIndex) -> bool:
    return (index.flags() & _TYPING) == _TYPING


def _plain_left_click(event) -> bool:
    return event.button() == Qt.MouseButton.LeftButton and not (
        event.modifiers() & _SELECTING
    )


class _TypingCells(QObject):
    """The cells of a table's editable columns: one click types, unused is grey.

    A cell with no widget in it that is enabled and editable opens its
    editor on a plain left click (not Ctrl or Shift, which select rows),
    once the view has handled the click; double-click, F2 and typing open it
    as before. The pointer is an I-beam over it. The column's other cells
    without a widget are unused and drawn grey, under the row line.
    """

    def __init__(self, view: QTableView) -> None:
        super().__init__(view)
        self._view = view
        self._pressed = QPersistentModelIndex()
        viewport = view.viewport()
        # Hover events say where the pointer is (_IdleMoveFilter drops moves).
        viewport.setAttribute(Qt.WidgetAttribute.WA_Hover)
        viewport.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 (Qt override)
        kind = event.type()
        if kind in (QEvent.Type.HoverEnter, QEvent.Type.HoverMove):
            if self._types_in(self._view.indexAt(event.position().toPoint())):
                watched.setCursor(Qt.CursorShape.IBeamCursor)
            else:
                watched.unsetCursor()
        elif kind == QEvent.Type.HoverLeave:
            watched.unsetCursor()
        elif kind == QEvent.Type.MouseButtonPress:
            index = self._view.indexAt(event.position().toPoint())
            typed = _plain_left_click(event) and self._types_in(index)
            self._pressed = QPersistentModelIndex(index if typed else QModelIndex())
        elif kind == QEvent.Type.MouseButtonRelease:
            pressed, self._pressed = self._pressed, QPersistentModelIndex()
            index = self._view.indexAt(event.position().toPoint())
            if (
                _plain_left_click(event)
                and pressed.isValid()
                and (index.row(), index.column()) == (pressed.row(), pressed.column())
            ):
                QTimer.singleShot(0, self, partial(self._edit, pressed))
        elif kind == QEvent.Type.Paint:
            self._paint_unused(watched, event.rect())
        return False

    def _types_in(self, index: QModelIndex) -> bool:
        """Whether *index* is a plain-text cell of an editable column to type in."""
        view = self._view
        return (
            index.isValid()
            and is_editable_column(view, index.column())
            and view.indexWidget(index) is None
            and _takes_typing(index)
        )

    def _edit(self, pressed: QPersistentModelIndex) -> None:
        if not pressed.isValid():
            return
        index = self._view.model().index(pressed.row(), pressed.column())
        if self._types_in(index):
            self._view.edit(index)

    def _paint_unused(self, viewport: QWidget, area: QRect) -> None:
        view = self._view
        model = view.model()
        if model is None:
            return
        columns = [
            column
            for column in range(model.columnCount())
            if is_editable_column(view, column) and not view.isColumnHidden(column)
        ]
        top = view.rowAt(area.top())
        if not columns or top < 0:
            return
        bottom = view.rowAt(area.bottom())
        if bottom < 0:
            bottom = model.rowCount() - 1
        grey = qcolor(current().colors.bg_surface_alt)
        painter = QPainter(viewport)
        for row in range(top, bottom + 1):
            for column in columns:
                index = model.index(row, column)
                if view.indexWidget(index) is None and not _takes_typing(index):
                    painter.fillRect(view.visualRect(index), grey)
        painter.end()


class ProblemCellDelegate(QStyledItemDelegate):
    """Draws a cell holding a problem (:data:`PROBLEM_ROLE`) in the danger colors.

    Its text is drawn in the danger text color and a 1px danger border goes
    inside the cell, over the selection and the grey of unused cells. The
    colors are read at paint time, so they follow theme changes.
    """

    def initStyleOption(self, option, index) -> None:  # noqa: N802 (Qt override)
        super().initStyleOption(option, index)
        if index.data(PROBLEM_ROLE):
            option.palette.setColor(
                QPalette.ColorRole.Text, qcolor(current().colors.danger_text)
            )

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        if not index.data(PROBLEM_ROLE):
            return
        painter.save()
        painter.setPen(QPen(qcolor(current().colors.danger), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(option.rect.adjusted(1, 1, -2, -2))
        painter.restore()


def mark_cell(item: QTableWidgetItem, problem: str, tip: str = "") -> None:
    """Mark *item* with *problem* ("" clears it); its tooltip says why, else *tip*.

    Its table needs a :class:`ProblemCellDelegate` to draw the mark. Changes
    nothing when the cell already shows them, and never emits ``itemChanged``
    (edit handlers listen to it).
    """
    marked = problem or None
    tooltip = problem or tip
    if item.data(PROBLEM_ROLE) == marked and item.toolTip() == tooltip:
        return
    # The model still reports the change, so the view repaints the cell.
    table = item.tableWidget()
    blocked = table.blockSignals(True) if table is not None else False
    try:
        item.setData(PROBLEM_ROLE, marked)
        item.setToolTip(tooltip)
    finally:
        if table is not None:
            table.blockSignals(blocked)


def configure_columns(view: QTableView, specs: Sequence[ColumnSpec]) -> None:
    """Apply one :class:`ColumnSpec` per column, in order.

    Call it after the columns exist (``setColumnCount`` or a model is set);
    resize rules on columns that don't exist yet are silently dropped by Qt.
    Editable columns get the pencil, and their plain-text cells open on one
    click.
    """
    header = view.horizontalHeader()
    if len(specs) > header.count():
        raise ValueError(
            f"{len(specs)} column rules for {header.count()} columns; "
            "set the columns before configuring them"
        )
    editable = [column for column, spec in enumerate(specs) if spec.editable]
    if editable or isinstance(header, EditableColumnsHeader):
        header = _editable_columns_header(view)
        header.set_editable_columns(editable)
    direct = Qt.FindChildOption.FindDirectChildrenOnly
    if editable and view.findChild(_TypingCells, "", direct) is None:
        _TypingCells(view)
    header.setStretchLastSection(False)
    for column, spec in enumerate(specs):
        header.setSectionResizeMode(column, _RESIZE_MODES[spec.mode])
        if spec.width:
            header.resizeSection(column, spec.width)


# Tables whose row height follows the density; weak so deleted tables drop out.
_styled_tables: "weakref.WeakSet[QTableView]" = weakref.WeakSet()
_following_density = False


def _apply_row_height(view: QTableView) -> None:
    metrics = current().metrics
    row_h = metrics.editor_row_h if view.property("cciControls") else metrics.row_h
    rows = view.verticalHeader()
    rows.setMinimumSectionSize(row_h)
    rows.setDefaultSectionSize(row_h)


def _refresh_row_heights() -> None:
    for view in list(_styled_tables):
        if shiboken6.isValid(view):  # Python may outlive a deleted table.
            _apply_row_height(view)
        else:
            _styled_tables.discard(view)


class _IdleMoveFilter(QObject):
    """Drops pointer moves with no button held before the view sees them.

    The theme's hover rule turns on mouse tracking, and a tracked move over a
    cell gives that cell's widget (a dropdown) the focus. Hover painting uses
    hover events, so it keeps working; drags hold a button, so they pass.
    """

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 (Qt override)
        return (
            event.type() == QEvent.Type.MouseMove
            and event.buttons() == Qt.MouseButton.NoButton
        )


def style_table(
    view: QTableView,
    *,
    row_lines: bool = True,
    alternating: bool = False,
    row_numbers: bool = False,
    selection: QAbstractItemView.SelectionMode = _SINGLE_SELECTION,
    embedded: bool = False,
    controls: bool = False,
) -> None:
    """Give *view* the standard look: left headers, row lines, density rows.

    *row_numbers* keeps the vertical header (e.g. filters, whose messages say
    "Static filter 2"). *embedded* drops the view's own border when it sits
    inside a card. *controls* is for tables whose cells hold dropdowns or
    fields: their rows are ``editor_row_h`` tall, leaving the controls 2px
    above and below.

    Passing the pointer over a cell's widget doesn't focus it.
    """
    view.setShowGrid(False)
    view.setProperty("rowLines", row_lines)
    view.setProperty("cciControls", controls)
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
    viewport = view.viewport()
    viewport.installEventFilter(_IdleMoveFilter(viewport))
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
    "PROBLEM_ROLE",
    "ColumnSpec",
    "EditableColumnsHeader",
    "ProblemCellDelegate",
    "TableToolbar",
    "configure_columns",
    "is_editable_column",
    "mark_cell",
    "style_table",
    "table_card",
]
