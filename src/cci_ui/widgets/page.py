"""A page: large title, subtitle, actions, body, and a footer.

Three kinds of page decide how extra window space is used:

- ``form``: a single centred column at most ``LAYOUT.form_max_w`` wide that
  scrolls when the window is short (settings-style pages, the small tools).
- ``workspace``: the body fills the whole width and height; lists and tables
  in it take the extra space and scroll inside themselves.
- ``split``: like workspace, for a main area plus a side panel
  (see :class:`~cci_ui.widgets.responsive.ResponsiveSplit`).
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt
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
from cci_ui.widgets.labels import text_label

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
        self.subtitle_label.setVisible(bool(subtitle))
        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)

        self._header = QWidget()
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        header_layout.addLayout(titles, 1)
        header_layout.addLayout(self.actions)

        #: Put the page's content here.
        self.body = QVBoxLayout()
        self.body.setSpacing(12)

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
        self._column_layout.addLayout(self.body)
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
        self._body_margins.addLayout(self.body, 1)
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
            self._body_margins.setContentsMargins(margin, 0, margin, 0)
            self.footer.setContentsMargins(margin, 10, margin, 12)

    # ------------------------------------------------------------------
    # Header actions and footer

    def add_action(self, widget: QWidget) -> None:
        """Add a button (or other widget) to the right of the title."""
        self.actions.addWidget(widget)

    def add_footer_widget(self, widget: QWidget) -> None:
        self.footer.addWidget(widget)
        self._footer_widget.setVisible(True)

    def set_next(self, text: str, on_click: Callable[[], None]) -> QPushButton:
        """Add a "Next: <step> →" link button to the footer."""
        button = make_button(f"Next: {text}", variant="plain", icon_name=IconName.NEXT)
        # Right-to-left puts the arrow after the text.
        button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.clicked.connect(on_click)
        self.add_footer_widget(button)
        return button


__all__ = ["Page", "PageKind"]
