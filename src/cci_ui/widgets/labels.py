"""Text labels in the type scale, and a label that shortens long paths."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from cci_ui.theme.manager import repolish
from cci_ui.theme.tokens import TYPE_SCALE


def text_label(
    text: str = "",
    *,
    style: str = "body",
    tone: Optional[str] = None,
    wrap: bool = False,
    selectable: bool = False,
    parent: Optional[QWidget] = None,
) -> QLabel:
    """A label in a :data:`~cci_ui.theme.tokens.TYPE_SCALE` style.

    *tone* (``"secondary"`` or ``"tertiary"``) recolors any style.
    """
    if style not in TYPE_SCALE:
        raise ValueError(
            f"Unknown text style {style!r}; expected one of {list(TYPE_SCALE)}"
        )
    label = QLabel(text, parent)
    label.setProperty("textStyle", style)
    if tone:
        label.setProperty("tone", tone)
    label.setWordWrap(wrap)
    if selectable:
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class ElidedLabel(QLabel):
    """Shows text that doesn't fit shortened in the middle, e.g. ``C:\\Users\\…\\data.zip``.

    :meth:`text` returns the full text and the tooltip shows it whenever it is
    shortened, so code that reads the label back is unaffected. Text is shown
    in *tone* (``None`` for the normal color); when empty, the placeholder is
    shown in the tertiary color.
    """

    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        *,
        placeholder: str = "",
        tone: Optional[str] = None,
        mode: Qt.TextElideMode = Qt.TextElideMode.ElideMiddle,
    ) -> None:
        super().__init__(parent)
        self._full_text = ""
        self._placeholder = placeholder
        self._tone = tone
        self._mode = mode
        # Paths can contain characters that look like markup.
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def text(self) -> str:  # Full text, not the shortened one on screen.
        return self._full_text

    def setText(self, text: Optional[str]) -> None:  # noqa: N802 (Qt API)
        self._full_text = text or ""
        tone = self._tone if self._full_text else "tertiary"
        if self.property("tone") != tone:
            self.setProperty("tone", tone)
            repolish(self)
        self._refresh()

    def placeholderText(self) -> str:  # noqa: N802 (Qt naming)
        return self._placeholder

    def setPlaceholderText(self, text: str) -> None:  # noqa: N802 (Qt naming)
        self._placeholder = text
        self._refresh()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        return QSize(0, super().minimumSizeHint().height())

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        shown = self._full_text or self._placeholder
        margins = self.contentsMargins()
        width = (
            self.fontMetrics().horizontalAdvance(shown)
            + margins.left()
            + margins.right()
        )
        return QSize(width, super().sizeHint().height())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._refresh()

    def changeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._refresh()

    def _refresh(self) -> None:
        shown = self._full_text or self._placeholder
        width = self.contentsRect().width()
        elided = (
            self.fontMetrics().elidedText(shown, self._mode, width)
            if width > 0
            else shown
        )
        super().setText(elided)
        self.setToolTip(self._full_text if elided != self._full_text else "")
        # Screen readers get the whole text, not the shortened one.
        self.setAccessibleName(self._full_text or self._placeholder)
        self.updateGeometry()


__all__ = ["ElidedLabel", "text_label"]
