"""A segmented control: a row of mutually exclusive options in one track."""

from __future__ import annotations

from typing import List, NamedTuple, Optional, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from cci_ui.icons import icon
from cci_ui.theme.qss import register_qss

register_qss(
    """
QFrame[cciRole="segmented"] {
    background: ${fill};
    border: none;
    border-radius: ${radius_pill}px;
}
QToolButton[cciRole="segment"] {
    background: transparent;
    border: none;
    border-radius: ${radius_control}px;
    padding: 0 10px;
    min-height: ${segment_h}px;
    max-height: ${segment_h}px;
    font-size: 12px;
    font-weight: 500;
}
QToolButton[cciRole="segment"]:hover {
    background: ${bg_hover};
}
QToolButton[cciRole="segment"]:checked {
    background: ${seg_selected};
}
QToolButton[cciRole="segment"]:focus {
    border: 1px solid ${accent};
}
"""
)


class Segment(NamedTuple):
    key: str
    text: str
    icon_name: Optional[str] = None
    tooltip: str = ""


class SegmentedControl(QFrame):
    """Pick one of a few options.

    The buttons share a :class:`QButtonGroup`, so Qt's own keyboard handling
    applies: Tab reaches the chosen option and the arrow keys pick another.
    """

    #: Emitted with the new option's key when the user picks it.
    currentChanged = Signal(str)

    def __init__(
        self,
        segments: Sequence[Segment],
        current: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        if not segments:
            raise ValueError("A segmented control needs at least one segment")
        self.setProperty("cciRole", "segmented")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._keys: List[str] = [segment.key for segment in segments]
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        for index, segment in enumerate(segments):
            button = QToolButton()
            button.setProperty("cciRole", "segment")
            button.setCheckable(True)
            button.setText(segment.text)
            button.setToolTip(segment.tooltip)
            button.setAccessibleName(segment.text or segment.tooltip)
            if segment.icon_name:
                button.setIcon(icon(segment.icon_name, "primary"))
                style = (
                    Qt.ToolButtonStyle.ToolButtonTextBesideIcon
                    if segment.text
                    else Qt.ToolButtonStyle.ToolButtonIconOnly
                )
                button.setToolButtonStyle(style)
            self._group.addButton(button, index)
            layout.addWidget(button)
        self._group.idClicked.connect(self._on_clicked)
        self.set_current(current if current is not None else self._keys[0])

    def current(self) -> str:
        return self._keys[self._group.checkedId()]

    def set_current(self, key: str) -> None:
        """Select *key* without emitting :attr:`currentChanged`."""
        self._group.button(self._keys.index(key)).setChecked(True)

    def _on_clicked(self, index: int) -> None:
        self.currentChanged.emit(self._keys[index])


__all__ = ["Segment", "SegmentedControl"]
