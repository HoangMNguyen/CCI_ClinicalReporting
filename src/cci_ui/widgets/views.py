"""Lists and tables that say what belongs in them while empty, and empty pages.

The placeholder views are the standard Qt classes (``QListWidget``,
``QTableWidget``, ``QTableView``) with one addition, so existing code that
fills them keeps working. :class:`EmptyState` fills a whole page, for
example "No data loaded" before a file is chosen.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
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
        self.message_label.setMaximumWidth(360)
        self.message_label.setVisible(bool(message))
        layout.addWidget(self.message_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.action_button = None
        if action_text:
            self.action_button = make_button(action_text, variant="primary")
            if on_action is not None:
                self.action_button.clicked.connect(on_action)
            layout.addSpacing(8)
            layout.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)


__all__ = [
    "EmptyState",
    "PlaceholderListWidget",
    "PlaceholderTableWidget",
    "PreviewTableView",
]
