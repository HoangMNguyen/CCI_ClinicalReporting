"""The inside of every tool's window: sidebar, header, pages, and overlays.

:class:`AppShell` arranges an optional :class:`~cci_ui.widgets.sidebar.Sidebar`
beside a header and a stack of pages. Below ``LAYOUT.sidebar_collapse_below``
window width the sidebar collapses to icons (with a dead zone, see
:mod:`~cci_ui.widgets.responsive`); the ≡ button or Ctrl+\\ toggles it at
any width, and that choice holds until the window next crosses the
threshold. The shell also owns the window's busy overlay.
"""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.theme.manager import ThemeManager, current, theme_events
from cci_ui.theme.qss import register_qss
from cci_ui.theme.tokens import LAYOUT
from cci_ui.widgets.busy import BusyOverlay
from cci_ui.widgets.display import DisplayButton
from cci_ui.widgets.labels import IconLabel, text_label
from cci_ui.widgets.responsive import Breakpoint
from cci_ui.widgets.sidebar import Sidebar

register_qss(
    """
QFrame[cciRole="appHeader"] {
    background: ${bg_window};
    border: none;
    border-bottom: 1px solid ${separator};
}
"""
)

#: Shortcut that shows or hides the sidebar.
SIDEBAR_SHORTCUT = "Ctrl+\\"


class AppHeader(QFrame):
    """The bar above the pages: where you are on the left, tools on the right."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("cciRole", "appHeader")
        self.context_label = text_label("", style="headline")
        self._chevron = IconLabel(IconName.BREADCRUMB, "tertiary", 14)
        self.page_label = text_label("", tone="secondary")
        self._trailing = QHBoxLayout()
        self._trailing.setSpacing(4)

        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(6)
        self._layout.addWidget(self.context_label)
        self._layout.addWidget(self._chevron)
        self._layout.addWidget(self.page_label)
        self._layout.addStretch(1)
        self._layout.addLayout(self._trailing)
        theme_events().changed.connect(self._apply_metrics)
        self._apply_metrics()
        self.set_context("")

    def _apply_metrics(self) -> None:
        metrics = current().metrics
        self.setFixedHeight(metrics.header_h)
        self._layout.setContentsMargins(metrics.page_margin, 0, 10, 0)

    def set_context(self, context: str, page: str = "") -> None:
        """Show "<context> › <page>" (e.g. "DEMO01 › Joins"), or just one of them."""
        self.context_label.setText(context)
        self.context_label.setVisible(bool(context))
        self.page_label.setText(page)
        self.page_label.setVisible(bool(page))
        self._chevron.setVisible(bool(context and page))

    def add_trailing(self, widget: QWidget) -> None:
        self._trailing.addWidget(widget)


class AppShell(QWidget):
    """Sidebar (optional), header with the Display button, pages, busy overlay."""

    #: Emitted with the page key whenever the current page changes.
    currentPageChanged = Signal(str)
    #: Emitted with True when the sidebar collapses to icons.
    sidebarCollapsedChanged = Signal(bool)
    #: Emitted with the new width when the user drags the sidebar's edge.
    sidebarWidthChanged = Signal(int)

    def __init__(
        self,
        theme: ThemeManager,
        *,
        title: str,
        with_sidebar: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._title = title
        self._pages: Dict[str, QWidget] = {}
        self._page_titles: Dict[str, str] = {}
        self._sections: Dict[str, None] = {}
        self._current = ""
        self._context = ""
        self._sidebar_width = LAYOUT.sidebar_w
        self._breakpoint = Breakpoint(LAYOUT.sidebar_collapse_below)
        # After restore_sidebar(), the first width seen only primes the
        # breakpoint, so the restored state isn't overridden on first show.
        self._keep_restored_state = False

        self.header = AppHeader()
        self.display_button = DisplayButton(theme)
        self.header.add_trailing(self.display_button)
        self.stack = QStackedWidget()
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header)
        main_layout.addWidget(self.stack, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar: Optional[Sidebar] = None
        self.splitter: Optional[QSplitter] = None
        if with_sidebar:
            self.sidebar = Sidebar(title)
            self.sidebar.currentChanged.connect(self.set_current)
            self.sidebar.toggleRequested.connect(self.toggle_sidebar)
            self.splitter = QSplitter(Qt.Orientation.Horizontal)
            self.splitter.setChildrenCollapsible(False)
            self.splitter.addWidget(self.sidebar)
            self.splitter.addWidget(main)
            self.splitter.setStretchFactor(0, 0)
            self.splitter.setStretchFactor(1, 1)
            self.splitter.splitterMoved.connect(self._remember_sidebar_width)
            layout.addWidget(self.splitter)
            self._apply_sidebar_width()
            shortcut = QShortcut(QKeySequence(SIDEBAR_SHORTCUT), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(self.toggle_sidebar)
        else:
            self.header.set_context(title)
            layout.addWidget(main)

        #: Covers the whole shell (sidebar included) while work runs.
        self.busy = BusyOverlay(self)

    # ------------------------------------------------------------------
    # Pages

    def add_page(
        self,
        key: str,
        page: QWidget,
        *,
        title: str,
        icon_name: Optional[str] = None,
        section: Optional[str] = None,
    ) -> None:
        """Add a page; with a sidebar it also gets an item (in *section*).

        Pages appear in the order they are added, so add them section by
        section; a new section title starts where the next page is added.
        """
        if key in self._pages:
            raise ValueError(f"The shell already has a page {key!r}")
        self._pages[key] = page
        self._page_titles[key] = title
        self.stack.addWidget(page)
        if self.sidebar is not None:
            if section and section not in self._sections:
                self._sections[section] = None
                self.sidebar.add_section(section)
            self.sidebar.add_item(key, title, icon_name or IconName.INFO)
        if not self._current:
            self.set_current(key)

    def page(self, key: str) -> QWidget:
        return self._pages[key]

    def current(self) -> str:
        return self._current

    def set_current(self, key: str) -> None:
        """Show page *key*; emits :attr:`currentPageChanged` if it changed."""
        page = self._pages[key]
        self.stack.setCurrentWidget(page)
        if self.sidebar is not None:
            self.sidebar.set_current(key)
        if key != self._current:
            self._current = key
            self._update_header()
            self.currentPageChanged.emit(key)

    def set_context(self, context: str) -> None:
        """What the header shows before the page title, e.g. the study name."""
        self._context = context
        self._update_header()

    def _update_header(self) -> None:
        if self.sidebar is None:
            self.header.set_context(self._context or self._title)
        else:
            self.header.set_context(
                self._context, self._page_titles.get(self._current, "")
            )

    # ------------------------------------------------------------------
    # Sidebar

    def is_sidebar_collapsed(self) -> bool:
        return self.sidebar is not None and self.sidebar.is_collapsed()

    def toggle_sidebar(self) -> None:
        self.set_sidebar_collapsed(not self.is_sidebar_collapsed())

    def set_sidebar_collapsed(self, collapsed: bool) -> None:
        if self.sidebar is None or collapsed == self.sidebar.is_collapsed():
            return
        self.sidebar.set_collapsed(collapsed)
        self._apply_sidebar_width()
        self.sidebarCollapsedChanged.emit(collapsed)

    def restore_sidebar(self, width: int, collapsed: bool) -> None:
        """Apply a remembered width and collapsed state (e.g. before first show)."""
        self.set_sidebar_width(width)
        self.set_sidebar_collapsed(collapsed)
        self._keep_restored_state = True

    def sidebar_width(self) -> int:
        """Width of the expanded sidebar (what the user last dragged it to)."""
        return self._sidebar_width

    def set_sidebar_width(self, width: int) -> None:
        self._sidebar_width = max(
            LAYOUT.sidebar_w_min, min(LAYOUT.sidebar_w_max, width)
        )
        self._apply_sidebar_width()

    def _apply_sidebar_width(self) -> None:
        if self.sidebar is None or self.splitter is None:
            return
        handle = self.splitter.handle(1)
        if self.sidebar.is_collapsed():
            collapsed = LAYOUT.sidebar_collapsed_w
            self.sidebar.setFixedWidth(collapsed)
            handle.setEnabled(False)
            # A fixed width alone doesn't move the splitter's divider.
            self.splitter.setSizes(
                [collapsed, max(1, self.splitter.width() - collapsed)]
            )
        else:
            self.sidebar.setMinimumWidth(LAYOUT.sidebar_w_min)
            self.sidebar.setMaximumWidth(LAYOUT.sidebar_w_max)
            handle.setEnabled(True)
            rest = max(1, self.width() - self._sidebar_width)
            self.splitter.setSizes([self._sidebar_width, rest])

    def _remember_sidebar_width(self, *_args) -> None:
        if self.sidebar is not None and not self.sidebar.is_collapsed():
            self._sidebar_width = self.sidebar.width()
            self.sidebarWidthChanged.emit(self._sidebar_width)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        if self.sidebar is None:
            return
        crossed = self._breakpoint.update(self.width())
        if self._keep_restored_state:
            self._keep_restored_state = False
        elif crossed:
            self.set_sidebar_collapsed(bool(self._breakpoint.below))


__all__ = ["SIDEBAR_SHORTCUT", "AppHeader", "AppShell"]
