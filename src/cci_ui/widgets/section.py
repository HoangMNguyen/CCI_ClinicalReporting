"""Grouped form sections: a small title, rows on a card, and a footnote.

This is the inset-grouped layout of macOS System Settings::

    Cut-off date                          <- title
    ┌──────────────────────────────────┐
    │ Apply cut-off date        ( ━━● ) │  <- rows, separated by inset lines
    │──────────────────────────────────│
    │ Cut-off               [2026-06-30]│
    └──────────────────────────────────┘
    Only rows on or before this date…     <- footnote
"""

from __future__ import annotations

from typing import Optional, Sequence, Union

from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from cci_ui.theme.manager import current, theme_events
from cci_ui.theme.palette import qcolor
from cci_ui.widgets.labels import text_label

#: Width of the label column in a row; ``None`` lets the label take the space.
LABEL_WIDTH = 132
#: Horizontal padding inside the card; separators start at this inset.
ROW_INSET = 14


class FormRow(QWidget):
    """One row of a :class:`Section`: a label on the left, fields on the right."""

    def __init__(
        self,
        label: Union[str, QWidget, None],
        fields: Sequence[QWidget],
        *,
        label_width: Optional[int] = LABEL_WIDTH,
        end_aligned: bool = False,
        separator: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._separator = separator
        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(10)

        self.label: Optional[QWidget] = None
        if isinstance(label, str):
            self.label = QLabel(label)
        elif label is not None:
            self.label = label
        if self.label is not None:
            if label_width is None:
                self._layout.addWidget(self.label, 1)
            else:
                self.label.setFixedWidth(label_width)
                self._layout.addWidget(self.label)
            if isinstance(self.label, QLabel) and fields:
                self.label.setBuddy(fields[0])

        # Fields stretch to fill the row, unless they sit at its end at their
        # own width (compact controls such as a date or a switch). A growing
        # label already pushes them to the end.
        label_grows = self.label is not None and label_width is None
        stretch_fields = not end_aligned and not label_grows
        if end_aligned and not label_grows:
            self._layout.addStretch(1)
        for field in fields:
            self._layout.addWidget(field, 1 if stretch_fields else 0)
        if stretch_fields and not fields:
            self._layout.addStretch(1)

        theme_events().changed.connect(self._apply_metrics)
        self._apply_metrics()

    def _apply_metrics(self) -> None:
        metrics = current().metrics
        pad = metrics.form_row_pad
        self._layout.setContentsMargins(ROW_INSET, pad, ROW_INSET, pad)
        self.setMinimumHeight(metrics.control_h + 2 * pad)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().paintEvent(event)
        if not self._separator:
            return
        painter = QPainter(self)
        painter.setPen(QPen(qcolor(current().colors.separator), 1))
        painter.drawLine(QPoint(ROW_INSET, 0), QPoint(self.width(), 0))


class Section(QWidget):
    """A titled card of :class:`FormRow` rows, with an optional footnote."""

    def __init__(
        self, title: str = "", footnote: str = "", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.title_label = text_label(title, style="subheadline")
        self.title_label.setContentsMargins(4, 0, 0, 0)
        self.title_label.setVisible(bool(title))
        layout.addWidget(self.title_label)

        self.card = QFrame()
        self.card.setProperty("cciRole", "card")
        self._rows = QVBoxLayout(self.card)
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(0)
        layout.addWidget(self.card)

        self.footnote_label = text_label(footnote, style="footnote", wrap=True)
        self.footnote_label.setContentsMargins(4, 0, 4, 0)
        self.footnote_label.setVisible(bool(footnote))
        layout.addWidget(self.footnote_label)

    def add_row(
        self,
        label: Union[str, QWidget, None],
        *fields: QWidget,
        label_width: Optional[int] = LABEL_WIDTH,
        end_aligned: bool = False,
    ) -> FormRow:
        """Add a row of a label and fields.

        Fields stretch across the row by default. Pass ``end_aligned=True`` to
        keep compact fields (a date, a short combo) at their own width at the
        row's end, or ``label_width=None`` for rows like "label ··· switch"
        where the label takes the space.
        """
        row = FormRow(
            label,
            fields,
            label_width=label_width,
            end_aligned=end_aligned,
            separator=self._rows.count() > 0,
        )
        self._rows.addWidget(row)
        return row

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        """Add content that spans the whole card, such as a table."""
        self._rows.addWidget(widget, stretch)

    def set_footnote(self, text: str) -> None:
        self.footnote_label.setText(text)
        self.footnote_label.setVisible(bool(text))


__all__ = ["LABEL_WIDTH", "ROW_INSET", "FormRow", "Section"]
