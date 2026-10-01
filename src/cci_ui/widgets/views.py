"""Lists and tables that say what belongs in them while empty, and empty pages.

The placeholder views are the standard Qt classes (``QListWidget``,
``QTableWidget``, ``QTableView``) plus a placeholder (and, for results,
:meth:`PreviewTableView.fit_columns`), so existing code that fills them keeps
working. :class:`EmptyState` fills a whole page, for example "No data
loaded" before a file is chosen.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidget,
    QTableView,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from cci_ui.theme.manager import current
from cci_ui.theme.palette import qcolor
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.labels import IconLabel, text_label

#: Widest a result column grows to fit its contents; longer values are
#: shortened (as the mockup's preview grid does).
COLUMN_MAX_W = 320
#: Rows looked at when sizing result columns: enough for a fair width,
#: without reading every row of a large result (it runs on the GUI thread).
SIZE_SAMPLE_ROWS = 100
_MESSAGE_MAX_W = 360


def _paint_placeholder(view: QAbstractItemView, text: str) -> None:
    if not text:
        return
    painter = QPainter(view.viewport())
    painter.setPen(qcolor(current().colors.text_tertiary))
    area = view.viewport().rect().adjusted(16, 16, -16, -16)
    painter.drawText(
        area, int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap), text
    )
    painter.end()


class _PlaceholderMixin:
    """Adds ``placeholderText`` to an item view (like :class:`QLineEdit` has)."""

    _placeholder = ""

    def placeholderText(self) -> str:  # noqa: N802 (Qt naming)
        return self._placeholder

    def setPlaceholderText(self, text: str) -> None:  # noqa: N802 (Qt naming)
        self._placeholder = text
        self.viewport().update()

    def _is_empty(self) -> bool:
        raise NotImplementedError

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().paintEvent(event)
        if self._is_empty():
            _paint_placeholder(self, self._placeholder)


class PlaceholderListWidget(_PlaceholderMixin, QListWidget):
    """A :class:`QListWidget` that shows its placeholder while it has no items."""

    def __init__(self, placeholder: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._placeholder = placeholder

    def _is_empty(self) -> bool:
        return self.count() == 0


class PlaceholderTableWidget(_PlaceholderMixin, QTableWidget):
    """A :class:`QTableWidget` that shows its placeholder while it has no rows."""

    def __init__(self, placeholder: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._placeholder = placeholder

    def _is_empty(self) -> bool:
        return self.rowCount() == 0


class PreviewTableView(_PlaceholderMixin, QTableView):
    """A :class:`QTableView` for results; shows its placeholder with no rows."""

    #: Emitted after :meth:`setModel`, e.g. to update a "1,284 rows" caption.
    modelChanged = Signal()

    def __init__(self, placeholder: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._placeholder = placeholder
        self.horizontalHeader().setResizeContentsPrecision(SIZE_SAMPLE_ROWS)

    def fit_columns(self, max_width: int = COLUMN_MAX_W) -> None:
        """Size columns to their contents (sampled rows), at most *max_width*.

        Longer values are shortened on screen; give the model a tooltip so
        hovering shows them whole.
        """
        self.resizeColumnsToContents()
        header = self.horizontalHeader()
        for column in range(header.count()):
            if header.sectionSize(column) > max_width:
                header.resizeSection(column, max_width)

    def setModel(self, model) -> None:  # noqa: N802 (Qt override)
        super().setModel(model)
        self.modelChanged.emit()
        self.viewport().update()

    def _is_empty(self) -> bool:
        model = self.model()
        return model is None or model.rowCount() == 0


class EmptyState(QWidget):
    """A centred icon, title, message, and optional button filling a page."""

    def __init__(
        self,
        icon_name: str,
        title: str,
        message: str = "",
        *,
        action_text: str = "",
        on_action: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addStretch(1)
        self.icon = IconLabel(icon_name, "tertiary", 40)
        layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignHCenter)
        self.title_label = text_label(title, style="title3")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.title_label)
        self.message_label = text_label(message, tone="secondary", wrap=True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.message_label.setMaximumWidth(_MESSAGE_MAX_W)
        # Centred by stretches, not an alignment flag: a layout sizes an
        # aligned label to its preferred width and one line of height, which
        # cut a wrapped message short.
        message_row = QHBoxLayout()
        message_row.addStretch(1)
        message_row.addWidget(self.message_label, 100)
        message_row.addStretch(1)
        layout.addLayout(message_row)
        # Only after parenting (see cci_ui.widgets).
        self.message_label.setVisible(bool(message))
        self.action_button = None
        if action_text:
            self.action_button = make_button(action_text, variant="primary")
            if on_action is not None:
                self.action_button.clicked.connect(on_action)
            layout.addSpacing(8)
            layout.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)


__all__ = [
    "COLUMN_MAX_W",
    "SIZE_SAMPLE_ROWS",
    "EmptyState",
    "PlaceholderListWidget",
    "PlaceholderTableWidget",
    "PreviewTableView",
]
