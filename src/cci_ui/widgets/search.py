"""A search box with a leading magnifying glass and a clear button."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLineEdit, QWidget

from cci_ui.icons import IconName, icon
from cci_ui.theme.qss import register_qss

_ICON = 14
_ICON_LEFT = 8

register_qss(
    """
QLineEdit[cciRole="search"] {
    padding-left: 28px;
}
"""
)


class SearchField(QLineEdit):
    """A :class:`QLineEdit` for filtering; existing ``textChanged`` code works as is.

    The icon is painted rather than added as a line-edit action, so it stays
    centred whatever height the density gives the field.
    """

    def __init__(self, placeholder: str = "Search", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("cciRole", "search")
        self.setPlaceholderText(placeholder)
        self.setAccessibleName(placeholder)
        self.setClearButtonEnabled(True)
        self._icon = icon(IconName.SEARCH, "tertiary")

    def activate(self) -> None:
        """Focus the field with its text selected, ready to type over."""
        self.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.selectAll()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().paintEvent(event)
        painter = QPainter(self)
        area = QRect(_ICON_LEFT, (self.height() - _ICON) // 2, _ICON, _ICON)
        self._icon.paint(painter, area)
        painter.end()


__all__ = ["SearchField"]
