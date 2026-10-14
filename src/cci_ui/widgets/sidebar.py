"""The sidebar: steps or pages in sections, with a status badge on each.

Each item shows an icon, a title, and on the right either a count, a ✓ when
done, a warning or error symbol, or "Optional". Collapsed to icons (on narrow
windows), sections become thin lines, titles move to tooltips, and a small
dot marks warnings and errors; with *strip_badges* the collapsed strip is a
little wider and shows each item's count, ✓, warning or error symbol beside
its icon instead.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from PySide6.QtCore import QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName, icon
from cci_ui.theme.manager import current, theme_events
from cci_ui.theme.palette import qcolor
from cci_ui.theme.qss import register_qss
from cci_ui.widgets.buttons import icon_button
from cci_ui.widgets.labels import escape_ampersands, text_label

register_qss(
    """
QFrame[cciRole="sidebar"] {
    background: ${bg_sidebar};
    border: none;
}
QScrollArea[cciRole="sidebarScroll"], QWidget[cciRole="sidebarList"] {
    background: transparent;
    border: none;
}
QLabel[cciRole="sidebarSection"] {
    color: ${text_secondary};
    font-size: 11px;
    font-weight: 600;
    padding: 12px 8px 4px 8px;
}
QFrame[cciRole="sidebarRule"] {
    background: ${separator};
    border: none;
    min-height: 1px;
    max-height: 1px;
}
"""
)

_ICON = 16
_BADGE_ICON = 14
_PAD = 8
_DOT = 7
#: Gap between the icon and its badge in the collapsed badge strip.
_STRIP_GAP = 4


class StepState(str, Enum):
    """What the badge on a sidebar item shows."""

    NONE = "none"
    DONE = "done"
    WARNING = "warning"
    ERROR = "error"
    OPTIONAL = "optional"


_STATE_ICONS = {
    StepState.DONE: (IconName.SUCCESS, "success"),
    StepState.WARNING: (IconName.WARNING, "warning"),
    StepState.ERROR: (IconName.ERROR, "danger"),
}


class SidebarItem(QAbstractButton):
    """One entry; painted directly so the selection pill and badge match the design."""

    def __init__(
        self,
        key: str,
        title: str,
        icon_name: str,
        parent=None,
        *,
        strip_badges: bool = False,
    ):
        super().__init__(parent)
        self.key = key
        self._title = title
        self._icon_name = icon_name
        self._state = StepState.NONE
        self._count: Optional[int] = None
        self._tip = ""
        self._collapsed = False
        self._strip_badges = strip_badges
        self.setCheckable(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        # The title is painted, but Qt still reads the button text for a
        # keyboard shortcut: a lone "&" would make one ("Order & rename").
        self.setText(escape_ampersands(title))
        self._update_tooltip()

    # ------------------------------------------------------------------
    # State

    def title(self) -> str:
        return self._title

    def state(self) -> StepState:
        return self._state

    def count(self) -> Optional[int]:
        return self._count

    def set_status(
        self,
        state: StepState = StepState.NONE,
        count: Optional[int] = None,
        tip: str = "",
    ) -> None:
        self._state = StepState(state)
        self._count = count
        self._tip = tip
        self._update_tooltip()
        self.update()

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self._update_tooltip()
        self.updateGeometry()
        self.update()

    def _update_tooltip(self) -> None:
        detail = self._tip or ("Optional" if self._state is StepState.OPTIONAL else "")
        self.setToolTip(f"{self._title} — {detail}" if detail else self._title)
        self.setAccessibleName(self.toolTip())

    # ------------------------------------------------------------------
    # Size and painting

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        if not self._collapsed:
            width = 180
        else:
            width = 56 if self._strip_badges else 40
        return QSize(width, current().metrics.sidebar_row)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        return QSize(40, current().metrics.sidebar_row)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        colors = current().colors
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        radius = current().metrics.radius_pill

        if self.isChecked():
            active = self.window().isActiveWindow()
            fill = colors.selection if active else colors.selection_inactive
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qcolor(fill))
            painter.drawRoundedRect(rect, radius, radius)
        elif self.underMouse():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qcolor(colors.bg_hover))
            painter.drawRoundedRect(rect, radius, radius)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(qcolor(colors.focus_ring), 2))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

        middle = self.height() // 2
        role = "accent" if self.isChecked() else "secondary"
        if self._collapsed and self._strip_badges:
            self._paint_strip_item(painter, colors, role)
            painter.end()
            return
        if self._collapsed:
            icon_rect = QRect(0, 0, _ICON, _ICON)
            icon_rect.moveCenter(self.rect().center())
            icon(self._icon_name, role).paint(painter, icon_rect)
            if self._state in (StepState.WARNING, StepState.ERROR):
                dot = (
                    colors.warning
                    if self._state is StepState.WARNING
                    else colors.danger
                )
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(qcolor(dot))
                painter.drawEllipse(
                    QRectF(icon_rect.right() - 2, icon_rect.top() - 3, _DOT, _DOT)
                )
            painter.end()
            return

        icon_rect = QRect(_PAD, middle - _ICON // 2, _ICON, _ICON)
        icon(self._icon_name, role).paint(painter, icon_rect)
        badge_width = self._paint_badge(painter, colors)
        text_left = icon_rect.right() + 1 + _PAD
        text_rect = QRect(
            text_left, 0, self.width() - text_left - badge_width - _PAD, self.height()
        )
        painter.setPen(qcolor(colors.text_primary))
        painter.setFont(self.font())
        title = self.fontMetrics().elidedText(
            self._title, Qt.TextElideMode.ElideRight, text_rect.width()
        )
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter), title)
        painter.end()

    def _paint_strip_item(self, painter: QPainter, colors, role: str) -> None:
        """Collapsed with badges: the icon, then its count or state symbol."""
        middle = self.height() // 2
        icon_rect = QRect(_PAD, middle - _ICON // 2, _ICON, _ICON)
        icon(self._icon_name, role).paint(painter, icon_rect)
        left = icon_rect.right() + 1 + _STRIP_GAP
        if self._state in _STATE_ICONS:
            badge = QRect(left, middle - _BADGE_ICON // 2, _BADGE_ICON, _BADGE_ICON)
            icon(*_STATE_ICONS[self._state]).paint(painter, badge)
            return
        if self._state is StepState.OPTIONAL or self._count is None:
            return
        font = QFont(self.font())
        font.setPixelSize(12)
        painter.setFont(font)
        painter.setPen(qcolor(colors.text_secondary))
        area = QRect(left, 0, self.width() - left, self.height())
        painter.drawText(
            area,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            str(self._count),
        )
        painter.setFont(self.font())

    def _paint_badge(self, painter: QPainter, colors) -> int:
        """Draw the badge at the right edge; return the width it took."""
        right = self.width() - _PAD
        middle = self.height() // 2
        if self._state in _STATE_ICONS:
            badge = QRect(
                right - _BADGE_ICON, middle - _BADGE_ICON // 2, _BADGE_ICON, _BADGE_ICON
            )
            icon(*_STATE_ICONS[self._state]).paint(painter, badge)
            return _BADGE_ICON + _PAD
        if self._state is StepState.OPTIONAL:
            text, color, size = "Optional", colors.text_tertiary, 11
        elif self._count is not None:
            text, color, size = str(self._count), colors.text_secondary, 12
        else:
            return 0
        font = QFont(self.font())
        font.setPixelSize(size)
        painter.setFont(font)
        painter.setPen(qcolor(color))
        width = painter.fontMetrics().horizontalAdvance(text)
        area = QRect(right - width, 0, width, self.height())
        painter.drawText(
            area, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), text
        )
        painter.setFont(self.font())
        return width + _PAD


class Sidebar(QFrame):
    """Sections of :class:`SidebarItem`.

    The items share an exclusive :class:`QButtonGroup`, so Qt's own keyboard
    handling applies: Tab reaches the current item and Up/Down pick another.
    With *strip_badges*, collapsed items show their badge beside the icon
    (the strip must be ``LAYOUT.sidebar_badge_strip_w`` wide to fit it).
    """

    #: Emitted with the item's key when the user picks an item.
    currentChanged = Signal(str)
    #: Emitted when the user clicks the collapse button in the sidebar's top row.
    toggleRequested = Signal()

    def __init__(
        self,
        title: str = "",
        parent: Optional[QWidget] = None,
        *,
        strip_badges: bool = False,
    ):
        super().__init__(parent)
        self.setProperty("cciRole", "sidebar")
        self._items: Dict[str, SidebarItem] = {}
        self._order: List[str] = []
        self._section_labels: List[QLabel] = []
        self._section_rules: List[QFrame] = []
        self._collapsed = False
        self._strip_badges = strip_badges
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.buttonClicked.connect(self._on_clicked)

        self._top = QWidget()
        top_layout = QHBoxLayout(self._top)
        top_layout.setContentsMargins(10, 0, 10, 0)
        top_layout.setSpacing(6)
        self.toggle_button = icon_button(IconName.SIDEBAR, "Hide sidebar (Ctrl+\\)")
        self.toggle_button.clicked.connect(self.toggleRequested)
        top_layout.addWidget(self.toggle_button)
        self.title_label = text_label(title, style="headline")
        top_layout.addWidget(self.title_label, 1)

        self._list = QWidget()
        self._list.setProperty("cciRole", "sidebarList")
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(10, 0, 10, 12)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setProperty("cciRole", "sidebarScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # A click on an item mustn't move the focus to the scroll area: the
        # field being edited would commit (and maybe start work) first.
        scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        scroll.setWidget(self._list)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._top)
        layout.addWidget(scroll, 1)

        theme_events().changed.connect(self._apply_metrics)
        self._apply_metrics()

    def _apply_metrics(self) -> None:
        self._top.setFixedHeight(current().metrics.header_h)
        for item in self._items.values():
            item.updateGeometry()

    # ------------------------------------------------------------------
    # Building

    def _insert(self, widget: QWidget) -> None:
        self._list_layout.insertWidget(self._list_layout.count() - 1, widget)

    def add_section(self, title: str) -> None:
        label = QLabel(title)
        label.setProperty("cciRole", "sidebarSection")
        rule = QFrame()
        rule.setProperty("cciRole", "sidebarRule")
        rule.setVisible(False)
        self._section_labels.append(label)
        self._section_rules.append(rule)
        self._insert(label)
        self._insert(rule)
        self._apply_collapsed()

    def add_item(self, key: str, title: str, icon_name: str) -> SidebarItem:
        if key in self._items:
            raise ValueError(f"The sidebar already has an item {key!r}")
        item = SidebarItem(key, title, icon_name, strip_badges=self._strip_badges)
        item.set_collapsed(self._collapsed)
        self._items[key] = item
        self._order.append(key)
        self._group.addButton(item)
        self._insert(item)
        return item

    # ------------------------------------------------------------------
    # State

    def item(self, key: str) -> SidebarItem:
        return self._items[key]

    def keys(self) -> List[str]:
        return list(self._order)

    def current(self) -> str:
        checked = self._group.checkedButton()
        return checked.key if checked is not None else ""

    def set_current(self, key: str) -> None:
        """Select *key* without emitting :attr:`currentChanged`."""
        self._items[key].setChecked(True)

    def set_status(
        self,
        key: str,
        state: StepState = StepState.NONE,
        *,
        count: Optional[int] = None,
        tip: str = "",
    ) -> None:
        self._items[key].set_status(state, count, tip)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self._apply_collapsed()

    def _apply_collapsed(self) -> None:
        collapsed = self._collapsed
        self.title_label.setVisible(not collapsed)
        tip = "Show sidebar (Ctrl+\\)" if collapsed else "Hide sidebar (Ctrl+\\)"
        self.toggle_button.setToolTip(tip)
        self.toggle_button.setAccessibleName(tip)
        self._list_layout.setContentsMargins(
            8 if collapsed else 10, 0, 8 if collapsed else 10, 12
        )
        for index, (label, rule) in enumerate(
            zip(self._section_labels, self._section_rules)
        ):
            label.setVisible(not collapsed)
            rule.setVisible(collapsed and index > 0)
        for item in self._items.values():
            item.set_collapsed(collapsed)

    # ------------------------------------------------------------------
    # Input

    def _on_clicked(self, button) -> None:
        self.currentChanged.emit(button.key)


__all__ = ["Sidebar", "SidebarItem", "StepState"]
