"""A side panel of titled sections, beside a main area or below it.

:class:`SidePanel` is the card a :class:`~cci_ui.widgets.responsive.ResponsiveSplit`
puts next to its main area (a data grid, say). Beside the main area its
sections sit one above the other; below it, on narrow windows, they sit side
by side and share the width. A separator between sections turns with them.
Call :meth:`SidePanel.follow` with the split to keep it in step.

:func:`labeled_field` and :func:`full_width` build the fields in a section.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cci_ui.theme.manager import current, repolish, theme_events
from cci_ui.widgets.labels import section_label, text_label
from cci_ui.widgets.responsive import ResponsiveSplit


def labeled_field(label: str, widget: QWidget) -> QVBoxLayout:
    """A small label above *widget*, as the fields in a panel are laid out."""
    layout = QVBoxLayout()
    layout.setSpacing(4)
    layout.addWidget(text_label(label, style="callout", tone="secondary"))
    layout.addWidget(widget)
    return layout


def full_width(button: QWidget) -> QWidget:
    """*button*, set to fill the panel's width (its main actions)."""
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return button


class SidePanel(QFrame):
    """A card of titled sections that scrolls when it is too short."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setProperty("cciRole", "card")
        self._stacked = False
        self._section_widgets: List[QWidget] = []
        self._separators: List[QFrame] = []

        self._sections = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self._sections.setContentsMargins(0, 0, 0, 0)
        self._sections.setSpacing(0)
        self._sections.addStretch(1)  # Beside the main area: spare height last.
        content = QWidget()
        content.setProperty("cciRole", "pageContent")
        content.setLayout(self._sections)
        scroll = QScrollArea()
        scroll.setProperty("cciRole", "page")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(scroll)

        theme_events().changed.connect(self._apply_metrics)

    def add_section(self, title: str) -> QVBoxLayout:
        """Add a section titled *title*; fill the layout it returns."""
        if self._section_widgets:
            separator = QFrame()
            self._separators.append(separator)
            self._insert(separator)
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.addWidget(section_label(title))
        self._section_widgets.append(section)
        self._apply_metrics()
        # At the top of its share when the sections sit side by side.
        self._insert(section, Qt.AlignmentFlag.AlignTop)
        self._arrange()
        return layout

    def _apply_metrics(self) -> None:
        """Space inside and between the parts of each section, by density."""
        metrics = current().metrics
        padding = metrics.panel_pad
        for section in self._section_widgets:
            layout = section.layout()
            layout.setContentsMargins(padding, padding, padding, padding)
            layout.setSpacing(metrics.panel_gap)

    def _insert(
        self, widget: QWidget, alignment: Optional[Qt.AlignmentFlag] = None
    ) -> None:
        index = self._sections.count() - 1  # Before the trailing stretch.
        if alignment is None:
            self._sections.insertWidget(index, widget)
        else:
            self._sections.insertWidget(index, widget, 0, alignment)

    def follow(self, split: ResponsiveSplit) -> None:
        """Arrange the sections for where *split* puts the panel, now and later."""
        split.stackedChanged.connect(self.set_stacked)
        self.set_stacked(split.is_stacked())

    def is_stacked(self) -> bool:
        """Whether the panel is below the main area (sections side by side)."""
        return self._stacked

    def set_stacked(self, stacked: bool) -> None:
        """Arrange the sections for where the panel is.

        *stacked*: the panel is below the main area, so its sections sit side
        by side; otherwise it is beside it, and they sit one above another.
        """
        self._stacked = bool(stacked)
        self._arrange()

    def _arrange(self) -> None:
        stacked = self._stacked
        self._sections.setDirection(
            QBoxLayout.Direction.LeftToRight
            if stacked
            else QBoxLayout.Direction.TopToBottom
        )
        # Side by side the sections share the width; one above another they
        # keep their own height and the trailing stretch takes the rest.
        share = 1 if stacked else 0
        for section in self._section_widgets:
            self._sections.setStretchFactor(section, share)
        self._sections.setStretch(self._sections.count() - 1, 1 - share)
        for separator in self._separators:
            separator.setProperty(
                "cciRole", "separatorVertical" if stacked else "separator"
            )
            repolish(separator)


__all__ = ["SidePanel", "full_width", "labeled_field"]
