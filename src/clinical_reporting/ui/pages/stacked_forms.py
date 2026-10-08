"""Stacked forms: new forms made of other forms' rows, one under another.

The page keeps its own stacked forms (the drafts) until "Apply to report":
:class:`StackedFormsMixin` edits them with :mod:`clinical_reporting.stacking`
(which decides how the items line up), checks them with
:func:`~clinical_reporting.stacking.problems` on Apply, and hands them to
:func:`~clinical_reporting.session.apply_stacked_forms`. Messages and
warnings are worded in :mod:`clinical_reporting.steps`; the page's own
labels and hints are here.

- The Stacked forms table: Name (typed in place) | Members (a searchable
  checklist of the loaded forms; members keep the order they were ticked) |
  Items | Rows, worked out live from the drafts.
- "Items of NAME": the selected stacked form's items grid
  (:class:`StackedItemsGrid`), from :func:`~clinical_reporting.stacking.layout`:
  a row per stacked item in three sections (In every member, Matched, Left
  out), a column per member present. Left-out rows from different members
  (Ctrl-click for several) become one stacked item with Match, or one keeps
  its item on its own (double-click does the same); Unmatch puts a match's
  items back in Left out. A matched row's member cells are dropdowns
  (:func:`~clinical_reporting.stacking.match_choices`) that change one
  member's item at a time (:func:`~clinical_reporting.stacking.set_match_item`).
- Two banners: what Apply did, and a standing one for the page's state: the
  drafts differ from the report's ("Not applied yet"), a new Corelisting ZIP
  started a new report (apply again), data changed since Apply makes a match
  ambiguous (an error that stops the export), or the report's stacked forms
  lack a member or a matched item.

Loading a saved setting (when it changes the report's stacked forms) replaces
the drafts with the report's; a new ZIP, or removing it, keeps them and asks
for Apply again (:meth:`StackedFormsMixin._forget_applied_stacked_forms`).
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial
from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QItemSelectionModel, QModelIndex, QRect, Qt, Signal
from PySide6.QtGui import (
    QFont,
    QFontMetrics,
    QKeySequence,
    QPainter,
    QPalette,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QStackedWidget,
    QStyledItemDelegate,
    QTableView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName, icon
from cci_ui.theme.manager import current, theme_events
from cci_ui.theme.palette import qcolor
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.checklist import ChecklistComboBox, ChecklistItem
from cci_ui.widgets.labels import section_label, text_label
from cci_ui.widgets.page import Page
from cci_ui.widgets.search import SearchField
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import ColumnSpec, style_table, table_card
from clinical_reporting import stacking, steps
from clinical_reporting.session import apply_stacked_forms
from clinical_reporting.stacking import (
    Match,
    MatchChoices,
    MatchedItem,
    StackedForm,
    StackLayout,
)

from ._common import CellComboBox, make_table

#: The Stacked forms table's columns: Name, Members, Items, Rows.
_FORMS_COLUMNS = (
    ColumnSpec("interactive", 220),
    ColumnSpec("stretch"),
    ColumnSpec("fixed", 76),
    ColumnSpec("fixed", 92),
)
_NAME_COLUMN, _MEMBERS_COLUMN, _ITEMS_COLUMN, _ROWS_COLUMN = range(4)
#: The Stacked forms table shows at most this many rows before it scrolls.
FORMS_TABLE_ROWS = 3.5

#: The items grid's first column (the stacked items), which stays in place.
FIRST_COLUMN_W = 232
#: Narrowest a member column gets before the grid scrolls sideways.
MEMBER_COLUMN_W = 140
#: The same from :data:`NARROW_FROM` members on, when columns show names only.
NARROW_MEMBER_COLUMN_W = 92
#: From this many members, the member columns narrow (their rows in the tooltip).
NARROW_FROM = 5

NO_STACKED_FORMS = "No stacked forms. Use New stacked form to stack two or more forms."
SELECT_A_STACKED_FORM = (
    "Select a stacked form above, or make one with New stacked form."
)
PICK_MEMBERS = "Pick two or more forms in Members to see how their items line up."
ITEMS_HINT = (
    "Select left-out items from different members (Ctrl-click for several), then "
    "Match. Match a single item to keep it on its own; double-click does the same."
)
MATCH_NAME_TIP = "Pick one of the matched names, or type a new one"
#: A matched cell's entry for giving the match nothing.
NOTHING = "—"
#: The headings in a matched cell's dropdown.
SIMILAR_NAMES = "Similar names"
OTHER_ITEMS = "Other items"

# What a grid row is (KIND_ROLE), and its key (KEY_ROLE): the section, the
# match's index, or the item name.
SECTION = "section"
NOTE = "note"
EVERY = "every"
MATCHED = "matched"
LEFT_OUT = "left"

KIND_ROLE = Qt.ItemDataRole.UserRole
KEY_ROLE = Qt.ItemDataRole.UserRole + 1
#: A section's count, note, and (In every member only) whether it is open.
COUNT_ROLE = Qt.ItemDataRole.UserRole + 2
NOTE_ROLE = Qt.ItemDataRole.UserRole + 3
OPEN_ROLE = Qt.ItemDataRole.UserRole + 4
#: A member cell with a tick: the member has the item.
TICK_ROLE = Qt.ItemDataRole.UserRole + 5


class _NameEdit(QLineEdit):
    """A line edit that says when it takes the focus (its row gets selected)."""

    focused = Signal()

    def focusInEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().focusInEvent(event)
        self.focused.emit()


class _MatchNameBox(CellComboBox):
    """A matched item's name: one of its items' names, or one typed."""

    def __init__(self, names: Sequence[str], name: str, parent=None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setLineEdit(_NameEdit())
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.addItems(list(names))
        self.setCurrentText(name)
        self.setToolTip(MATCH_NAME_TIP)
        self.setAccessibleName("Name of the matched item")


class _MatchItemBox(CellComboBox):
    """A member's item in a match, as a dropdown.

    It lists "—" (none) and the member's current item, then the items it
    can take instead under the headings Similar names and Other items, which
    can't be picked. Typing filters the items; text that isn't one changes
    nothing. :attr:`picked` gives the item chosen (``None`` for "—"), even
    the current one.
    """

    picked = Signal(object)

    def __init__(
        self,
        member: str,
        match_name: str,
        choices: MatchChoices,
        warning: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setLineEdit(_NameEdit())
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setAccessibleName(f"Item {member} gives {match_name}")
        self.addItem(NOTHING, None)
        if choices.clears:
            self.setItemData(
                0,
                steps.stacked_clear_tooltip(choices.clears, choices.current),
                Qt.ItemDataRole.ToolTipRole,
            )
        if choices.current is not None:
            self.addItem(choices.current, choices.current)
        #: The entry showing what the member gives now.
        self._chosen = self.count() - 1
        model = self.model()
        for heading, names in (
            (SIMILAR_NAMES, choices.similar),
            (OTHER_ITEMS, choices.others),
        ):
            if not names:
                continue
            self.addItem(heading)
            title = model.item(self.count() - 1)
            title.setEnabled(False)
            font = QFont(self.font())
            font.setWeight(QFont.Weight.DemiBold)
            title.setFont(font)
            for name in names:
                self.addItem(name, name)
        self.setCurrentIndex(self._chosen)
        if warning:
            self.setItemIcon(self._chosen, icon(IconName.WARNING, "warning"))
            self.setToolTip(warning)

        completer = QCompleter(
            [self.itemData(i) for i in range(self.count()) if self.itemData(i)], self
        )
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(completer)
        self.activated.connect(self._on_activated)
        self.lineEdit().editingFinished.connect(self._show_chosen)

    def _on_activated(self, index: int) -> None:
        if not self.model().item(index).isEnabled():  # A heading (typed in full).
            self.setCurrentIndex(self._chosen)
            return
        self.picked.emit(self.itemData(index))

    def _show_chosen(self) -> None:
        """Typed text that isn't an item gives way to the entry chosen."""
        shown = self.itemText(self.currentIndex())
        if self.currentText() != shown:
            self.setEditText(shown)


class _GridDelegate(QStyledItemDelegate):
    """Draws the items grid: section and note rows, ticks, muted left-out names.

    Section and note rows span the grid and keep their text at the left
    edge when the members scroll sideways. The frozen first column draws
    nothing on them (the grid's row shows through) and fills its other cells,
    so the cells scrolling under it stay hidden.
    """

    def __init__(self, view: QTableView, *, frozen: bool) -> None:
        super().__init__(view)
        self._frozen = frozen
        #: Ticks in the middle of narrow member columns, else where text starts.
        self.center_ticks = False

    def initStyleOption(self, option, index) -> None:  # noqa: N802 (Qt override)
        super().initStyleOption(option, index)
        if index.data(KIND_ROLE) == LEFT_OUT:
            option.palette.setColor(
                QPalette.ColorRole.Text, qcolor(current().colors.text_secondary)
            )

    def paint(self, painter, option, index) -> None:
        kind = index.data(KIND_ROLE)
        if kind in (SECTION, NOTE):
            if not self._frozen:
                self._paint_spanning(painter, option, index)
            return
        if self._frozen:
            painter.fillRect(option.rect, qcolor(current().colors.bg_surface))
        super().paint(painter, option, index)
        if index.data(TICK_ROLE):
            side = 14
            rect = QRect(0, 0, side, side)
            rect.moveCenter(option.rect.center())
            if not self.center_ticks:
                rect.moveLeft(option.rect.left() + 8)
            icon(IconName.TICK, "success").paint(painter, rect)

    def _paint_spanning(self, painter, option, index) -> None:
        colors = current().colors
        rect = QRect(option.rect)
        painter.save()
        section = index.data(KIND_ROLE) == SECTION
        if section:
            painter.fillRect(rect, qcolor(colors.bg_surface_alt))
        painter.setPen(qcolor(colors.separator))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        # At the view's left edge, however far the members are scrolled.
        x = max(rect.left(), 0) + 12
        middle = rect.center().y()
        font = QFont(option.font)
        if not section:
            painter.setFont(font)
            painter.setPen(qcolor(colors.text_secondary))
            text = QFontMetrics(font).elidedText(
                index.data(Qt.ItemDataRole.DisplayRole) or "",
                Qt.TextElideMode.ElideRight,
                max(0, rect.right() - x),
            )
            painter.drawText(
                QRect(x, rect.top(), max(0, rect.right() - x), rect.height()),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )
            painter.restore()
            return

        is_open = index.data(OPEN_ROLE)
        if is_open is not None:
            chevron = QRect(x, middle - 7, 14, 14)
            icon(
                IconName.SECTION_OPEN if is_open else IconName.SECTION_CLOSED,
                "secondary",
            ).paint(painter, chevron)
            x += 20
        title_font = QFont(font)
        title_font.setWeight(QFont.Weight.DemiBold)
        title = index.data(Qt.ItemDataRole.DisplayRole) or ""
        title_w = QFontMetrics(title_font).horizontalAdvance(title)
        painter.setFont(title_font)
        painter.setPen(qcolor(colors.text_secondary))
        painter.drawText(
            QRect(x, rect.top(), title_w + 1, rect.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )
        x += title_w + 8

        small = QFont(font)
        small.setPixelSize(12)
        metrics = QFontMetrics(small)
        count = str(index.data(COUNT_ROLE) or 0)
        pill = QRect(x, middle - 9, metrics.horizontalAdvance(count) + 12, 18)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor(colors.fill))
        painter.drawRoundedRect(pill, 9, 9)
        painter.setFont(small)
        painter.setPen(qcolor(colors.text_secondary))
        painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, count)
        x = pill.right() + 10

        note = metrics.elidedText(
            index.data(NOTE_ROLE) or "",
            Qt.TextElideMode.ElideRight,
            max(0, rect.right() - x),
        )
        painter.setPen(qcolor(colors.text_tertiary))
        painter.drawText(
            QRect(x, rect.top(), max(0, rect.right() - x), rect.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            note,
        )
        painter.restore()


class StackedItemsGrid(QTableView):
    """The items grid: a row per stacked item, a column per member present.

    The first column (the stacked items) stays in place when the member
    columns scroll sideways: :attr:`frozen` is a second view of the same
    model and selection, drawn over that column, showing only it, and
    scrolling up and down with the grid. The matched items' name boxes sit
    in it; their member cells' dropdowns sit in the grid. Only Matched and
    Left out rows can be selected (Ctrl-click for several).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        #: The first column, kept in place over the grid.
        self.frozen = QTableView(self)
        model = QStandardItemModel(0, 1, self)
        self.setModel(model)
        style_table(self, selection=QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._delegate = _GridDelegate(self, frozen=False)
        self.setItemDelegate(self._delegate)

        self.frozen.setModel(model)
        self.frozen.setSelectionModel(self.selectionModel())
        style_table(
            self.frozen,
            selection=QAbstractItemView.SelectionMode.ExtendedSelection,
            embedded=True,
        )
        # Its section and note rows let the grid's show through.
        self.frozen.setStyleSheet("QTableView { background: transparent; }")
        self.frozen.setItemDelegate(_GridDelegate(self.frozen, frozen=True))
        self.frozen.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.frozen.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.frozen.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        for policy in (
            self.frozen.setHorizontalScrollBarPolicy,
            self.frozen.setVerticalScrollBarPolicy,
        ):
            policy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.frozen.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        self.verticalScrollBar().valueChanged.connect(
            self.frozen.verticalScrollBar().setValue
        )
        self.frozen.verticalScrollBar().valueChanged.connect(
            self.verticalScrollBar().setValue
        )
        self.horizontalHeader().sectionResized.connect(self._place_frozen)
        self.viewport().stackUnder(self.frozen)
        self.set_members([])

    # -- what the page sets

    def set_members(self, headers: Sequence[Tuple[str, str]]) -> None:
        """Start over with a column per member: (header text, tooltip) each."""
        model = self.model()
        model.setRowCount(0)
        self.clearSpans()
        model.setColumnCount(1 + len(headers))
        model.setHorizontalHeaderLabels(
            ["Stacked item", *(text for text, _ in headers)]
        )
        narrow = len(headers) >= NARROW_FROM
        # Narrow columns center their names, as their ticks are.
        align = (
            Qt.AlignmentFlag.AlignCenter
            if narrow
            else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        for column, (_, tip) in enumerate(headers, start=1):
            model.setHeaderData(
                column, Qt.Orientation.Horizontal, tip, Qt.ItemDataRole.ToolTipRole
            )
            model.setHeaderData(
                column,
                Qt.Orientation.Horizontal,
                align,
                Qt.ItemDataRole.TextAlignmentRole,
            )
        self._delegate.center_ticks = narrow
        header = self.horizontalHeader()
        header.setMinimumSectionSize(
            NARROW_MEMBER_COLUMN_W if narrow else MEMBER_COLUMN_W
        )
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, FIRST_COLUMN_W)
        for column in range(1, model.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
            self.frozen.setColumnHidden(column, True)
        self.frozen.setColumnHidden(0, False)
        self.frozen.setColumnWidth(0, FIRST_COLUMN_W)
        self._place_frozen()

    def add_section(
        self, section: str, title: str, count: int, note: str, *, opened=None
    ) -> int:
        """Add a section's row; *opened* (True/False) gives it a chevron."""
        item = self._spanning_row(SECTION, section, title)
        item.setData(count, COUNT_ROLE)
        item.setData(note, NOTE_ROLE)
        item.setData(opened, OPEN_ROLE)
        return item.row()

    def add_note(self, text: str) -> int:
        """Add a line saying a section is empty."""
        return self._spanning_row(NOTE, None, text).row()

    def add_item(self, kind: str, key, name: str, ticks: Sequence[bool]) -> int:
        """Add a stacked item's row, *ticks* under the members that have it.

        Matched and Left out rows can be selected.
        """
        flags = Qt.ItemFlag.ItemIsEnabled
        if kind in (MATCHED, LEFT_OUT):
            flags |= Qt.ItemFlag.ItemIsSelectable
        first = QStandardItem(name)
        row = [first]
        for tick in ticks:
            item = QStandardItem()
            item.setData(tick, TICK_ROLE)
            row.append(item)
        for item in row:
            item.setFlags(flags)
            item.setData(kind, KIND_ROLE)
            item.setData(key, KEY_ROLE)
        self.model().appendRow(row)
        return first.row()

    def set_first_widget(self, row: int, widget: QWidget) -> None:
        """Show *widget* in *row*'s first cell (it stays in place)."""
        self.frozen.setIndexWidget(self.model().index(row, 0), widget)

    def first_widget(self, row: int) -> Optional[QWidget]:
        """The widget in *row*'s first cell, if any."""
        return self.frozen.indexWidget(self.model().index(row, 0))

    def set_cell_widget(self, row: int, column: int, widget: QWidget) -> None:
        """Show *widget* in a member's cell (it scrolls with the members)."""
        self.setIndexWidget(self.model().index(row, column), widget)

    def cell_widget(self, row: int, column: int) -> Optional[QWidget]:
        """The widget in a member's cell, if any."""
        return self.indexWidget(self.model().index(row, column))

    def scroll_position(self) -> Tuple[int, int]:
        """How far the grid is scrolled: across, down."""
        return self.horizontalScrollBar().value(), self.verticalScrollBar().value()

    def scroll_back(self, position: Tuple[int, int]) -> None:
        """Scroll to *position* again once the rows were filled anew."""
        # Both views lay out their rows first, so the scroll bars can reach it.
        self.doItemsLayout()
        self.frozen.doItemsLayout()
        across, down = position
        self.horizontalScrollBar().setValue(across)
        self.verticalScrollBar().setValue(down)

    def row_of(self, kind: str, key) -> int:
        """The row showing the item *key* of *kind*, or -1."""
        model = self.model()
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if index.data(KIND_ROLE) == kind and index.data(KEY_ROLE) == key:
                return row
        return -1

    def selected_keys(self) -> List[Tuple[str, object]]:
        """The (kind, key) of each selected row, top to bottom."""
        rows = sorted(index.row() for index in self.selectionModel().selectedRows(0))
        model = self.model()
        return [
            (model.index(row, 0).data(KIND_ROLE), model.index(row, 0).data(KEY_ROLE))
            for row in rows
        ]

    def select_rows(self, rows: Sequence[int], *, scroll: bool = True) -> None:
        """Select exactly these rows; *scroll* brings the first into view."""
        selection = self.selectionModel()
        selection.clearSelection()
        model = self.model()
        for row in rows:
            selection.select(
                model.index(row, 0),
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
        if rows and scroll:
            self.scrollTo(model.index(rows[0], 1 if model.columnCount() > 1 else 0))

    # -- keeping the first column in place

    def _spanning_row(self, kind: str, key, text: str) -> QStandardItem:
        model = self.model()
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setData(kind, KIND_ROLE)
        item.setData(key, KEY_ROLE)
        model.appendRow(item)
        row = item.row()
        if model.columnCount() > 1:
            self.setSpan(row, 0, 1, model.columnCount())
        return item

    def _place_frozen(self, *_args) -> None:
        header = self.horizontalHeader()
        self.frozen.horizontalHeader().setFixedHeight(header.height())
        self.frozen.setGeometry(
            self.viewport().x(),
            header.y(),
            self.columnWidth(0),
            header.height() + self.viewport().height(),
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._place_frozen()

    def updateGeometries(self) -> None:  # noqa: N802 (Qt override)
        super().updateGeometries()
        self._place_frozen()


class _ItemsPanel(QWidget):
    """The "Items of NAME" panel: search, buttons, then the grid or a message."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.title = section_label("")
        self.search = SearchField("Search items")
        self.search.setFixedWidth(260)
        self.match_button = make_button("Match")
        self.unmatch_button = make_button("Unmatch")
        self._head = QWidget()
        head = QHBoxLayout(self._head)
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        head.addWidget(self.title, 1)
        head.addWidget(self.search)
        head.addWidget(self.match_button)
        head.addWidget(self.unmatch_button)

        self.grid = StackedItemsGrid()
        self._message = text_label(tone="secondary", wrap=True)
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty = QFrame()
        empty.setProperty("cciRole", "card")
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.addWidget(self._message)
        self._stack = QStackedWidget()
        self._stack.addWidget(table_card(self.grid))
        self._stack.addWidget(empty)
        self.hint = text_label(ITEMS_HINT, style="caption", wrap=True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._head)
        layout.addWidget(self._stack, 1)
        layout.addWidget(self.hint)

    def show_grid(self) -> None:
        """Show the items grid, with the search, buttons and hint."""
        self._stack.setCurrentIndex(0)
        self._head.setVisible(True)
        self.hint.setVisible(True)

    def show_message(self, text: str, *, head: bool) -> None:
        """Say *text* where the grid goes; *head*: still show search, buttons, hint."""
        self._message.setText(text)
        self._stack.setCurrentIndex(1)
        self._head.setVisible(head)
        self.hint.setVisible(head)

    def message(self) -> str:
        """What shows where the grid goes ("" while the grid shows)."""
        return self._message.text() if self._stack.currentIndex() == 1 else ""


class StackedFormsPage(Page):
    """Stacked forms: several forms' rows one under another, as a new form."""

    KEY = steps.STACKED
    SECTION = "Data"
    ICON = IconName.STACKED_FORMS
    EXPORTS = (
        "pushButton_stacked_new",
        "pushButton_stacked_remove",
        "pushButton_stacked_apply",
        "banner_stacked",
        "banner_stacked_state",
        "tableWidget_stacked_forms",
        "panel_stacked_items",
        "label_stacked_items",
        "lineEdit_stacked_item_search",
        "pushButton_stacked_match",
        "pushButton_stacked_unmatch",
        "tableView_stacked_items",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Optional. Put the rows of several forms one under another as one new "
            "form, then apply it to the report.",
            parent=parent,
        )
        self.pushButton_stacked_new = make_button(
            "New stacked form", icon_name=IconName.ADD
        )
        self.pushButton_stacked_remove = make_button("Remove")
        self.pushButton_stacked_apply = make_button(
            "Apply to report", variant="primary"
        )
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(self.pushButton_stacked_new)
        toolbar.addWidget(self.pushButton_stacked_remove)
        toolbar.addStretch(1)
        toolbar.addWidget(self.pushButton_stacked_apply)
        # What applying did, or why it couldn't.
        self.banner_stacked = StatusBanner()
        # The page's state (not applied, apply again, a conflict, something
        # missing): standing, so it isn't repeated in the status bar.
        self.banner_stacked_state = StatusBanner(dismissible=False, announce=False)

        self.tableWidget_stacked_forms = make_table(
            ["Name", "Members", "Items", "Rows"],
            _FORMS_COLUMNS,
            placeholder=NO_STACKED_FORMS,
        )
        for column in (_ITEMS_COLUMN, _ROWS_COLUMN):
            header = self.tableWidget_stacked_forms.horizontalHeaderItem(column)
            header.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        self._forms_card = table_card(self.tableWidget_stacked_forms)
        forms = QVBoxLayout()
        forms.setSpacing(6)
        forms.addWidget(section_label("Stacked forms"))
        forms.addWidget(self._forms_card)

        self.panel_stacked_items = _ItemsPanel()
        self.label_stacked_items = self.panel_stacked_items.title
        self.lineEdit_stacked_item_search = self.panel_stacked_items.search
        self.pushButton_stacked_match = self.panel_stacked_items.match_button
        self.pushButton_stacked_unmatch = self.panel_stacked_items.unmatch_button
        self.tableView_stacked_items = self.panel_stacked_items.grid

        self.body.addLayout(toolbar)
        self.body.addWidget(self.banner_stacked)
        self.body.addWidget(self.banner_stacked_state)
        self.body.addLayout(forms)
        self.body.addWidget(self.panel_stacked_items, 1)
        self.add_shortcut(
            QKeySequence.StandardKey.Find, self.lineEdit_stacked_item_search.activate
        )

        # The table is as tall as its rows, up to FORMS_TABLE_ROWS of them.
        model = self.tableWidget_stacked_forms.model()
        for signal in (model.rowsInserted, model.rowsRemoved, model.modelReset):
            signal.connect(self._fit_forms_table)
        theme_events().changed.connect(self._fit_forms_table)
        self._fit_forms_table()

    def _fit_forms_table(self, *_args) -> None:
        table = self.tableWidget_stacked_forms
        card = self._forms_card
        card.ensurePolished()
        table.ensurePolished()
        # Empty, it needs room for its placeholder (inset 16px all round).
        rows = min(table.rowCount(), FORMS_TABLE_ROWS) if table.rowCount() else 2
        header = table.horizontalHeader().sizeHint().height()
        margins = card.layout().contentsMargins()
        frames = 2 * (card.frameWidth() + table.frameWidth())
        card.setFixedHeight(
            round(header + rows * current().metrics.row_h)
            + margins.top()
            + margins.bottom()
            + frames
        )


class StackedFormsMixin:
    """Behavior for the Stacked forms page."""

    def _init_stacked_forms(self) -> None:
        """Connect the page's controls; it starts with no stacked forms."""
        # The page's stacked forms, applied or not.
        self._stacked_drafts: List[StackedForm] = []
        # The report's stacked forms when the page last saw them: when they
        # change (a saved setting loaded), the drafts follow.
        self._stacked_seen: List[StackedForm] = []
        # A new Corelisting ZIP started a new report without them.
        self._stacked_apply_again = False
        self._stacked_every_open = False

        self.ui.pushButton_stacked_new.clicked.connect(self.click_new_stacked_form)
        self.ui.pushButton_stacked_remove.clicked.connect(
            self.click_remove_stacked_form
        )
        self.ui.pushButton_stacked_apply.clicked.connect(self.click_apply_stacked_forms)
        self.ui.pushButton_stacked_match.clicked.connect(self.click_match_stacked_items)
        self.ui.pushButton_stacked_unmatch.clicked.connect(
            self.click_unmatch_stacked_items
        )
        self.ui.tableWidget_stacked_forms.itemSelectionChanged.connect(
            self._on_stacked_form_selected
        )
        self.ui.lineEdit_stacked_item_search.textChanged.connect(
            self._on_stacked_search_changed
        )
        grid = self.ui.tableView_stacked_items
        for view in (grid, grid.frozen):
            view.clicked.connect(self._on_stacked_grid_clicked)
            view.doubleClicked.connect(self._on_stacked_grid_double_clicked)
        grid.selectionModel().selectionChanged.connect(
            self._on_stacked_grid_selection_changed
        )
        self.update_stacked_forms_ui()

    def _on_stacked_search_changed(self, _text: str) -> None:
        self._show_stacked_items()

    def _on_stacked_grid_selection_changed(self, _selected, _deselected) -> None:
        self._update_stacked_item_buttons()

    # ------------------------------------------------------------------
    # Refresh (called by update_all_ui)

    def update_stacked_forms_ui(self) -> None:
        """Show the drafts over the report's data, and the page's state.

        When the report's stacked forms changed (a saved setting was loaded),
        the drafts become the report's.
        """
        applied = list(self.report.stacked_forms)
        if applied != self._stacked_seen:
            self._stacked_drafts = list(applied)
            self._stacked_seen = applied
            self._stacked_apply_again = False
        self._fill_stacked_forms_table(self._current_stacked_row())
        self._show_stacked_state()

    def _forget_applied_stacked_forms(self) -> None:
        """Note that the report no longer has the applied stacked forms.

        (A new Corelisting ZIP starts a new report.) The drafts stay; the
        page asks for Apply again.
        """
        if self._stacked_seen:
            self._stacked_apply_again = True
        self._stacked_seen = []
        self._set_label_text(self.ui.banner_stacked, "")

    def _has_unapplied_stacked_forms(self) -> bool:
        """Whether the page's stacked forms differ from the report's."""
        return self._stripped_stacked_drafts() != list(self.report.stacked_forms)

    # ------------------------------------------------------------------
    # Slots bound to the page's buttons

    def click_new_stacked_form(self) -> None:
        """Add a stacked form without a name or members, selected, its name focused."""
        self._stacked_drafts.append(StackedForm("", ()))
        row = len(self._stacked_drafts) - 1
        self._fill_stacked_forms_table(row)
        self._show_stacked_state()
        edit = self.ui.tableWidget_stacked_forms.cellWidget(row, _NAME_COLUMN)
        if edit is not None:
            edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def click_remove_stacked_form(self) -> None:
        """Remove the selected stacked form from the page (Apply removes it)."""
        row = self._current_stacked_row()
        if row is None:
            return
        del self._stacked_drafts[row]
        remaining = len(self._stacked_drafts)
        self._fill_stacked_forms_table(min(row, remaining - 1) if remaining else None)
        self._show_stacked_state()

    def click_apply_stacked_forms(self) -> None:
        """Apply the page's stacked forms to the report, unless they have problems."""
        drafts = self._stripped_stacked_drafts()
        loaded = self.report.loaded_data
        found = stacking.problems(drafts, loaded.keys(), loaded)
        if found:
            self._set_label_text(
                self.ui.banner_stacked, steps.stacked_problems_message(found)
            )
            return
        apply_stacked_forms(self.report, drafts)
        self._stacked_drafts = list(drafts)
        self._stacked_seen = list(self.report.stacked_forms)
        self._stacked_apply_again = False
        self.update_all_ui()
        self._set_label_text(
            self.ui.banner_stacked, steps.stacked_applied_message(self.report)
        )

    def click_match_stacked_items(self) -> None:
        """Match the selected left-out items into one stacked item.

        The new match is selected and its name box focused, to name it.
        """
        row = self._current_stacked_row()
        if row is None:
            return
        groups, matches = self._selected_stacked_items()
        if matches:
            return
        try:
            matched = stacking.add_match(
                self._stacked_drafts[row], self.report.loaded_data, groups
            )
        except ValueError:
            return  # The button says why (see _update_stacked_item_buttons).
        self._stacked_drafts[row] = matched
        self._after_stacked_items_edit(row, focus_match=len(matched.matches) - 1)

    def click_unmatch_stacked_items(self) -> None:
        """Put the selected matches' items back in Left out."""
        row = self._current_stacked_row()
        if row is None:
            return
        groups, matches = self._selected_stacked_items()
        if not matches or groups:
            return
        self._stacked_drafts[row] = stacking.remove_matches(
            self._stacked_drafts[row], matches
        )
        self._after_stacked_items_edit(row)

    # ------------------------------------------------------------------
    # The Stacked forms table

    def _current_stacked_row(self) -> Optional[int]:
        """The selected stacked form's row (and index in the drafts), if any."""
        table = self.ui.tableWidget_stacked_forms
        rows = table.selectionModel().selectedRows()
        if rows and rows[0].row() < len(self._stacked_drafts):
            return rows[0].row()
        return None

    def _fill_stacked_forms_table(self, select: Optional[int]) -> None:
        """Rebuild the table from the drafts and select row *select*."""
        table = self.ui.tableWidget_stacked_forms
        table.blockSignals(True)
        try:
            for row in range(table.rowCount()):
                for column in (_NAME_COLUMN, _MEMBERS_COLUMN):
                    # Qt deletes a replaced widget later; hide it now so it
                    # isn't left drawn over the table until then.
                    old = table.cellWidget(row, column)
                    if old is not None:
                        old.hide()
            table.setRowCount(len(self._stacked_drafts))
            for row, stacked in enumerate(self._stacked_drafts):
                for column in range(table.columnCount()):
                    # Under the cell widgets, so a double-click opens no editor.
                    cell = QTableWidgetItem("")
                    cell.setFlags(
                        Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                    )
                    if column in (_ITEMS_COLUMN, _ROWS_COLUMN):
                        cell.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                        )
                    table.setItem(row, column, cell)
                table.setCellWidget(row, _NAME_COLUMN, self._stacked_name_edit(row))
                table.setCellWidget(
                    row, _MEMBERS_COLUMN, self._stacked_members_box(row)
                )
                self._show_stacked_form_row(row)
            if select is not None and 0 <= select < table.rowCount():
                table.selectRow(select)
            else:
                table.clearSelection()
        finally:
            table.blockSignals(False)
        self._on_stacked_form_selected()

    def _stacked_name_edit(self, row: int) -> QLineEdit:
        edit = _NameEdit(self._stacked_drafts[row].name)
        edit.setPlaceholderText("Name, e.g. VISITS")
        edit.setAccessibleName("Stacked form name")
        edit.textEdited.connect(partial(self._on_stacked_name_edited, row))
        edit.focused.connect(partial(self._select_stacked_form, row))
        return edit

    def _stacked_members_box(self, row: int) -> ChecklistComboBox:
        box = ChecklistComboBox(
            search_placeholder="Search forms",
            empty_text="Pick two or more forms…",
            no_match_text="No forms match.",
        )
        box.setAccessibleName("Members")
        box.popupOpened.connect(partial(self._on_stacked_members_opened, row))
        box.itemToggled.connect(partial(self._on_stacked_member_toggled, row))
        return box

    def _show_stacked_form_row(self, row: int) -> None:
        """Bring *row*'s members, item count and rows up to date."""
        table = self.ui.tableWidget_stacked_forms
        stacked = self._stacked_drafts[row]
        loaded = self.report.loaded_data
        box = table.cellWidget(row, _MEMBERS_COLUMN)
        box.set_items(self._stacked_member_choices(stacked))
        box.set_summary(self._stacked_members_summary(stacked))
        box.set_footer(
            f"{len(stacked.members)} picked. Stacked forms can't be members."
        )
        items = rows = ""
        if stacked.members:
            plan = stacking.layout(stacked, loaded)
            items = str(len(plan.every) + len(plan.matched))
            rows = f"{plan.rows:,}"
        table.item(row, _ITEMS_COLUMN).setText(items)
        table.item(row, _ROWS_COLUMN).setText(rows)

    def _stacked_member_choices(self, stacked: StackedForm) -> List[ChecklistItem]:
        """The Members checklist: the loaded forms (ticked members not loaded last)."""
        loaded = self.report.loaded_data
        additional = getattr(self, "_additional_form_keys", set())
        choices = []
        for form in sorted(loaded):
            rows = steps.row_count(len(loaded[form]))
            detail = f"Additional input · {rows}" if form in additional else rows
            choices.append(
                ChecklistItem(form, form, detail, checked=form in stacked.members)
            )
        # So a member that isn't loaded can still be unticked.
        choices.extend(
            ChecklistItem(member, member, "Not loaded", checked=True)
            for member in stacked.members
            if member not in loaded
        )
        return choices

    def _stacked_members_summary(self, stacked: StackedForm) -> str:
        loaded = self.report.loaded_data
        names = [
            member if member in loaded else f"{member} (not loaded)"
            for member in stacked.members
        ]
        if len(names) > 4:
            return f"{', '.join(names[:3])}, … ({len(names)} forms)"
        return ", ".join(names)

    def _select_stacked_form(self, row: int) -> None:
        table = self.ui.tableWidget_stacked_forms
        if self._current_stacked_row() != row and row < table.rowCount():
            table.selectRow(row)

    def _on_stacked_form_selected(self) -> None:
        """Show the selected stacked form's items, from the top, unsearched."""
        search = self.ui.lineEdit_stacked_item_search
        search.blockSignals(True)
        search.clear()
        search.blockSignals(False)
        self.ui.pushButton_stacked_remove.setEnabled(
            self._current_stacked_row() is not None
        )
        self._show_stacked_items(keep=())

    def _on_stacked_name_edited(self, row: int, text: str) -> None:
        self._stacked_drafts[row] = replace(self._stacked_drafts[row], name=text)
        if row == self._current_stacked_row():
            self.ui.label_stacked_items.setText(
                self._stacked_items_title(self._stacked_drafts[row])
            )
        self._show_stacked_state()

    def _on_stacked_members_opened(self, row: int) -> None:
        self._select_stacked_form(row)
        self._show_stacked_form_row(row)

    def _on_stacked_member_toggled(self, row: int, form: str, ticked: bool) -> None:
        """Add *form* as the last member, or take it out."""
        stacked = self._stacked_drafts[row]
        members = [member for member in stacked.members if member != form]
        if ticked:
            members.append(form)
        self._stacked_drafts[row] = stacking.with_members(stacked, members)
        # The checklist stays open: update its row in place.
        self._show_stacked_form_row(row)
        if row == self._current_stacked_row():
            self._show_stacked_items(keep=())
        self._show_stacked_state()

    # ------------------------------------------------------------------
    # The items grid

    @staticmethod
    def _stacked_items_title(stacked: StackedForm) -> str:
        return f"Items of {stacked.name.strip() or 'the new stacked form'}"

    def _show_stacked_items(
        self, keep: Optional[Sequence[Tuple[str, object]]] = None, focus_match=None
    ) -> None:
        """Show the selected stacked form's items grid.

        The rows in *keep* (``(kind, key)``, the selected ones by default)
        stay selected; *focus_match* is a match whose name box gets the focus.
        """
        panel = self.ui.panel_stacked_items
        grid = self.ui.tableView_stacked_items
        row = self._current_stacked_row()
        if row is None:
            panel.show_message(SELECT_A_STACKED_FORM, head=False)
            self._update_stacked_item_buttons()
            return
        stacked = self._stacked_drafts[row]
        self.ui.label_stacked_items.setText(self._stacked_items_title(stacked))
        plan = stacking.layout(stacked, self.report.loaded_data)
        if len(plan.present) < 2:
            panel.show_message(PICK_MEMBERS, head=True)
            grid.set_members([])
            self._update_stacked_item_buttons()
            return
        if keep is None:
            keep = grid.selected_keys()
        self._fill_stacked_grid(stacked, plan)
        panel.show_grid()
        rows = [grid.row_of(kind, key) for kind, key in keep]
        if focus_match is not None:
            rows = [grid.row_of(MATCHED, focus_match)]
        grid.select_rows([r for r in rows if r >= 0])
        self._update_stacked_item_buttons()
        if focus_match is not None:
            box = grid.first_widget(grid.row_of(MATCHED, focus_match))
            if box is not None:
                box.setFocus(Qt.FocusReason.OtherFocusReason)
                box.lineEdit().selectAll()

    def _fill_stacked_grid(self, stacked: StackedForm, plan: StackLayout) -> None:
        grid = self.ui.tableView_stacked_items
        loaded = self.report.loaded_data
        narrow = len(plan.present) >= NARROW_FROM
        headers = []
        for member in plan.present:
            rows = steps.row_count(len(loaded[member]))
            headers.append(
                (member if narrow else f"{member}  {rows}", f"{member} · {rows}")
            )
        grid.set_members(headers)

        query = self.ui.lineEdit_stacked_item_search.text().strip().casefold()

        def hit(*names: str) -> bool:
            return not query or any(query in name.casefold() for name in names)

        def ticks(members: Sequence[str]) -> List[bool]:
            return [member in members for member in plan.present]

        grid.add_section(
            EVERY,
            "In every member",
            len(plan.every),
            "Same name in every member; rename them on Order & rename.",
            opened=self._stacked_every_open,
        )
        if self._stacked_every_open:
            for group in plan.every:
                if hit(group.name):
                    grid.add_item(EVERY, group.name, group.name, ticks(group.members))

        grid.add_section(
            MATCHED,
            "Matched",
            len(plan.matched),
            "You name these: pick one of the names or type a new one.",
        )
        if not plan.matched:
            grid.add_note("No matches yet. Select left-out items below, then Match.")
        for item in plan.matched:
            match = stacked.matches[item.index]
            if not hit(item.name, *match.names):
                continue
            grid_row = grid.add_item(MATCHED, item.index, item.name, ticks(()))
            grid.set_first_widget(grid_row, self._match_name_box(match, item.index))
            for column, member in enumerate(plan.present, start=1):
                grid.set_cell_widget(
                    grid_row,
                    column,
                    self._match_item_box(plan, match, item, member, column),
                )

        grid.add_section(
            LEFT_OUT,
            "Left out",
            len(plan.left_out),
            "Not in the stacked form unless you match them.",
        )
        if not plan.left_out:
            grid.add_note("Nothing left out.")
        for group in plan.left_out:
            if hit(group.name):
                grid.add_item(LEFT_OUT, group.name, group.name, ticks(group.members))

    def _match_name_box(self, match: Match, index: int) -> QComboBox:
        box = _MatchNameBox(match.names, match.name)
        box.currentTextChanged.connect(partial(self._on_match_renamed, index))
        box.lineEdit().focused.connect(partial(self._on_match_focused, index))
        return box

    def _match_item_box(
        self,
        plan: StackLayout,
        match: Match,
        item: MatchedItem,
        member: str,
        column: int,
    ) -> QComboBox:
        """*member*'s cell (in *column*) of a matched row: what it gives, and could."""
        box = _MatchItemBox(
            member,
            item.name,
            stacking.match_choices(plan, self.report.loaded_data, item.index, member),
            steps.stacked_cell_warning(item, match, member),
        )
        box.picked.connect(
            partial(self._on_match_item_picked, item.index, member, column)
        )
        box.lineEdit().focused.connect(
            partial(self._on_match_focused, item.index, scroll=False)
        )
        return box

    def _on_match_renamed(self, index: int, name: str) -> None:
        row = self._current_stacked_row()
        if row is None:
            return
        self._stacked_drafts[row] = stacking.rename_match(
            self._stacked_drafts[row], index, name
        )
        self._show_stacked_state()

    def _on_match_item_picked(
        self, index: int, member: str, column: int, picked: Optional[str]
    ) -> None:
        """Give the match at *index* *member*'s item *picked* (``None``: none).

        The grid shows the edit where it was scrolled, the cell keeping the
        focus unless its match went.
        """
        row = self._current_stacked_row()
        if row is None:
            return
        stacked = self._stacked_drafts[row]
        edited = stacking.set_match_item(
            stacked, self.report.loaded_data, index, member, picked
        )
        if edited == stacked:
            return
        self._stacked_drafts[row] = edited
        grid = self.ui.tableView_stacked_items
        position = grid.scroll_position()
        self._after_stacked_items_edit(row)
        grid.scroll_back(position)
        if len(edited.matches) == len(stacked.matches):
            box = grid.cell_widget(grid.row_of(MATCHED, index), column)
            if box is not None:
                box.setFocus(Qt.FocusReason.OtherFocusReason)

    def _on_match_focused(self, index: int, scroll: bool = True) -> None:
        """Typing in a match's name or cell selects its row (as clicking it would)."""
        grid = self.ui.tableView_stacked_items
        if grid.selected_keys() != [(MATCHED, index)]:
            grid.select_rows([grid.row_of(MATCHED, index)], scroll=scroll)

    def _on_stacked_grid_clicked(self, index: QModelIndex) -> None:
        """Open or close In every member when its row is clicked."""
        if index.data(KIND_ROLE) == SECTION and index.data(KEY_ROLE) == EVERY:
            self._stacked_every_open = not self._stacked_every_open
            self._show_stacked_items()

    def _on_stacked_grid_double_clicked(self, index: QModelIndex) -> None:
        """Keep a left-out item on its own."""
        if index.data(KIND_ROLE) != LEFT_OUT:
            return
        grid = self.ui.tableView_stacked_items
        grid.select_rows([index.row()])
        self.click_match_stacked_items()

    def _selected_stacked_items(self) -> Tuple[List[str], List[int]]:
        """The selected left-out item names and matches' indexes."""
        keys = self.ui.tableView_stacked_items.selected_keys()
        groups = [key for kind, key in keys if kind == LEFT_OUT]
        matches = [key for kind, key in keys if kind == MATCHED]
        return groups, matches

    def _update_stacked_item_buttons(self) -> None:
        """Match only left-out items from different members; Unmatch only matches."""
        match_button = self.ui.pushButton_stacked_match
        unmatch_button = self.ui.pushButton_stacked_unmatch
        row = self._current_stacked_row()
        showing = self.ui.panel_stacked_items.message() == ""
        if row is None or not showing:
            match_button.setEnabled(False)
            unmatch_button.setEnabled(False)
            return
        groups, matches = self._selected_stacked_items()
        why = ""
        if matches:
            why = "Select only left-out items to match them."
        else:
            try:
                stacking.add_match(
                    self._stacked_drafts[row], self.report.loaded_data, groups
                )
            except ValueError as problem:
                why = str(problem)
        match_button.setEnabled(not why)
        if why:
            match_button.setToolTip(why)
        elif len(groups) == 1:
            match_button.setToolTip(f"Keep {groups[0]} on its own")
        else:
            match_button.setToolTip(
                f"Match {' with '.join(groups)} into one stacked item"
            )
        unmatch = bool(matches) and not groups
        unmatch_button.setEnabled(unmatch)
        unmatch_button.setToolTip(
            "Put their items back in Left out"
            if unmatch
            else "Select matched items to unmatch them"
        )

    def _after_stacked_items_edit(self, row: int, focus_match=None) -> None:
        """Show an edit of the items: the row's counts, the grid, the state."""
        self._show_stacked_form_row(row)
        search = self.ui.lineEdit_stacked_item_search
        if focus_match is not None and search.text():
            # The new match shows whatever the search.
            search.blockSignals(True)
            search.clear()
            search.blockSignals(False)
        self._show_stacked_items(keep=(), focus_match=focus_match)
        self._show_stacked_state()

    # ------------------------------------------------------------------
    # The page's state

    def _stripped_stacked_drafts(self) -> List[StackedForm]:
        """The drafts with the names typed on the page trimmed."""
        return [
            replace(
                stacked,
                name=stacked.name.strip(),
                matches=tuple(
                    Match(match.name.strip(), match.items) for match in stacked.matches
                ),
            )
            for stacked in self._stacked_drafts
        ]

    def _show_stacked_state(self) -> None:
        """The standing banner: apply again, not applied yet, a conflict, or what's missing."""
        if self._stacked_apply_again and self._stacked_drafts:
            state = steps.APPLY_STACKED_AGAIN
        elif self._has_unapplied_stacked_forms():
            state = steps.STACKED_NOT_APPLIED
        else:
            state = steps.stacked_conflict_message(
                self.report
            ) or steps.stacked_missing_message(self.report)
        self._set_label_text(self.ui.banner_stacked_state, state)
