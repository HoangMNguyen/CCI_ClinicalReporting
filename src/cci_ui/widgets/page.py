"""A page: large title, subtitle, actions, body, and a footer.

Three kinds of page decide how extra window space is used:

- ``form``: a single centred column at most ``LAYOUT.form_max_w`` wide that
  scrolls when the window is short (settings-style pages, the small tools).
- ``workspace``: the body fills the whole width and height; lists and tables
  in it take the extra space and scroll inside themselves.
- ``split``: like workspace, for a main area plus a side panel
  (see :class:`~cci_ui.widgets.responsive.ResponsiveSplit`).

A page with nothing to show yet (no data loaded, say) can show an empty
state in place of its body and header actions: :meth:`Page.set_empty_state`
and :meth:`Page.show_empty_state`. :meth:`Page.add_shortcut` adds a key that
works while the page's content is shown (not its empty state, not when
another page is).
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional, Union

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.theme.manager import current, theme_events
from cci_ui.theme.qss import register_qss
from cci_ui.theme.tokens import LAYOUT
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.labels import escape_ampersands, text_label

register_qss(
    """
QScrollArea[cciRole="page"] {
    background: transparent;
    border: none;
}
QWidget[cciRole="pageContent"] {
    background: transparent;
}
"""
)

#: Space between the header and the body.
_HEADER_GAP = 14


class _Column(QWidget):
    """The form column; it prefers its maximum width.

    A layout that centres a widget sizes it to its preferred width, so this
    makes the column use all the space up to its maximum.
    """

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        return QSize(self.maximumWidth(), super().sizeHint().height())


class PageKind(str, Enum):
    FORM = "form"
    WORKSPACE = "workspace"
    SPLIT = "split"


class Page(QWidget):
    """Base layout for every screen; add content to :attr:`body`."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        *,
        kind: PageKind = PageKind.WORKSPACE,
        max_width: int = LAYOUT.form_max_w,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.kind = PageKind(kind)
        self._max_width = max_width

        self.title_label = text_label(title, style="title1")
        self.subtitle_label = text_label(subtitle, tone="secondary", wrap=True)
        self._actions_widget = QWidget()
        self.actions = QHBoxLayout(self._actions_widget)
        self.actions.setContentsMargins(0, 0, 0, 0)
        self.actions.setSpacing(8)
        self._empty_state: Optional[QWidget] = None

        self._header = QWidget()
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        header_layout.addLayout(titles, 1)
        # Only after parenting (see cci_ui.widgets).
        self.subtitle_label.setVisible(bool(subtitle))
        header_layout.addWidget(self._actions_widget)

        # The body and, when set, the empty state shown in its place.
        self._body_widget = QWidget()
        #: Put the page's content here.
        self.body = QVBoxLayout(self._body_widget)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(12)
        self._main = QVBoxLayout()
        self._main.setContentsMargins(0, 0, 0, 0)
        self._main.addWidget(self._body_widget, 1)

        self._footer_widget = QWidget()
        #: Footer buttons, right-aligned (e.g. "Next: Forms →").
        self.footer = QHBoxLayout(self._footer_widget)
        self.footer.addStretch(1)
        self._footer_widget.setVisible(False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        if self.kind is PageKind.FORM:
            self._build_form(outer)
        else:
            self._build_workspace(outer)

        theme_events().changed.connect(self._apply_metrics)
        self._apply_metrics()

    # ------------------------------------------------------------------
    # Layouts

    def _build_form(self, outer: QVBoxLayout) -> None:
        # The footer lives in the column so it always lines up with the
        # content: at the bottom of a short page, after the content of a long
        # one that scrolls.
        self._column = _Column()
        self._column.setProperty("cciRole", "pageContent")
        self._column_layout = QVBoxLayout(self._column)
        self._column_layout.addWidget(self._header)
        self._column_layout.addLayout(self._main)
        self._column_layout.addStretch(1)
        self._column_layout.addWidget(self._footer_widget)

        content = QWidget()
        content.setProperty("cciRole", "pageContent")
        centering = QHBoxLayout(content)
        centering.setContentsMargins(0, 0, 0, 0)
        # Centred at its preferred width, which is its maximum (see _Column):
        # all the width up to the maximum, in the middle beyond it.
        centering.addWidget(self._column, 0, Qt.AlignmentFlag.AlignHCenter)

        self.scroll_area = QScrollArea()
        self.scroll_area.setProperty("cciRole", "page")
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(content)
        outer.addWidget(self.scroll_area, 1)

    def _build_workspace(self, outer: QVBoxLayout) -> None:
        self._column = None
        self.scroll_area = None
        self._header_margins = QVBoxLayout()
        self._header_margins.addWidget(self._header)
        outer.addLayout(self._header_margins)
        self._body_margins = QVBoxLayout()
        self._body_margins.addLayout(self._main, 1)
        outer.addLayout(self._body_margins, 1)
        outer.addWidget(self._footer_widget)

    def _apply_metrics(self) -> None:
        margin = current().metrics.page_margin
        if self._column is not None:
            self._column.setMaximumWidth(self._max_width + 2 * margin)
            self._column_layout.setContentsMargins(margin, margin, margin, margin)
            self._column_layout.setSpacing(current().metrics.section_gap)
            self.footer.setContentsMargins(0, 0, 0, 0)
        else:
            self._header_margins.setContentsMargins(margin, margin, margin, _HEADER_GAP)
            # The footer spaces the body from the bottom edge when there is one.
            bottom = 0 if self._footer_widget.isVisibleTo(self) else margin
            self._body_margins.setContentsMargins(margin, 0, margin, bottom)
            self.footer.setContentsMargins(margin, 10, margin, 12)

    def title(self) -> str:
        return self.title_label.text()

    def set_subtitle(self, text: str) -> None:
        """Change the line under the title; "" hides it."""
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))

    def add_shortcut(
        self,
        keys: Union[str, QKeySequence, QKeySequence.StandardKey],
        action: Callable[[], None],
    ) -> QShortcut:
        """Run *action* on *keys* while this page's content is shown.

        Not while another page is shown, nor while the page shows its empty
        state. For a button, pass its ``click``: it does nothing while the
        button is disabled.
        """
        # Parented to the body, which is hidden along with the page or by
        # the empty state; a hidden parent turns the shortcut off.
        shortcut = QShortcut(QKeySequence(keys), self._body_widget)
        shortcut.activated.connect(action)
        return shortcut

    # ------------------------------------------------------------------
    # Empty state

    def set_empty_state(self, state: QWidget) -> None:
        """What the page shows instead of its body and actions when empty.

        It stays hidden until :meth:`show_empty_state`; the title, subtitle,
        and footer stay either way.
        """
        if self._empty_state is not None:
            raise ValueError("The page already has an empty state")
        self._empty_state = state
        self._main.addWidget(state, 1)
        state.hide()  # Only after parenting (see cci_ui.widgets).

    def show_empty_state(self, show: bool) -> None:
        """Show the empty state in place of the body and actions, or not."""
        if self._empty_state is None:
            raise ValueError("Call set_empty_state first")
        self._empty_state.setVisible(show)
        self._body_widget.setVisible(not show)
        self._actions_widget.setVisible(not show)

    @property
    def empty_state(self) -> Optional[QWidget]:
        """The widget :meth:`set_empty_state` gave the page, if any."""
        return self._empty_state

    def is_showing_empty_state(self) -> bool:
        """Whether the empty state is in place of the body.

        (Even while the page itself is hidden.)
        """
        return self._empty_state is not None and not self._body_widget.isVisibleTo(self)

    # ------------------------------------------------------------------
    # Header actions and footer

    def add_action(self, widget: QWidget) -> None:
        """Add a button (or other widget) to the right of the title."""
        self.actions.addWidget(widget)

    def add_footer_widget(self, widget: QWidget) -> None:
        self.footer.addWidget(widget)
        self._footer_widget.setVisible(True)
        self._apply_metrics()

    def set_next(self, text: str, on_click: Callable[[], None]) -> QPushButton:
        """Add a "Next: <step> →" link button to the footer."""
        button = make_button(
            escape_ampersands(f"Next: {text}"), variant="plain", icon_name=IconName.NEXT
        )
        # Right-to-left puts the arrow after the text.
        button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.clicked.connect(on_click)
        self.add_footer_widget(button)
        return button


__all__ = ["Page", "PageKind"]
