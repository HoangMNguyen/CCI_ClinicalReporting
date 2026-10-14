"""Pieces several pages share."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QLineEdit,
    QWidget,
)

from cci_ui.theme.manager import set_invalid
from cci_ui.widgets.tables import (
    ColumnSpec,
    ProblemCellDelegate,
    configure_columns,
    style_table,
)
from cci_ui.widgets.views import PlaceholderTableWidget

#: An item box's tooltip after its item, while it has no problem.
ITEM_TIP = "Pick an item, or type to find one"


def make_table(
    headers: Sequence[str],
    columns: Sequence[ColumnSpec],
    *,
    placeholder: str = "",
    row_numbers: bool = False,
    selection: QAbstractItemView.SelectionMode = (
        QAbstractItemView.SelectionMode.SingleSelection
    ),
    controls: bool = False,
) -> PlaceholderTableWidget:
    """A styled table with *headers* and one column rule per header.

    *row_numbers* shows row numbers, for tables whose messages refer to rows
    ("Static filter 2 must have an item"). *controls* is for tables whose
    cells hold dropdowns or fields (see :func:`style_table`). Its cells can
    be marked with a problem (:func:`cci_ui.widgets.tables.mark_cell`).
    """
    table = PlaceholderTableWidget(placeholder)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    style_table(table, row_numbers=row_numbers, selection=selection, controls=controls)
    configure_columns(table, columns)
    table.setItemDelegate(ProblemCellDelegate(table))
    return table


def show_problem(widget: QWidget, problem: str, tip: str = "") -> None:
    """Mark *widget* red with *problem* as its tooltip; "" clears it to *tip*."""
    set_invalid(widget, bool(problem))
    widget.setToolTip(problem or tip)


class CellComboBox(QComboBox):
    """A combo box in a table cell that ignores the wheel unless it has focus.

    Scrolling the table over it must not pick another entry by the way. It
    says when it takes the focus (``focused``), so its row can be selected.
    """

    focused = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def focusInEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().focusInEvent(event)
        self.focused.emit()

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class FocusEdit(QLineEdit):
    """A line edit that says when it takes the focus (its row gets selected)."""

    focused = Signal()

    def focusInEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().focusInEvent(event)
        self.focused.emit()


class ItemBox(CellComboBox):
    """A row's item: the items it can take; typing filters them.

    Text typed that isn't one of them gives way to the item picked when the
    box loses the focus. Its tooltip names the item whole (a narrow cell cuts
    a long one), then its problem (:meth:`set_problem`) or :data:`ITEM_TIP`.
    """

    def __init__(self, choices: Sequence[str], item: str, parent=None) -> None:
        super().__init__(parent)
        self._problem = ""
        self.setEditable(True)
        self.setLineEdit(FocusEdit())
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.addItems(list(choices))
        completer = QCompleter(self.model(), self)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(completer)
        self.setCurrentIndex(self.findText(item) if item else -1)
        self.lineEdit().setPlaceholderText("Pick an item")
        self.lineEdit().setCursorPosition(0)
        self._show_tip(item)
        self.currentTextChanged.connect(self._show_tip)
        self.lineEdit().editingFinished.connect(self._show_picked)

    def set_problem(self, problem: str) -> None:
        """Mark the box red with *problem* after its item in the tooltip; "" clears it."""
        self._problem = problem
        set_invalid(self, bool(problem))
        self._show_tip(self.currentText())

    def _show_tip(self, text: str) -> None:
        tips = (text, self._problem or ITEM_TIP)
        self.setToolTip("\n".join(tip for tip in tips if tip))

    def _show_picked(self) -> None:
        index = self.currentIndex()
        picked = self.itemText(index) if index >= 0 else ""
        if self.currentText() != picked:
            self.setEditText(picked)
        self.lineEdit().setCursorPosition(0)
