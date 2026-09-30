"""Layouts that rearrange at a width breakpoint without flickering.

Each breakpoint has a dead zone (``LAYOUT.breakpoint_buffer`` wide) around
its threshold: a layout switches to "narrow" below ``threshold - buffer/2``
and back to "wide" only above ``threshold + buffer/2``, so resizing a window
slowly across the threshold doesn't make it jump back and forth.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from cci_ui.theme.tokens import LAYOUT

# Qt's largest widget size (QWIDGETSIZE_MAX), used to lift a size limit.
_NO_LIMIT = (1 << 24) - 1


class Breakpoint:
    """Tracks whether a width is below *threshold*, with a dead zone."""

    def __init__(self, threshold: int, buffer: int = LAYOUT.breakpoint_buffer) -> None:
        self.threshold = threshold
        self.half_buffer = buffer / 2
        self.below: Optional[bool] = None

    def update(self, width: int) -> bool:
        """Record *width*; return True if it moved to the other side."""
        if self.below is None:
            below = width < self.threshold
        elif self.below:
            below = width < self.threshold + self.half_buffer
        else:
            below = width < self.threshold - self.half_buffer
        changed = below != self.below
        self.below = below
        return changed


class ResponsiveSplit(QWidget):
    """A main area with a side panel: beside it when wide, below it when narrow.

    Side by side, the panel is *side_width* wide and can be dragged between
    the panel limits. Stacked, the panel takes at most *stacked_side_share*
    of the height so the main area (a data grid, say) keeps most of it.
    """

    #: Emitted with True when the panel moves below the main area, False when
    #: it moves beside it; also emitted once at the first layout.
    stackedChanged = Signal(bool)

    def __init__(
        self,
        main: QWidget,
        side: QWidget,
        *,
        breakpoint: int = LAYOUT.panel_below_content,
        side_width: int = LAYOUT.panel_w,
        side_min: int = LAYOUT.panel_w_min,
        side_max: int = LAYOUT.panel_w_max,
        stacked_side_share: float = 0.4,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.main = main
        self.side = side
        self._side_width = side_width
        self._side_min = side_min
        self._side_max = side_max
        self._stacked_side_share = stacked_side_share
        self._breakpoint = Breakpoint(breakpoint)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(main)
        self.splitter.addWidget(side)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)

    def is_stacked(self) -> bool:
        return bool(self._breakpoint.below)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        if self._breakpoint.update(self.width()):
            self._arrange()
            self.stackedChanged.emit(self.is_stacked())
        elif self.is_stacked():
            self.side.setMaximumHeight(self._stacked_side_limit())

    def _stacked_side_limit(self) -> int:
        return max(1, int(self.height() * self._stacked_side_share))

    def _arrange(self) -> None:
        if self.is_stacked():
            if self.splitter.orientation() == Qt.Orientation.Horizontal:
                # Keep a panel width the user dragged for when it comes back.
                self._side_width = self.splitter.sizes()[1] or self._side_width
            self.splitter.setOrientation(Qt.Orientation.Vertical)
            self.side.setMinimumWidth(0)
            self.side.setMaximumWidth(_NO_LIMIT)
            limit = self._stacked_side_limit()
            self.side.setMaximumHeight(limit)
            self.splitter.setSizes([max(1, self.height() - limit), limit])
        else:
            self.splitter.setOrientation(Qt.Orientation.Horizontal)
            self.side.setMaximumHeight(_NO_LIMIT)
            self.side.setMinimumWidth(self._side_min)
            self.side.setMaximumWidth(self._side_max)
            main_width = max(1, self.width() - self._side_width)
            self.splitter.setSizes([main_width, self._side_width])


__all__ = ["Breakpoint", "ResponsiveSplit"]
