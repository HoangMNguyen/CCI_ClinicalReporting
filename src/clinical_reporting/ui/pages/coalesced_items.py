"""Coalesced items: one item made from two or more items of a form.

The page keeps its own coalesced items (the drafts) until the user goes to
another step: :class:`CoalescedItemsMixin` edits them, previews each with
:func:`~clinical_reporting.coalescing.preview`, marks what stops them from
reaching the report with :func:`~clinical_reporting.coalescing.item_problems`
as they change, and, when the user leaves the page
(:meth:`CoalescedItemsMixin._apply_coalesced_step`, called by the window's
``apply_data_steps``), hands them to
:func:`~clinical_reporting.session.apply_coalesced_items`. Drafts with a
problem hold the step: nothing from it reaches the report, and its badge is
red. They are made from the forms of ``report.stacked_data`` (the loaded
forms and the stacked forms). Messages are worded in
:mod:`clinical_reporting.steps`; the page's own labels and hints are here.

- The Coalesced items table: Name | Form | Items, in order | Filled |
  Overlaps | When values overlap, a read-only summary of the drafts ("—"
  while one can't be built yet); a draft's Name is red with its problems.
- The editor of the selected draft: its form, name (one of its items' names
  or a new one) and what to do where values overlap; its items in order,
  each later one with an optional condition (a Filters operator and value
  tested on the value so far) and the rows it gives; and how its form's rows
  take their value. Each problem is marked on the field that fixes it.
- Two banners: what reaching the report did, and a standing one when the
  report's coalesced items lack a form or an item.

Loading a saved setting (when it changes the report's coalesced items)
replaces the drafts with the report's; a new Corelisting ZIP keeps them, and
they reach the new report as soon as it is loaded
(:meth:`CoalescedItemsMixin._forget_applied_coalesced_items`). Removing an
input drops those it leaves with nothing to be made from: all of them once
no input is left (see ``WidgetBaseMixin._drop_data_steps_without_input``).
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial
from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QStackedWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.theme.manager import current, theme_events
from cci_ui.theme.palette import qcolor
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.labels import section_label, text_label
from cci_ui.widgets.page import Page
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import ColumnSpec, mark_cell, table_card
from clinical_reporting import coalescing, feedback, steps
from clinical_reporting.coalescing import (
    CONDITION_OPERATORS,
    KEEP_EARLIER,
    REFUSE,
    CoalescedItem,
    Fill,
    Outcome,
)
from clinical_reporting.session import apply_coalesced_items

from ._common import CellComboBox, ItemBox, make_table, show_problem

#: The Coalesced items table's columns.
_ITEMS_COLUMNS = (
    ColumnSpec("interactive", 180),
    ColumnSpec("fixed", 110),
    ColumnSpec("stretch"),
    ColumnSpec("fixed", 80),
    ColumnSpec("fixed", 90),
    ColumnSpec("fixed", 180),
)
(
    _NAME_COLUMN,
    _FORM_COLUMN,
    _ITEMS_COLUMN,
    _FILLED_COLUMN,
    _OVERLAPS_COLUMN,
    _OVERLAP_COLUMN,
) = range(6)
#: The Coalesced items table shows at most this many rows before it scrolls.
ITEMS_TABLE_ROWS = 3.5

#: The editor's items table's columns: #, Item, condition, Value, Rows.
_FILLS_COLUMNS = (
    ColumnSpec("fixed", 44),
    ColumnSpec("stretch", editable=True),
    ColumnSpec("fixed", 290, editable=True),
    ColumnSpec("stretch", editable=True),
    ColumnSpec("fixed", 80),
)
_NUMBER_COLUMN, _ITEM_COLUMN, _CONDITION_COLUMN, _VALUE_COLUMN, _ROWS_COLUMN = range(5)
#: The editor's items table always has room for this many rows.
FILLS_TABLE_MIN_ROWS = 2
#: How many characters the Form and Name boxes are wide, whatever they list.
FORM_BOX_CHARS = 12
NAME_BOX_CHARS = 20

NO_COALESCED_ITEMS = (
    "No coalesced items. Use New coalesced item to make one from two or more "
    "items of a form."
)
SELECT_A_COALESCED_ITEM = (
    "Select a coalesced item above, or make one with New coalesced item."
)
PICK_ITEMS = "Pick its form and at least two of its items to see how it fills."
#: The condition cell of the first item, which has none.
STARTS_THE_VALUE = "starts the value"
#: A later item's condition entry for none (it fills empty values only).
NO_CONDITION = "—"
#: A count of a coalesced item that can't be built yet.
NOT_BUILT = "—"
#: "When values overlap": what each choice shows, by its value.
OVERLAP_CHOICES = {REFUSE: "Refuse", KEEP_EARLIER: "Keep the earlier value"}
CONDITION_TIP = (
    "Where the value so far meets this condition, this item replaces it. "
    "Empty values are always filled."
)

_READ_ONLY = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


class _ConditionBox(CellComboBox):
    """A later item's condition: none, or a Filters operator."""

    def __init__(self, operator: str, parent=None) -> None:
        super().__init__(parent)
        self.addItem(NO_CONDITION, "")
        for name in CONDITION_OPERATORS:
            self.addItem(name, name)
        self.setCurrentIndex(max(self.findData(operator), 0))
        self.setToolTip(CONDITION_TIP)


class _EditorPanel(QWidget):
    """The selected coalesced item's editor, or a message when none is selected."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.title = text_label("", style="headline")
        # Their width doesn't follow long form or item names, so the page
        # still fits the narrowest window.
        fixed_width = QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        self.form = QComboBox()
        self.form.setAccessibleName("Form")
        self.form.setSizeAdjustPolicy(fixed_width)
        self.form.setMinimumContentsLength(FORM_BOX_CHARS)
        self.name = QComboBox()
        self.name.setEditable(True)
        self.name.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name.lineEdit().setPlaceholderText("Name, e.g. Race")
        self.name.setAccessibleName("Name")
        self.name.setSizeAdjustPolicy(fixed_width)
        self.name.setMinimumContentsLength(NAME_BOX_CHARS)
        self.overlap = QComboBox()
        self.overlap.setAccessibleName("When values overlap")
        for value, text in OVERLAP_CHOICES.items():
            self.overlap.addItem(text, value)
        # Each label above its box, so the row fits the narrowest window.
        head = QGridLayout()
        head.setHorizontalSpacing(16)
        head.setVerticalSpacing(4)
        for column, (text, box) in enumerate(
            (
                ("Form", self.form),
                ("Name", self.name),
                ("When values overlap", self.overlap),
            )
        ):
            label = text_label(text, style="subheadline")
            label.setBuddy(box)
            head.addWidget(label, 0, column)
            head.addWidget(box, 1, column)
        head.setColumnStretch(3, 1)

        self.fills = make_table(
            ["#", "Item", "Fills where the value so far is empty or", "Value", "Rows"],
            _FILLS_COLUMNS,
            controls=True,
        )
        self.fills.horizontalHeaderItem(_ROWS_COLUMN).setTextAlignment(_RIGHT)
        self._fills_card = table_card(self.fills)

        self.add_button = make_button("Add item", icon_name=IconName.ADD)
        self.remove_button = make_button("Remove item")
        self.up_button = make_button("Move up")
        self.down_button = make_button("Move down")
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        for button in (
            self.add_button,
            self.remove_button,
            self.up_button,
            self.down_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)
        self.counts = text_label("", tone="secondary", wrap=True)

        editor = QFrame()
        editor.setProperty("cciRole", "card")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(16, 14, 16, 14)
        editor_layout.setSpacing(10)
        editor_layout.addWidget(self.title)
        editor_layout.addLayout(head)
        editor_layout.addWidget(self._fills_card, 1)
        editor_layout.addLayout(buttons)
        editor_layout.addWidget(self.counts)

        self._message = text_label(tone="secondary", wrap=True)
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty = QFrame()
        empty.setProperty("cciRole", "card")
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.addWidget(self._message)
        self._stack = QStackedWidget()
        self._stack.addWidget(editor)
        self._stack.addWidget(empty)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        theme_events().changed.connect(self._fit_fills_table)
        self._fit_fills_table()

    def show_editor(self) -> None:
        """Show the editor."""
        self._stack.setCurrentIndex(0)

    def show_message(self, text: str) -> None:
        """Say *text* in place of the editor."""
        self._message.setText(text)
        self._stack.setCurrentIndex(1)

    def message(self) -> str:
        """What shows in place of the editor ("" while the editor shows)."""
        return self._message.text() if self._stack.currentIndex() == 1 else ""

    def _fit_fills_table(self, *_args) -> None:
        """The items table always has room for its header and a few rows."""
        table = self.fills
        card = self._fills_card
        card.ensurePolished()
        table.ensurePolished()
        header = table.horizontalHeader().sizeHint().height()
        margins = card.layout().contentsMargins()
        frames = 2 * (card.frameWidth() + table.frameWidth())
        card.setMinimumHeight(
            round(header + FILLS_TABLE_MIN_ROWS * current().metrics.editor_row_h)
            + margins.top()
            + margins.bottom()
            + frames
        )


class CoalescedItemsPage(Page):
    """Coalesced items: one item made from two or more items of a form."""

    KEY = steps.COALESCED
    SECTION = "Data"
    ICON = IconName.COALESCED_ITEMS
    EXPORTS = (
        "pushButton_coalesced_new",
        "pushButton_coalesced_remove",
        "banner_coalesced",
        "banner_coalesced_state",
        "tableWidget_coalesced_items",
        "panel_coalesced_editor",
        "label_coalesced_editor",
        "comboBox_coalesced_form",
        "comboBox_coalesced_name",
        "comboBox_coalesced_overlap",
        "tableWidget_coalesced_fills",
        "pushButton_coalesced_add_item",
        "pushButton_coalesced_remove_item",
        "pushButton_coalesced_up",
        "pushButton_coalesced_down",
        "label_coalesced_counts",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Optional. Make one item from two or more items of a form. Your "
            "changes reach the report when you go to another step.",
            parent=parent,
        )
        self.pushButton_coalesced_new = make_button(
            "New coalesced item", icon_name=IconName.ADD
        )
        self.pushButton_coalesced_remove = make_button("Remove")
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(self.pushButton_coalesced_new)
        toolbar.addWidget(self.pushButton_coalesced_remove)
        toolbar.addStretch(1)
        # What reaching the report did.
        self.banner_coalesced = StatusBanner()
        # The report's coalesced items lack a form or an item: standing, so
        # it isn't repeated in the status bar.
        self.banner_coalesced_state = StatusBanner(dismissible=False, announce=False)

        self.tableWidget_coalesced_items = make_table(
            [
                "Name",
                "Form",
                "Items, in order",
                "Filled",
                "Overlaps",
                "When values overlap",
            ],
            _ITEMS_COLUMNS,
            placeholder=NO_COALESCED_ITEMS,
        )
        for column in (_FILLED_COLUMN, _OVERLAPS_COLUMN):
            header = self.tableWidget_coalesced_items.horizontalHeaderItem(column)
            header.setTextAlignment(_RIGHT)
        self._items_card = table_card(self.tableWidget_coalesced_items)
        items = QVBoxLayout()
        items.setSpacing(6)
        items.addWidget(section_label("Coalesced items"))
        items.addWidget(self._items_card)

        self.panel_coalesced_editor = _EditorPanel()
        editor = self.panel_coalesced_editor
        self.label_coalesced_editor = editor.title
        self.comboBox_coalesced_form = editor.form
        self.comboBox_coalesced_name = editor.name
        self.comboBox_coalesced_overlap = editor.overlap
        self.tableWidget_coalesced_fills = editor.fills
        self.pushButton_coalesced_add_item = editor.add_button
        self.pushButton_coalesced_remove_item = editor.remove_button
        self.pushButton_coalesced_up = editor.up_button
        self.pushButton_coalesced_down = editor.down_button
        self.label_coalesced_counts = editor.counts

        # Below the toolbar, the page scrolls when the window is too short
        # for the table and the editor; taller, the editor takes the room.
        content = QWidget()
        content.setProperty("cciRole", "pageContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        content_layout.addWidget(self.banner_coalesced)
        content_layout.addWidget(self.banner_coalesced_state)
        content_layout.addLayout(items)
        content_layout.addWidget(self.panel_coalesced_editor, 1)
        scroll = QScrollArea()
        scroll.setProperty("cciRole", "page")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        self.body.addLayout(toolbar)
        self.body.addWidget(scroll, 1)

        # The table is as tall as its rows, up to ITEMS_TABLE_ROWS of them.
        model = self.tableWidget_coalesced_items.model()
        for signal in (model.rowsInserted, model.rowsRemoved, model.modelReset):
            signal.connect(self._fit_items_table)
        theme_events().changed.connect(self._fit_items_table)
        self._fit_items_table()

    def _fit_items_table(self, *_args) -> None:
        table = self.tableWidget_coalesced_items
        card = self._items_card
        card.ensurePolished()
        table.ensurePolished()
        # Empty, it needs room for its placeholder (inset 16px all round).
        rows = min(table.rowCount(), ITEMS_TABLE_ROWS) if table.rowCount() else 2
        header = table.horizontalHeader().sizeHint().height()
        margins = card.layout().contentsMargins()
        frames = 2 * (card.frameWidth() + table.frameWidth())
        card.setFixedHeight(
            round(header + rows * current().metrics.row_h)
            + margins.top()
            + margins.bottom()
            + frames
        )


class CoalescedItemsMixin:
    """Behavior for the Coalesced items page."""

    def _init_coalesced_items(self) -> None:
        """Connect the page's controls; it starts with no coalesced items."""
        # The page's coalesced items, applied or not.
        self._coalesced_drafts: List[CoalescedItem] = []
        # The report's coalesced items when the page last saw them: when they
        # change (a saved setting loaded), the drafts follow.
        self._coalesced_seen: List[CoalescedItem] = []
        # The forms and coalesced items build the table was last filled for:
        # only a change refills it, so other steps' updates keep the page's
        # selection.
        self._coalesced_shown_for: Tuple[object, object] = (None, None)

        self.ui.pushButton_coalesced_new.clicked.connect(self.click_new_coalesced_item)
        self.ui.pushButton_coalesced_remove.clicked.connect(
            self.click_remove_coalesced_item
        )
        self.ui.pushButton_coalesced_add_item.clicked.connect(
            self.click_add_item_to_coalesced
        )
        self.ui.pushButton_coalesced_remove_item.clicked.connect(
            self.click_remove_item_from_coalesced
        )
        self.ui.pushButton_coalesced_up.clicked.connect(
            self.click_move_item_up_in_coalesced
        )
        self.ui.pushButton_coalesced_down.clicked.connect(
            self.click_move_item_down_in_coalesced
        )
        self.ui.tableWidget_coalesced_items.itemSelectionChanged.connect(
            self._on_coalesced_item_selected
        )
        fills = self.ui.tableWidget_coalesced_fills
        fills.itemSelectionChanged.connect(self._update_coalesced_part_buttons)
        fills.itemChanged.connect(self._on_coalesced_value_edited)
        self.ui.comboBox_coalesced_form.currentIndexChanged.connect(
            self._on_coalesced_form_picked
        )
        self.ui.comboBox_coalesced_name.editTextChanged.connect(
            self._on_coalesced_name_edited
        )
        self.ui.comboBox_coalesced_overlap.currentIndexChanged.connect(
            self._on_coalesced_overlap_picked
        )
        theme_events().changed.connect(self._show_coalesced_starts)
        self.update_coalesced_items_ui()

    # ------------------------------------------------------------------
    # Refresh (called by update_all_ui)

    def update_coalesced_items_ui(self) -> None:
        """Show the drafts over the report's forms, their problems, what's missing.

        When the report's coalesced items changed (a saved setting was
        loaded), the drafts become the report's. The table and editor are
        filled again only when the report's forms or coalesced items build
        changed; what the page last brought to the report is then out of
        date, so its message goes.
        """
        applied = list(self.report.coalesced_items)
        changed = applied != self._coalesced_seen
        if changed:
            self._coalesced_drafts = list(applied)
            self._coalesced_seen = applied
        shown_for = (self.report.stacked_data, self.report.coalesced_build)
        if changed or any(
            now is not then for now, then in zip(shown_for, self._coalesced_shown_for)
        ):
            self._coalesced_shown_for = shown_for
            self._set_label_text(self.ui.banner_coalesced, "")
            self._fill_coalesced_items_table(self._current_coalesced_row())
        self._show_coalesced_state()

    def _forget_applied_coalesced_items(self) -> None:
        """Note that the report no longer has the applied coalesced items.

        (A new Corelisting ZIP starts a new report.) The drafts stay, and
        reach the new report once it is loaded (``apply_data_steps``).
        """
        self._coalesced_seen = []
        self._set_label_text(self.ui.banner_coalesced, "")

    def _replace_coalesced_drafts(self, drafts: Sequence[CoalescedItem]) -> None:
        """Make *drafts* the page's coalesced items (an input was removed).

        What last reached the report is out of date, so its message goes.
        """
        self._coalesced_drafts = list(drafts)
        self._set_label_text(self.ui.banner_coalesced, "")
        self._fill_coalesced_items_table(None)

    def _has_unapplied_coalesced_items(self) -> bool:
        """Whether the page's coalesced items differ from the report's."""
        return self._stripped_coalesced_drafts() != list(self.report.coalesced_items)

    def _apply_coalesced_step(self) -> None:
        """Bring the page's coalesced items to the report (the user left the page).

        Nothing happens without loaded data or changes; with problems the
        step is held (its marks say why) and nothing from it is used.
        """
        if not self.report.loaded_data or not self._has_unapplied_coalesced_items():
            return
        if self._show_coalesced_problems(self._show_coalesced_summaries()):
            return
        drafts = self._stripped_coalesced_drafts()
        apply_coalesced_items(self.report, drafts)
        self._coalesced_drafts = list(drafts)
        self._coalesced_seen = list(self.report.coalesced_items)
        self.update_all_ui()
        self._set_label_text(
            self.ui.banner_coalesced, steps.coalesced_applied_message(self.report)
        )

    # ------------------------------------------------------------------
    # Slots bound to the page's buttons

    def click_new_coalesced_item(self) -> None:
        """Add a coalesced item with two empty items, of the form being edited.

        (Of the first form when none is.) It is selected.
        """
        row = self._current_coalesced_row()
        forms = sorted(self.report.stacked_data)
        if row is not None:
            form = self._coalesced_drafts[row].form
        else:
            form = forms[0] if forms else ""
        self._coalesced_drafts.append(CoalescedItem(form, "", "", (Fill(""),)))
        self._fill_coalesced_items_table(len(self._coalesced_drafts) - 1)
        self._show_coalesced_state()

    def click_remove_coalesced_item(self) -> None:
        """Remove the selected coalesced item (from the report on leaving the page)."""
        row = self._current_coalesced_row()
        if row is None:
            return
        del self._coalesced_drafts[row]
        remaining = len(self._coalesced_drafts)
        self._fill_coalesced_items_table(min(row, remaining - 1) if remaining else None)
        self._show_coalesced_state()

    def click_add_item_to_coalesced(self) -> None:
        """Add an empty item at the end of the selected coalesced item."""
        row = self._current_coalesced_row()
        if row is None:
            return
        parts = self._coalesced_parts(row)
        parts.append(Fill(""))
        self._set_coalesced_parts(row, parts, len(parts) - 1)

    def click_remove_item_from_coalesced(self) -> None:
        """Remove the selected item; of two, clear it instead (it keeps two rows)."""
        row = self._current_coalesced_row()
        part = self._current_coalesced_part()
        if row is None or part is None:
            return
        parts = self._coalesced_parts(row)
        if len(parts) > 2:
            del parts[part]
        else:
            parts[part] = Fill("")
        self._set_coalesced_parts(row, parts, min(part, len(parts) - 1))

    def click_move_item_up_in_coalesced(self) -> None:
        """Move the selected item up one row (in row 1 it has no condition)."""
        self._move_coalesced_part(-1)

    def click_move_item_down_in_coalesced(self) -> None:
        """Move the selected item down one row (in row 1 it has no condition)."""
        self._move_coalesced_part(1)

    # ------------------------------------------------------------------
    # The Coalesced items table

    def _current_coalesced_row(self) -> Optional[int]:
        """The selected coalesced item's row (and index in the drafts), if any."""
        table = self.ui.tableWidget_coalesced_items
        rows = table.selectionModel().selectedRows()
        if rows and rows[0].row() < len(self._coalesced_drafts):
            return rows[0].row()
        return None

    def _fill_coalesced_items_table(self, select: Optional[int]) -> None:
        """Rebuild the table from the drafts and select row *select*."""
        table = self.ui.tableWidget_coalesced_items
        table.blockSignals(True)
        try:
            table.setRowCount(len(self._coalesced_drafts))
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    cell = QTableWidgetItem("")
                    cell.setFlags(_READ_ONLY)
                    if column in (_FILLED_COLUMN, _OVERLAPS_COLUMN):
                        cell.setTextAlignment(_RIGHT)
                    table.setItem(row, column, cell)
            if select is not None and 0 <= select < table.rowCount():
                table.selectRow(select)
            else:
                table.clearSelection()
        finally:
            table.blockSignals(False)
        self._on_coalesced_item_selected()

    def _show_coalesced_summaries(self) -> List[Optional[Outcome]]:
        """Bring each row of the table up to date with its draft.

        Returns what each draft gives, by position (see
        :func:`~clinical_reporting.coalescing.preview`): ``None`` while it
        can't be built.
        """
        table = self.ui.tableWidget_coalesced_items
        drafts = self._coalesced_drafts
        data = self.report.stacked_data
        outcomes = [coalescing.preview(drafts, row, data) for row in range(len(drafts))]
        for row, (draft, outcome) in enumerate(zip(drafts, outcomes)):
            if table.item(row, _NAME_COLUMN) is None:
                continue
            texts = {
                _NAME_COLUMN: draft.name.strip() or coalescing.NEW_COALESCED_ITEM,
                _FORM_COLUMN: draft.form,
                _ITEMS_COLUMN: ", ".join(name for name in draft.items if name),
                _FILLED_COLUMN: NOT_BUILT if outcome is None else f"{outcome.filled:,}",
                _OVERLAPS_COLUMN: (
                    NOT_BUILT if outcome is None else f"{outcome.overlapping:,}"
                ),
                _OVERLAP_COLUMN: OVERLAP_CHOICES.get(draft.on_overlap, ""),
            }
            for column, text in texts.items():
                table.item(row, column).setText(text)
        return outcomes

    def _show_coalesced_problems(
        self, outcomes: Sequence[Optional[Outcome]]
    ) -> List[str]:
        """Mark what stops the drafts from reaching the report; return it by line.

        Each draft's Name in the table, and in the editor the selected
        draft's Form, Name, items, condition values, Rows of the later items
        whose overlaps it refuses, and When values overlap. The lines
        ("Race in DM: Give it a name.") are the page's problems: they turn
        its badge red and hold the step. *outcomes* are what each draft
        gives (:meth:`_show_coalesced_summaries`).
        """
        drafts = self._stripped_coalesced_drafts()
        found = coalescing.item_problems(drafts, self.report.stacked_data, outcomes)
        table = self.ui.tableWidget_coalesced_items
        lines = []
        for row, (draft, problems) in enumerate(zip(drafts, found)):
            texts = list(dict.fromkeys(problem.text for problem in problems))
            lines.extend(f"{coalescing.label(draft)}: {text}" for text in texts)
            cell = table.item(row, _NAME_COLUMN)
            if cell is not None:
                mark_cell(cell, "\n".join(texts))
        row = self._current_coalesced_row()
        if row is not None:
            self._mark_coalesced_editor(found[row])
        self._set_page_problems(steps.COALESCED, lines)
        return lines

    def _mark_coalesced_editor(self, problems: Sequence[feedback.Problem]) -> None:
        """Mark the editor's fields with the selected draft's *problems*."""

        def on(*fields: str) -> str:
            texts = (problem.text for problem in problems if problem.field in fields)
            return "\n".join(dict.fromkeys(texts))

        ui = self.ui
        show_problem(ui.comboBox_coalesced_form, on("form"))
        show_problem(ui.comboBox_coalesced_name, on("name"))
        fills = ui.tableWidget_coalesced_fills
        for position in range(fills.rowCount()):
            box = fills.cellWidget(position, _ITEM_COLUMN)
            if isinstance(box, ItemBox):
                box.set_problem(on(f"item.{position}"))
            for column, field in (
                (_VALUE_COLUMN, f"value.{position}"),
                (_ROWS_COLUMN, f"overlap.{position}"),
            ):
                cell = fills.item(position, column)
                if cell is not None:
                    mark_cell(cell, on(field))
        overlaps = dict.fromkeys(
            problem.text for problem in problems if problem.field.startswith("overlap.")
        )
        show_problem(ui.comboBox_coalesced_overlap, "\n".join(overlaps))

    def _on_coalesced_item_selected(self) -> None:
        """Show the selected coalesced item in the editor."""
        self.ui.pushButton_coalesced_remove.setEnabled(
            self._current_coalesced_row() is not None
        )
        self._show_coalesced_editor()

    # ------------------------------------------------------------------
    # The editor

    def _show_coalesced_editor(self, part: Optional[int] = None) -> None:
        """Fill the editor from the selected draft; *part* is the row to select."""
        panel = self.ui.panel_coalesced_editor
        row = self._current_coalesced_row()
        if row is None:
            panel.show_message(SELECT_A_COALESCED_ITEM)
            self._update_coalesced_part_buttons()
            self._show_coalesced_outcome()
            return
        panel.show_editor()
        draft = self._coalesced_drafts[row]
        form_box = self.ui.comboBox_coalesced_form
        data = self.report.stacked_data
        form_box.blockSignals(True)
        form_box.clear()
        for form in sorted(data):
            form_box.addItem(form, form)
        if draft.form and draft.form not in data:
            form_box.addItem(f"{draft.form} (not loaded)", draft.form)
        form_box.setCurrentIndex(form_box.findData(draft.form) if draft.form else -1)
        form_box.blockSignals(False)
        overlap_box = self.ui.comboBox_coalesced_overlap
        overlap_box.blockSignals(True)
        overlap_box.setCurrentIndex(max(overlap_box.findData(draft.on_overlap), 0))
        overlap_box.blockSignals(False)
        self._show_coalesced_parts(row, part)

    def _show_coalesced_parts(self, row: int, part: Optional[int]) -> None:
        """Fill the name's choices and the items table, then the outcome."""
        draft = self._coalesced_drafts[row]
        name_box = self.ui.comboBox_coalesced_name
        name_box.blockSignals(True)
        name_box.clear()
        name_box.addItems(list(dict.fromkeys(name for name in draft.items if name)))
        name_box.setEditText(draft.name)
        name_box.lineEdit().setCursorPosition(0)
        name_box.blockSignals(False)
        self._fill_coalesced_parts_table(row, part)
        self._show_coalesced_outcome()

    def _fill_coalesced_parts_table(self, row: int, select: Optional[int]) -> None:
        """Rebuild the items table from the draft at *row*; select row *select*."""
        table = self.ui.tableWidget_coalesced_fills
        parts = self._coalesced_parts(row)
        table.blockSignals(True)
        try:
            for old_row in range(table.rowCount()):
                for column in (_ITEM_COLUMN, _CONDITION_COLUMN):
                    # Qt deletes a replaced widget later: hide it and quieten it
                    # now, so it is neither drawn nor heard until then.
                    old = table.cellWidget(old_row, column)
                    if old is not None:
                        old.blockSignals(True)
                        old.hide()
            table.setRowCount(len(parts))
            for position, part in enumerate(parts):
                number = QTableWidgetItem(str(position + 1))
                number.setFlags(_READ_ONLY)
                table.setItem(position, _NUMBER_COLUMN, number)
                # Under the cell widgets, so the row can be selected there.
                for column in (_ITEM_COLUMN, _CONDITION_COLUMN):
                    under = QTableWidgetItem("")
                    under.setFlags(_READ_ONLY)
                    table.setItem(position, column, under)
                box = ItemBox(self._coalesced_item_choices(row, position), part.item)
                box.setAccessibleName(f"Item {position + 1}")
                box.currentIndexChanged.connect(
                    partial(self._on_coalesced_part_picked, position)
                )
                box.lineEdit().focused.connect(
                    partial(self._select_coalesced_part, position)
                )
                table.setCellWidget(position, _ITEM_COLUMN, box)
                value = QTableWidgetItem("")
                if position == 0:
                    table.item(position, _CONDITION_COLUMN).setText(STARTS_THE_VALUE)
                    value.setFlags(Qt.ItemFlag.ItemIsSelectable)
                else:
                    condition = _ConditionBox(part.operator)
                    condition.setAccessibleName(f"Condition of item {position + 1}")
                    condition.currentIndexChanged.connect(
                        partial(self._on_coalesced_condition_picked, position)
                    )
                    condition.focused.connect(
                        partial(self._select_coalesced_part, position)
                    )
                    table.setCellWidget(position, _CONDITION_COLUMN, condition)
                    value.setText(part.value if part.operator else "")
                    value.setFlags(self._coalesced_value_flags(part.operator))
                table.setItem(position, _VALUE_COLUMN, value)
                rows = QTableWidgetItem("")
                rows.setFlags(_READ_ONLY)
                rows.setTextAlignment(_RIGHT)
                table.setItem(position, _ROWS_COLUMN, rows)
            self._show_coalesced_starts()
            if select is not None and 0 <= select < table.rowCount():
                table.selectRow(select)
            else:
                table.clearSelection()
        finally:
            table.blockSignals(False)
        self._update_coalesced_part_buttons()

    def _show_coalesced_starts(self, *_args) -> None:
        """Mute the first row's "starts the value" (again, in a new theme)."""
        cell = self.ui.tableWidget_coalesced_fills.item(0, _CONDITION_COLUMN)
        if cell is not None:
            cell.setForeground(QBrush(qcolor(current().colors.text_secondary)))

    @staticmethod
    def _coalesced_value_flags(operator: str) -> Qt.ItemFlag:
        """A condition's value can be typed only once it has an operator."""
        if operator:
            return _READ_ONLY | Qt.ItemFlag.ItemIsEditable
        return Qt.ItemFlag.ItemIsSelectable

    def _coalesced_item_choices(self, row: int, position: int) -> List[str]:
        """What the item at *position* of the draft at *row* can be.

        Its form's items that no other row, and no other coalesced item of the
        form, has; and its own.
        """
        drafts = self._coalesced_drafts
        draft = drafts[row]
        own = draft.items[position]
        taken = {name for index, name in enumerate(draft.items) if index != position}
        taken.update(
            name
            for index, other in enumerate(drafts)
            if index != row and other.form == draft.form
            for name in other.items
        )
        frame = self.report.stacked_data.get(draft.form)
        columns = [] if frame is None else [str(name) for name in frame.columns]
        choices = [name for name in columns if name not in taken or name == own]
        if own and own not in choices:  # An item its form no longer has.
            choices.append(own)
        return choices

    def _show_coalesced_outcome(self) -> None:
        """Show what the drafts give, their problems, and the page's state.

        The table's summaries, then the selected draft's rows and counts in
        the editor, then every problem marked on its field.
        """
        outcomes = self._show_coalesced_summaries()
        row = self._current_coalesced_row()
        if row is not None:
            draft = self._coalesced_drafts[row]
            outcome = outcomes[row]
            self.ui.label_coalesced_editor.setText(coalescing.label(draft))
            table = self.ui.tableWidget_coalesced_fills
            table.blockSignals(True)
            try:
                for position, name in enumerate(draft.items):
                    cell = table.item(position, _ROWS_COLUMN)
                    if cell is not None:
                        count = None if outcome is None else outcome.rows.get(name)
                        cell.setText("" if count is None else f"{count:,}")
            finally:
                table.blockSignals(False)
            self.ui.label_coalesced_counts.setText(
                PICK_ITEMS
                if outcome is None
                else steps.coalesced_counts(draft, outcome)
            )
        self._show_coalesced_problems(outcomes)
        self._show_coalesced_state()

    def _coalesced_parts(self, row: int) -> List[Fill]:
        """The items of the draft at *row* in order, the first as a fill."""
        draft = self._coalesced_drafts[row]
        return [Fill(draft.first), *draft.fills]

    def _set_coalesced_parts(
        self, row: int, parts: Sequence[Fill], select: Optional[int]
    ) -> None:
        """Give the draft at *row* these items; show them, *select* selected.

        The first item has no condition. While its name is blank or the first
        item's, the name follows the first item.
        """
        draft = self._coalesced_drafts[row]
        first = parts[0].item
        name = draft.name
        if first != draft.first and (not name.strip() or name == draft.first):
            name = first
        self._coalesced_drafts[row] = replace(
            draft, name=name, first=first, fills=tuple(parts[1:])
        )
        self._show_coalesced_parts(row, select)

    def _current_coalesced_part(self) -> Optional[int]:
        """The selected row of the items table, if any."""
        table = self.ui.tableWidget_coalesced_fills
        rows = table.selectionModel().selectedRows()
        if rows and rows[0].row() < table.rowCount():
            return rows[0].row()
        return None

    def _select_coalesced_part(self, position: int) -> None:
        """Typing in a row's cell selects its row (as clicking it would)."""
        table = self.ui.tableWidget_coalesced_fills
        if self._current_coalesced_part() != position and position < table.rowCount():
            table.selectRow(position)

    def _move_coalesced_part(self, step: int) -> None:
        row = self._current_coalesced_row()
        part = self._current_coalesced_part()
        if row is None or part is None:
            return
        parts = self._coalesced_parts(row)
        to = part + step
        if not 0 <= to < len(parts):
            return
        parts[part], parts[to] = parts[to], parts[part]
        # Row 1 has no condition: the item moved there drops its own, and the
        # one moved out of it comes with none (see _set_coalesced_parts).
        self._set_coalesced_parts(row, parts, to)

    def _update_coalesced_part_buttons(self) -> None:
        """Add item needs a coalesced item; the others, an item row to act on."""
        editing = self._current_coalesced_row() is not None
        part = self._current_coalesced_part() if editing else None
        last = self.ui.tableWidget_coalesced_fills.rowCount() - 1
        self.ui.pushButton_coalesced_add_item.setEnabled(editing)
        self.ui.pushButton_coalesced_remove_item.setEnabled(part is not None)
        self.ui.pushButton_coalesced_up.setEnabled(part is not None and part > 0)
        self.ui.pushButton_coalesced_down.setEnabled(part is not None and part < last)

    def _on_coalesced_form_picked(self, index: int) -> None:
        """Another form: its items start over, two empty rows.

        A name that only followed the first item goes with them; a typed one
        stays.
        """
        row = self._current_coalesced_row()
        if row is None:
            return
        form = self.ui.comboBox_coalesced_form.itemData(index) or ""
        draft = self._coalesced_drafts[row]
        if form == draft.form:
            return
        name = "" if draft.name in ("", draft.first) else draft.name
        self._coalesced_drafts[row] = replace(
            draft, form=form, name=name, first="", fills=(Fill(""),)
        )
        self._show_coalesced_parts(row, None)

    def _on_coalesced_name_edited(self, text: str) -> None:
        row = self._current_coalesced_row()
        if row is None:
            return
        draft = self._coalesced_drafts[row]
        if text != draft.name:
            self._coalesced_drafts[row] = replace(draft, name=text)
            self._show_coalesced_outcome()

    def _on_coalesced_overlap_picked(self, index: int) -> None:
        row = self._current_coalesced_row()
        if row is None:
            return
        on_overlap = self.ui.comboBox_coalesced_overlap.itemData(index) or REFUSE
        draft = self._coalesced_drafts[row]
        if on_overlap != draft.on_overlap:
            self._coalesced_drafts[row] = replace(draft, on_overlap=on_overlap)
            self._show_coalesced_outcome()

    def _on_coalesced_part_picked(self, position: int, index: int) -> None:
        """The item at *position* was picked (a whole item name, not typing)."""
        row = self._current_coalesced_row()
        box = self.ui.tableWidget_coalesced_fills.cellWidget(position, _ITEM_COLUMN)
        if row is None or box is None:
            return
        name = box.itemText(index) if index >= 0 else ""
        parts = self._coalesced_parts(row)
        if name == parts[position].item:
            return
        parts[position] = replace(parts[position], item=name)
        self._set_coalesced_parts(row, parts, position)

    def _on_coalesced_condition_picked(self, position: int, index: int) -> None:
        """A later item's condition changed: without one, its value goes."""
        row = self._current_coalesced_row()
        table = self.ui.tableWidget_coalesced_fills
        box = table.cellWidget(position, _CONDITION_COLUMN)
        if row is None or box is None or position == 0:
            return
        operator = box.itemData(index) or ""
        parts = self._coalesced_parts(row)
        part = parts[position]
        parts[position] = replace(
            part, operator=operator, value=part.value if operator else ""
        )
        value = table.item(position, _VALUE_COLUMN)
        table.blockSignals(True)
        try:
            value.setFlags(self._coalesced_value_flags(operator))
            if not operator:
                value.setText("")
        finally:
            table.blockSignals(False)
        draft = self._coalesced_drafts[row]
        self._coalesced_drafts[row] = replace(draft, fills=tuple(parts[1:]))
        self._show_coalesced_outcome()

    def _on_coalesced_value_edited(self, cell: QTableWidgetItem) -> None:
        """A condition's value was typed."""
        row = self._current_coalesced_row()
        position = cell.row()
        if row is None or cell.column() != _VALUE_COLUMN or position == 0:
            return
        parts = self._coalesced_parts(row)
        if position >= len(parts) or parts[position].value == cell.text():
            return
        parts[position] = replace(parts[position], value=cell.text())
        draft = self._coalesced_drafts[row]
        self._coalesced_drafts[row] = replace(draft, fills=tuple(parts[1:]))
        self._show_coalesced_outcome()

    # ------------------------------------------------------------------
    # The page's state

    def _stripped_coalesced_drafts(self) -> List[CoalescedItem]:
        """The drafts with the names typed on the page trimmed."""
        return [
            replace(draft, name=draft.name.strip()) for draft in self._coalesced_drafts
        ]

    def _show_coalesced_state(self) -> None:
        """The standing banner: the forms and items the report's coalesced items lack."""
        self._set_label_text(
            self.ui.banner_coalesced_state, steps.coalesced_missing_message(self.report)
        )
