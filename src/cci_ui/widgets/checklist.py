"""A combo box whose popup is a searchable checklist, e.g. a stacked form's Members.

:class:`ChecklistComboBox` looks and sizes like any other combo box (it suits
a table cell, like the Joins page's combos). The closed box shows a summary
the page sets (``"SV, DSSVLTFU"``); opening it shows a search field, the
rows with tick boxes, and a hint under them. Clicking a row, or pressing
Space on it, ticks or unticks it and emits ``itemToggled``; the checklist
stays open for more ticks until Escape or a click outside closes it.

The page owns the rows: it answers ``itemToggled`` by updating its own state
and calling :meth:`~ChecklistComboBox.set_items`,
:meth:`~ChecklistComboBox.set_summary` and
:meth:`~ChecklistComboBox.set_footer` again. Doing that while the checklist
is open keeps its search text and scroll position.
"""

from __future__ import annotations

import math
from typing import Iterable, NamedTuple, Optional, Sequence, Tuple

from PySide6.QtCore import (
    QEvent,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QPoint,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QFont, QFontMetrics, QFontMetricsF, QGuiApplication, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionComboBox,
    QStyleOptionViewItem,
    QStylePainter,
    QVBoxLayout,
    QWidget,
)

from cci_ui.theme.manager import current, theme_events
from cci_ui.theme.palette import qcolor
from cci_ui.theme.tokens import TYPE_SCALE
from cci_ui.widgets.labels import text_label
from cci_ui.widgets.search import SearchField
from cci_ui.widgets.views import PlaceholderListWidget

#: Narrowest the checklist opens, however narrow the box (as in the mockup).
_POPUP_MIN_W = 300
#: Tallest the list of rows grows before it scrolls.
_LIST_MAX_H = 248
#: Transparent margin around the card, room for its shadow.
_SHADOW_MARGIN = 12
#: Space between the box and the checklist.
_GAP = 4
#: Space between a row's text and its detail.
_DETAIL_GAP = 12

_KEY_ROLE = Qt.ItemDataRole.UserRole
_DETAIL_ROLE = Qt.ItemDataRole.UserRole + 1


class ChecklistItem(NamedTuple):
    """One row of the checklist.

    *key* identifies the row in ``itemToggled``; *text* is shown in bold and
    *detail* in grey at the right; the search looks in both.
    """

    key: str
    text: str
    detail: str = ""
    checked: bool = False


class _RowDelegate(QStyledItemDelegate):
    """Draws a row as tick box, bold text, and the detail aligned right."""

    def paint(self, painter, option, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        view = opt.widget
        style = view.style()
        # The keyboard's row looks like the row under the pointer.
        if view.hasFocus() and index == view.currentIndex():
            opt.state |= QStyle.StateFlag.State_MouseOver
        text, detail = opt.text, index.data(_DETAIL_ROLE) or ""
        opt.text = ""
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, view)
        area = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, view)
        colors = current().colors
        text_metrics = QFontMetrics(opt.font)
        text_w = text_metrics.horizontalAdvance(text)
        painter.save()
        if detail:
            detail_font = QFont(option.font)
            detail_font.setPixelSize(TYPE_SCALE["callout"].size)
            detail_font.setWeight(QFont.Weight(TYPE_SCALE["callout"].weight))
            metrics = QFontMetrics(detail_font)
            room = area.width() - _DETAIL_GAP
            # The real width rounded up: rounded down (horizontalAdvance), a
            # detail such as "35 rows" is cut to "35 ro…" though it fits.
            detail_w = math.ceil(QFontMetricsF(detail_font).horizontalAdvance(detail))
            if text_w + detail_w > room:
                # Each keeps at least half the row; the other gets the rest.
                text_w = min(text_w, max(room // 2, room - detail_w))
                detail_w = room - text_w
            place = QRect(
                area.right() - detail_w + 1, area.top(), detail_w, area.height()
            )
            painter.setFont(detail_font)
            painter.setPen(qcolor(colors.text_secondary))
            painter.drawText(
                place,
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                metrics.elidedText(detail, Qt.TextElideMode.ElideRight, detail_w),
            )
            area.setRight(place.left() - _DETAIL_GAP)
        painter.setFont(opt.font)
        painter.setPen(qcolor(colors.text_primary))
        painter.drawText(
            area,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            text_metrics.elidedText(text, Qt.TextElideMode.ElideRight, area.width()),
        )
        painter.restore()


class _ChecklistView(PlaceholderListWidget):
    """The rows; a click or Space ticks a row instead of selecting it.

    A ticked row is also shown selected, as in the mockup.
    """

    toggleRequested = Signal(QListWidgetItem)
    leaveTop = Signal()

    def __init__(self, placeholder: str) -> None:
        super().__init__(placeholder)
        self.setProperty("cciRole", "embedded")
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setItemDelegate(_RowDelegate(self))
        # A quick second click ticks again rather than doing nothing.
        self.clicked.connect(self._toggle_index)
        self.doubleClicked.connect(self._toggle_index)

    def _toggle_index(self, index: QModelIndex) -> None:
        item = self.item(index.row())
        if item is not None:
            self.toggleRequested.emit(item)

    def _is_empty(self) -> bool:
        return all(self.isRowHidden(row) for row in range(self.count()))

    def visible_rows(self) -> Tuple[int, ...]:
        return tuple(row for row in range(self.count()) if not self.isRowHidden(row))

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        item = self.currentItem()
        if event.key() == Qt.Key.Key_Space and item is not None:
            if not self.isRowHidden(self.row(item)):
                self.toggleRequested.emit(item)
            return
        rows = self.visible_rows()
        if event.key() == Qt.Key.Key_Up and (
            not rows or item is None or self.row(item) <= rows[0]
        ):
            self.leaveTop.emit()
            return
        super().keyPressEvent(event)


class _ChecklistPopup(QWidget):
    """The open checklist: search, rows, and a hint, on a card with a shadow."""

    toggled = Signal(str, bool)

    def __init__(self, parent: QWidget, search_placeholder: str, no_match: str):
        # No native shadow: it would outline the transparent margin that holds
        # the card's own soft shadow.
        flags = (
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        super().__init__(parent, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._anchor = parent

        card = QFrame()
        card.setProperty("cciRole", "popover")
        self._shadow = QGraphicsDropShadowEffect(card)
        self._shadow.setBlurRadius(24)
        self._shadow.setOffset(0, 6)
        card.setGraphicsEffect(self._shadow)

        self.search = SearchField(search_placeholder)
        self.list = _ChecklistView(no_match)
        self.footer = text_label(style="footnote", wrap=True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        layout.addWidget(self.footer)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(*(_SHADOW_MARGIN,) * 4)
        outer.addWidget(card)

        self.search.textChanged.connect(self._filter)
        self.search.installEventFilter(self)
        self.list.toggleRequested.connect(self._toggle)
        self.list.leaveTop.connect(self.search.setFocus)
        theme_events().changed.connect(self._sync_theme)
        self._sync_theme()

    # -- rows

    def set_items(self, items: Sequence[ChecklistItem]) -> None:
        """Show *items*; the search text, scroll position and keyboard row stay."""
        view = self.list
        keys = [view.item(row).data(_KEY_ROLE) for row in range(view.count())]
        if keys != [entry.key for entry in items]:
            scroll = view.verticalScrollBar().value()
            focused = view.currentItem()
            focused_key = focused.data(_KEY_ROLE) if focused is not None else None
            view.clear()
            for entry in items:
                row = QListWidgetItem()
                row.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                row.setData(_KEY_ROLE, entry.key)
                font = row.font()
                font.setWeight(QFont.Weight(TYPE_SCALE["headline"].weight))
                row.setFont(font)
                view.addItem(row)
                if entry.key == focused_key:
                    view.setCurrentItem(row, QItemSelectionModel.SelectionFlag.NoUpdate)
            self._fill(items)
            view.doItemsLayout()
            view.verticalScrollBar().setValue(scroll)
        else:
            self._fill(items)

    def _fill(self, items: Sequence[ChecklistItem]) -> None:
        for row, entry in enumerate(items):
            item = self.list.item(row)
            item.setText(entry.text)
            item.setData(_DETAIL_ROLE, entry.detail)
            self._show_checked(item, entry.checked)
        self._filter(self.search.text())
        self._fit()

    def _show_checked(self, item: QListWidgetItem, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        item.setCheckState(state)
        # Through the selection model: the item's own setSelected does nothing
        # in a view where the user can't select.
        flag = QItemSelectionModel.SelectionFlag
        self.list.selectionModel().select(
            self.list.indexFromItem(item), flag.Select if checked else flag.Deselect
        )

    def _toggle(self, item: QListWidgetItem) -> None:
        checked = item.checkState() != Qt.CheckState.Checked
        self._show_checked(item, checked)
        self.toggled.emit(item.data(_KEY_ROLE), checked)

    def _filter(self, text: str) -> None:
        needle = text.strip().casefold()
        view = self.list
        for row in range(view.count()):
            item = view.item(row)
            haystack = f"{item.text()}\n{item.data(_DETAIL_ROLE) or ''}".casefold()
            view.setRowHidden(row, bool(needle) and needle not in haystack)
        view.viewport().update()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        # Down from the search field moves on to the rows.
        if (
            watched is self.search
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Down
        ):
            rows = self.list.visible_rows()
            if rows:
                self.list.setFocus(Qt.FocusReason.TabFocusReason)
                self.list.setCurrentRow(
                    rows[0], QItemSelectionModel.SelectionFlag.NoUpdate
                )
            return True
        return super().eventFilter(watched, event)

    def set_footer(self, text: str) -> None:
        self.footer.setText(text)
        self.footer.setVisible(bool(text))
        self._fit()

    # -- size and place

    def _fit(self) -> None:
        """Show every row up to :data:`_LIST_MAX_H`, then scroll."""
        view = self.list
        row_h = max(view.sizeHintForRow(0), current().metrics.row_h)
        rows = max(view.count(), 2)  # room for the "no matches" text
        frame = 2 * view.frameWidth()
        view.setFixedHeight(min(rows * row_h, _LIST_MAX_H) + frame)
        if self.isVisible():
            self._place()

    def open_under(self) -> None:
        self.search.clear()
        self.list.scrollToTop()
        self._fit()
        self._place()
        self.show()
        self.search.setFocus(Qt.FocusReason.PopupFocusReason)

    def _place(self) -> None:
        anchor = self._anchor
        width = max(_POPUP_MIN_W, anchor.width()) + 2 * _SHADOW_MARGIN
        layout = self.layout()
        layout.activate()
        height = (
            layout.totalHeightForWidth(width)
            if layout.hasHeightForWidth()
            else layout.totalSizeHint().height()
        )
        self.resize(width, height)
        below = anchor.mapToGlobal(QPoint(0, anchor.height() + _GAP))
        x, y = below.x() - _SHADOW_MARGIN, below.y() - _SHADOW_MARGIN
        screen = QGuiApplication.screenAt(below) or anchor.screen()
        if screen is not None:
            area = screen.availableGeometry()
            if y + height > area.bottom() + 1:
                # No room below: open above the box instead.
                top = anchor.mapToGlobal(QPoint(0, 0)).y()
                y = top - _GAP - height + _SHADOW_MARGIN
            x = max(area.left(), min(x, area.right() + 1 - width))
            y = max(area.top(), y)
        self.move(x, y)

    def _sync_theme(self) -> None:
        self._shadow.setColor(qcolor(current().colors.shadow_toast))
        if self.isVisible():
            # Density changes the row height; wait until the rows have it.
            QTimer.singleShot(0, self._fit)

    # -- closing

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # A click on the box while open should just close the checklist, not
        # reopen it (Qt would replay the press to the box).
        anchor = self._anchor
        local = anchor.mapFromGlobal(event.globalPosition().toPoint())
        if anchor.rect().contains(local):
            self.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._anchor.update()

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().hideEvent(event)
        self._anchor.update()


class ChecklistComboBox(QComboBox):
    """A combo box that opens a searchable checklist instead of a list.

    ``currentText()`` is the summary set with :meth:`set_summary`; while it
    is blank the box shows *empty_text* in the placeholder color.
    ``popupOpened`` is emitted just before the checklist shows, so a page
    can refresh the rows then; ``itemToggled(key, checked)`` after each tick.
    """

    itemToggled = Signal(str, bool)
    popupOpened = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        search_placeholder: str = "Search",
        empty_text: str = "",
        no_match_text: str = "No matches.",
    ) -> None:
        super().__init__(parent)
        self._search_placeholder = search_placeholder
        self._no_match_text = no_match_text
        self._items: Tuple[ChecklistItem, ...] = ()
        self._footer = ""
        # Made when first opened, so building a page shows no extra window.
        self._popup: Optional[_ChecklistPopup] = None
        self.setPlaceholderText(empty_text)

    # -- what the page sets

    def set_items(self, items: Iterable[ChecklistItem]) -> None:
        """Show these rows; if open, the search text and scroll position stay."""
        self._items = tuple(items)
        if self._popup is not None:
            self._popup.set_items(self._items)

    def set_summary(self, text: str) -> None:
        """The text of the closed box (blank shows the empty text)."""
        if not text:
            self.clear()
        elif self.count():
            self.setItemText(0, text)
        else:
            self.addItem(text)
            self.setCurrentIndex(0)
        self.update()

    def set_footer(self, text: str) -> None:
        """The hint under the rows, e.g. "2 picked."."""
        self._footer = text
        if self._popup is not None:
            self._popup.set_footer(text)

    def is_open(self) -> bool:
        """Whether the checklist is showing."""
        return self._popup is not None and self._popup.isVisible()

    # -- opening and closing

    def showPopup(self) -> None:  # noqa: N802 (Qt override)
        """Open the checklist under the box, with the search field focused."""
        if self.is_open():
            return
        self.popupOpened.emit()
        popup = self._popup
        if popup is None:
            popup = self._popup = _ChecklistPopup(
                self, self._search_placeholder, self._no_match_text
            )
            popup.toggled.connect(self._toggled)
            popup.set_items(self._items)
            popup.set_footer(self._footer)
        popup.open_under()

    def hidePopup(self) -> None:  # noqa: N802 (Qt override)
        """Close the checklist."""
        if self._popup is not None:
            self._popup.hide()

    def _toggled(self, key: str, checked: bool) -> None:
        self._items = tuple(
            item._replace(checked=checked) if item.key == key else item
            for item in self._items
        )
        self.itemToggled.emit(key, checked)

    # -- painting

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Drawn here rather than by QComboBox so a long summary ends in "…"
        # and the empty text is greyed under the stylesheet too.
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        if self.is_open():
            option.state |= QStyle.StateFlag.State_On
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option)
        field = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            option,
            QStyle.SubControl.SC_ComboBoxEditField,
            self,
        )
        text = self.currentText()
        if not text:
            text = self.placeholderText()
            placeholder = option.palette.placeholderText()
            for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
                option.palette.setBrush(role, placeholder)
        option.currentText = option.fontMetrics.elidedText(
            text, Qt.TextElideMode.ElideRight, field.width()
        )
        painter.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, option)


__all__ = ["ChecklistComboBox", "ChecklistItem"]
