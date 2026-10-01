"""The inside of every tool's window: sidebar, header, pages, and overlays.

:class:`AppShell` arranges an optional :class:`~cci_ui.widgets.sidebar.Sidebar`
beside a header and a stack of pages, above a status bar. Below
``LAYOUT.sidebar_collapse_below`` window width the sidebar collapses to icons
(with a dead zone, see :mod:`~cci_ui.widgets.responsive`); the ≡ button or
Ctrl+\\ toggles it at any width, and that choice holds until the window next
crosses the threshold. With a sidebar, Ctrl+Tab and Ctrl+PgDown also go to
the next page, Ctrl+Shift+Tab and Ctrl+PgUp to the previous one. The shell
also owns the window's busy overlay.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Union

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QSizePolicy,
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
from cci_ui.widgets.labels import ElidedLabel, IconLabel, text_label
from cci_ui.widgets.responsive import Breakpoint
from cci_ui.widgets.sidebar import Sidebar
from cci_ui.widgets.status import KIND_ICONS, KINDS

register_qss(
    """
QFrame[cciRole="appHeader"] {
    background: ${bg_window};
    border: none;
    border-bottom: 1px solid ${separator};
}
QFrame[cciRole="statusBar"] {
    background: ${bg_window};
    border: none;
    border-top: 1px solid ${separator};
}
"""
)

#: Shortcut that shows or hides the sidebar.
SIDEBAR_SHORTCUT = "Ctrl+\\"
#: Shortcuts to the next and previous page (as a tab widget has).
NEXT_PAGE_SHORTCUTS = (QKeySequence.StandardKey.NextChild, "Ctrl+PgDown")
PREVIOUS_PAGE_SHORTCUTS = (QKeySequence.StandardKey.PreviousChild, "Ctrl+PgUp")
#: How long after the window first shows a restored sidebar state holds,
#: whatever sizes the window passes through while it opens (a window
#: reopening maximized is first laid out at its normal size).
RESTORE_SETTLE_MS = 500
#: Share of the status bar's width a message may take; the summary keeps the rest.
MESSAGE_SHARE = 0.6


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


def _status_text() -> ElidedLabel:
    label = ElidedLabel(tone="secondary", mode=Qt.TextElideMode.ElideRight)
    label.setProperty("textStyle", "caption")
    return label


class AppStatusBar(QFrame):
    """The strip along the bottom: a summary on the left, the last message on the right.

    A message shows on one line (line breaks become spaces), shortened when
    it doesn't fit; its tooltip has the whole text.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("cciRole", "statusBar")
        self.summary_label = _status_text()
        self.kind_icon = IconLabel(*KIND_ICONS["info"], size=12)
        self.message_label = _status_text()
        self.message_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self._kind = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)
        layout.addWidget(self.summary_label, 1)
        layout.addSpacing(10)
        layout.addWidget(self.kind_icon)
        layout.addWidget(self.message_label)
        # Only after parenting (see cci_ui.widgets).
        self.kind_icon.setVisible(False)
        theme_events().changed.connect(self._apply_metrics)
        self._apply_metrics()

    def _apply_metrics(self) -> None:
        self.setFixedHeight(current().metrics.status_h)

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text)

    def summary(self) -> str:
        return self.summary_label.text()

    def show_message(self, text: str, kind: str = "info") -> None:
        """Show *text* with the symbol for *kind* (info, success, warning, error)."""
        if kind not in KINDS:
            raise ValueError(f"Unknown message kind {kind!r}; expected one of {KINDS}")
        self._kind = kind
        self.kind_icon.set_icon(*KIND_ICONS[kind])
        self.kind_icon.setVisible(True)
        self.message_label.setText(" ".join(text.split()))

    def clear_message(self) -> None:
        self._kind = ""
        self.kind_icon.setVisible(False)
        self.message_label.setText("")

    def message(self) -> str:
        return self.message_label.text()

    def message_kind(self) -> str:
        """The kind of the message shown, or "" when there is none."""
        return self._kind

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self.message_label.setMaximumWidth(int(self.width() * MESSAGE_SHARE))


class AppShell(QWidget):
    """Sidebar (optional), header with the Display button, pages, status bar.

    Pass the app's :class:`~cci_ui.theme.manager.ThemeManager` as *theme* for
    the header's Display button; without one (tests) the header has none.
    """

    #: Emitted with the page key whenever the current page changes.
    currentPageChanged = Signal(str)
    #: Emitted with True when the sidebar collapses to icons.
    sidebarCollapsedChanged = Signal(bool)
    #: Emitted with the new width when the user drags the sidebar's edge.
    sidebarWidthChanged = Signal(int)

    def __init__(
        self,
        theme: Optional[ThemeManager],
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
        # After restore_sidebar(), widths seen until the window has settled
        # only prime the breakpoint, so the restored state isn't overridden.
        self._keep_restored_state = False
        self._restore_settled = QTimer(self)
        self._restore_settled.setSingleShot(True)
        self._restore_settled.setInterval(RESTORE_SETTLE_MS)
        self._restore_settled.timeout.connect(self._end_restore)

        self.header = AppHeader()
        self.display_button: Optional[DisplayButton] = None
        if theme is not None:
            self.display_button = DisplayButton(theme)
            self.header.add_trailing(self.display_button)
        self.stack = QStackedWidget()
        self.status_bar = AppStatusBar()
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header)
        main_layout.addWidget(self.stack, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
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
            self._add_shortcut(SIDEBAR_SHORTCUT, self.toggle_sidebar)
            for keys in NEXT_PAGE_SHORTCUTS:
                self._add_shortcut(keys, self.next_page)
            for keys in PREVIOUS_PAGE_SHORTCUTS:
                self._add_shortcut(keys, self.previous_page)
        else:
            self.header.set_context(title)
            layout.addWidget(main)
        layout.addWidget(self.status_bar)

        #: Covers the whole shell (sidebar included) while work runs.
        self.busy = BusyOverlay(self)

    def _add_shortcut(
        self, keys: Union[str, QKeySequence.StandardKey], action: Callable[[], None]
    ) -> None:
        # While the focus is anywhere in the shell, whichever page is shown
        # (unlike Page.add_shortcut, which follows one page's content).
        shortcut = QShortcut(QKeySequence(keys), self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(action)

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

    def current_page(self) -> Optional[QWidget]:
        """The page shown, or ``None`` before any page is added."""
        return self._pages.get(self._current)

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

    def next_page(self) -> None:
        """Show the page after the current one (none after the last)."""
        self._step_page(1)

    def previous_page(self) -> None:
        """Show the page before the current one (none before the first)."""
        self._step_page(-1)

    def _step_page(self, step: int) -> None:
        keys = list(self._pages)
        if not keys:
            return
        index = keys.index(self._current) + step
        if 0 <= index < len(keys):
            self.set_current(keys[index])

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
        """Apply a remembered width and collapsed state (before the first show).

        The state holds while the window opens (see :data:`RESTORE_SETTLE_MS`);
        after that, crossing the breakpoint collapses or expands as usual.
        """
        self.set_sidebar_width(width)
        self.set_sidebar_collapsed(collapsed)
        self._keep_restored_state = True
        if self.isVisible():  # Already shown: no showEvent will start the wait.
            self._restore_settled.start()

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

    def _end_restore(self) -> None:
        self._keep_restored_state = False

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        if self._keep_restored_state and not self._restore_settled.isActive():
            self._restore_settled.start()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        if self.sidebar is None:
            return
        crossed = self._breakpoint.update(self.width())
        if crossed and not self._keep_restored_state:
            self.set_sidebar_collapsed(bool(self._breakpoint.below))


__all__ = [
    "MESSAGE_SHARE",
    "NEXT_PAGE_SHORTCUTS",
    "PREVIOUS_PAGE_SHORTCUTS",
    "RESTORE_SETTLE_MS",
    "SIDEBAR_SHORTCUT",
    "AppHeader",
    "AppShell",
    "AppStatusBar",
]
