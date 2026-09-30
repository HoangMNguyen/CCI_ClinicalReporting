"""Keeping the window usable-looking while work runs in the background.

:class:`BusyOverlay` covers a widget (usually the whole window) the moment
work starts, so no click, key, or shortcut can change what the work is
using. It only dims the window and shows a spinner after a short delay, so
quick tasks don't flash.
"""

from __future__ import annotations

from typing import Optional

import shiboken6
from PySide6.QtCore import (
    QEvent,
    QObject,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from cci_ui.theme.manager import current
from cci_ui.theme.palette import qcolor
from cci_ui.theme.qss import register_qss

#: Show the dimming and spinner only if the work takes longer than this.
REVEAL_DELAY_MS = 150

register_qss(
    """
QFrame[cciRole="busyCard"] {
    background: ${bg_surface};
    border: 1px solid ${border_card};
    border-radius: 14px;
}
"""
)


class Spinner(QWidget):
    """A small rotating arc in the accent color."""

    def __init__(self, size: int = 20, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._rotation = QVariantAnimation(self)
        self._rotation.setStartValue(0)
        self._rotation.setEndValue(360)
        self._rotation.setDuration(900)
        self._rotation.setLoopCount(-1)
        self._rotation.valueChanged.connect(self._set_angle)

    def _set_angle(self, angle) -> None:
        self._angle = int(angle)
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._rotation.start()

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().hideEvent(event)
        self._rotation.stop()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(qcolor(current().colors.accent), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        arc = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        # Qt angles are in 1/16 degree, counter-clockwise; draw a 270° arc.
        painter.drawArc(arc, -self._angle * 16, 270 * 16)
        painter.end()


class BusyOverlay(QWidget):
    """Blocks *target* while work runs; dims it and shows a message after a moment."""

    #: Emitted with True when work starts and False when it ends.
    busyChanged = Signal(bool)

    def __init__(self, target: QWidget):
        super().__init__(target)
        self._busy = False
        self._revealed = False
        self._previous_focus: Optional[QWidget] = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Working")

        self._card = QFrame()
        self._card.setProperty("cciRole", "busyCard")
        self._spinner = Spinner()
        self._message = QLabel()
        self._message.setTextFormat(Qt.TextFormat.PlainText)
        card_layout = QHBoxLayout(self._card)
        card_layout.setContentsMargins(22, 16, 22, 16)
        card_layout.setSpacing(12)
        card_layout.addWidget(self._spinner)
        card_layout.addWidget(self._message)
        layout = QVBoxLayout(self)
        layout.addWidget(self._card, 0, Qt.AlignmentFlag.AlignCenter)
        self._card.setVisible(False)

        self._reveal_timer = QTimer(self)
        self._reveal_timer.setSingleShot(True)
        self._reveal_timer.setInterval(REVEAL_DELAY_MS)
        self._reveal_timer.timeout.connect(self._reveal)
        target.installEventFilter(self)
        self.setVisible(False)

    @property
    def busy(self) -> bool:
        return self._busy

    def message(self) -> str:
        return self._message.text()

    def start(self, message: str = "Working…") -> None:
        """Block input now; dim and show *message* if still busy after a moment."""
        self.set_message(message)
        if self._busy:
            return
        self._busy = True
        self._previous_focus = self.window().focusWidget()
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        # Messages stay readable: keep toast hosts above the dimming.
        for sibling in self.parentWidget().children():
            if (
                isinstance(sibling, QWidget)
                and sibling.property("cciRole") == "toastHost"
            ):
                sibling.raise_()
        self.setCursor(Qt.CursorShape.WaitCursor)
        self.setVisible(True)
        self.setFocus()
        self._reveal_timer.start()
        self.busyChanged.emit(True)

    def set_message(self, message: str) -> None:
        self._message.setText(message)

    def stop(self) -> None:
        """Unblock and give keyboard focus back to where it was."""
        if not self._busy:
            return
        self._busy = False
        self._reveal_timer.stop()
        self._revealed = False
        self._card.setVisible(False)
        self.setVisible(False)
        self.unsetCursor()
        previous, self._previous_focus = self._previous_focus, None
        try:
            # The widget may have been deleted or hidden while busy.
            if previous is not None and shiboken6.isValid(previous):
                if previous.isVisible():
                    previous.setFocus()
        finally:
            self.busyChanged.emit(False)

    def is_revealed(self) -> bool:
        return self._revealed

    def _reveal(self) -> None:
        self._revealed = True
        self._card.setVisible(True)
        self.update()

    # ------------------------------------------------------------------
    # Covering the target and swallowing input

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return False

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self._revealed:
            painter = QPainter(self)
            painter.fillRect(self.rect(), qcolor(current().colors.scrim))
            painter.end()

    def event(self, event: QEvent) -> bool:
        # Claim every key before shortcuts see it, so window shortcuts
        # (Ctrl+S, the sidebar toggle, mnemonics) can't start anything while busy.
        if event.type() == QEvent.Type.ShortcutOverride:
            event.accept()
            return True
        return super().event(event)

    def _swallow(self, event) -> None:
        event.accept()

    mousePressEvent = mouseReleaseEvent = mouseDoubleClickEvent = _swallow  # noqa: N815
    wheelEvent = keyPressEvent = keyReleaseEvent = _swallow  # noqa: N815

    def focusNextPrevChild(self, next: bool) -> bool:  # noqa: A002, N802
        return False  # Tab can't leave the overlay while busy.


__all__ = ["REVEAL_DELAY_MS", "BusyOverlay", "Spinner"]
