"""The Display button: a header button whose popover sets appearance and density.

The choices apply immediately and are shared by every CCI tool, because
:class:`~cci_ui.theme.manager.ThemeManager` stores them in shared settings.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName, icon
from cci_ui.theme.manager import ThemeManager, ThemeMode, current, theme_events
from cci_ui.theme.palette import qcolor
from cci_ui.theme.qss import register_qss
from cci_ui.theme.tokens import Density
from cci_ui.widgets.buttons import set_variant
from cci_ui.widgets.labels import text_label
from cci_ui.widgets.segmented import Segment, SegmentedControl

register_qss(
    """
QFrame[cciRole="popover"] {
    background: ${bg_surface};
    border: 1px solid ${border_card};
    border-radius: 12px;
}
"""
)

APPEARANCE_SEGMENTS = (
    Segment(ThemeMode.SYSTEM.value, "System", IconName.APPEARANCE_SYSTEM),
    Segment(ThemeMode.LIGHT.value, "Light", IconName.APPEARANCE_LIGHT),
    Segment(ThemeMode.DARK.value, "Dark", IconName.APPEARANCE_DARK),
)
DENSITY_SEGMENTS = (
    Segment(Density.COMFORTABLE.value, "Comfortable"),
    Segment(Density.COMPACT.value, "Compact"),
)

#: Transparent margin around the card, room for its shadow.
_SHADOW_MARGIN = 12


class DisplayPopover(QWidget):
    """Popup with the Appearance and Density choices."""

    def __init__(self, theme: ThemeManager, parent: Optional[QWidget] = None) -> None:
        # No native shadow: it would outline the transparent margin that holds
        # the card's own soft shadow.
        flags = (
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        super().__init__(parent, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._theme = theme
        self._anchor: Optional[QWidget] = None

        card = QFrame()
        card.setProperty("cciRole", "popover")
        self._shadow = QGraphicsDropShadowEffect(card)
        self._shadow.setBlurRadius(24)
        self._shadow.setOffset(0, 6)
        card.setGraphicsEffect(self._shadow)

        grid = QGridLayout(card)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.addWidget(text_label("Display", style="headline"), 0, 0, 1, 2)
        grid.addWidget(text_label("Appearance", tone="secondary"), 1, 0)
        self.appearance = SegmentedControl(APPEARANCE_SEGMENTS, theme.mode.value)
        grid.addWidget(self.appearance, 1, 1)
        grid.addWidget(text_label("Density", tone="secondary"), 2, 0)
        self.density = SegmentedControl(DENSITY_SEGMENTS, theme.density.value)
        grid.addWidget(self.density, 2, 1)
        note = text_label(
            "Shared by all CCI tools. Compact fits more rows on laptop screens.",
            style="footnote",
            wrap=True,
        )
        grid.addWidget(note, 3, 0, 1, 2)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(*(_SHADOW_MARGIN,) * 4)
        outer.addWidget(card)

        self.appearance.currentChanged.connect(
            lambda key: theme.set_mode(ThemeMode(key))
        )
        self.density.currentChanged.connect(lambda key: theme.set_density(Density(key)))
        theme_events().changed.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        self.appearance.set_current(self._theme.mode.value)
        self.density.set_current(self._theme.density.value)
        self._shadow.setColor(qcolor(current().colors.shadow_toast))
        if self.isVisible() and self._anchor is not None:
            # Density changes the size; stay attached to the button. Wait until
            # the button itself has been resized for the new density.
            QTimer.singleShot(0, self._replace)

    def _replace(self) -> None:
        if self.isVisible() and self._anchor is not None:
            self._place(self._anchor)

    def show_below(self, anchor: QWidget) -> None:
        """Open under *anchor*, right edges aligned, kept on its screen."""
        self._anchor = anchor
        self._sync()
        self._place(anchor)
        self.show()

    def _place(self, anchor: QWidget) -> None:
        self.adjustSize()
        self.resize(self.sizeHint())
        bottom_right = anchor.mapToGlobal(QPoint(anchor.width(), anchor.height()))
        x = bottom_right.x() - self.width() + _SHADOW_MARGIN
        y = bottom_right.y() + 6 - _SHADOW_MARGIN
        screen = QGuiApplication.screenAt(bottom_right) or anchor.screen()
        if screen is not None:
            area = screen.availableGeometry()
            x = max(area.left(), min(x, area.right() - self.width()))
            y = max(area.top(), min(y, area.bottom() - self.height()))
        self.move(x, y)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # A click on the Display button while open should just close the
        # popover, not reopen it (Qt would replay the press to the button).
        anchor = self._anchor
        if anchor is not None:
            local = anchor.mapFromGlobal(event.globalPosition().toPoint())
            if anchor.rect().contains(local):
                self.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)
        super().mousePressEvent(event)


class DisplayButton(QToolButton):
    """The ◐ header button that opens the :class:`DisplayPopover`."""

    def __init__(self, theme: ThemeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setIcon(icon(IconName.DISPLAY))
        self.setToolTip("Display: appearance and density")
        self.setAccessibleName("Display settings")
        self.setProperty("iconOnly", True)
        set_variant(self, "ghost")
        self.popover = DisplayPopover(theme, self)
        self.clicked.connect(lambda: self.popover.show_below(self))


__all__ = ["APPEARANCE_SEGMENTS", "DENSITY_SEGMENTS", "DisplayButton", "DisplayPopover"]
