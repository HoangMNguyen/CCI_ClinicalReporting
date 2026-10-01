"""An on/off switch in the macOS style.

:class:`ToggleSwitch` is a :class:`QCheckBox` underneath, so code written for
checkboxes (``isChecked``, ``setChecked``, ``toggled``, ``stateChanged``)
works unchanged; only the drawing differs.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QSizePolicy, QWidget

from cci_ui.theme.manager import current, theme_events
from cci_ui.theme.palette import qcolor
from cci_ui.theme.tokens import Density

_TRACK = {Density.COMFORTABLE: QSize(38, 22), Density.COMPACT: QSize(32, 18)}
_KNOB_INSET = 2
_TEXT_GAP = 8
_ANIMATION_MS = 120


def _mix(start: QColor, end: QColor, amount: float) -> QColor:
    """The color *amount* (0..1) of the way from *start* to *end*."""
    return QColor.fromRgbF(
        start.redF() + (end.redF() - start.redF()) * amount,
        start.greenF() + (end.greenF() - start.greenF()) * amount,
        start.blueF() + (end.blueF() - start.blueF()) * amount,
        start.alphaF() + (end.alphaF() - start.alphaF()) * amount,
    )


class ToggleSwitch(QCheckBox):
    """A switch; the optional text is drawn to the right of it."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._position = 0.0  # 0 = off, 1 = on; animated in between.
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(_ANIMATION_MS)
        self._animation.valueChanged.connect(self._set_position)
        self.toggled.connect(self._animate_to)
        # Always its own size: in a stretching layout a wider switch would make
        # clicks on empty space flip it.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        theme_events().changed.connect(self._on_theme_changed)

    def _track_size(self) -> QSize:
        return _TRACK[current().density]

    def _label_text(self) -> str:
        """The text as shown: ``&`` mnemonics removed, ``&&`` kept as ``&``."""
        return self.text().replace("&&", "\0").replace("&", "").replace("\0", "&")

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        track = self._track_size()
        width = track.width()
        height = track.height()
        if self.text():
            metrics = self.fontMetrics()
            width += _TEXT_GAP + metrics.horizontalAdvance(self._label_text())
            height = max(height, metrics.height())
        return QSize(width + 4, height + 4)  # room for the focus ring

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        return self.sizeHint()

    def hitButton(self, pos) -> bool:  # noqa: N802 (Qt override)
        # The switch and its text, even if a layout made the widget wider.
        return QRect(QPoint(0, 0), self.sizeHint()).contains(pos)

    def _animate_to(self, checked: bool) -> None:
        target = 1.0 if checked else 0.0
        if not self.isVisible():
            self._set_position(target)
            return
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(target)
        self._animation.start()

    def _set_position(self, value) -> None:
        self._position = float(value)
        self.update()

    def _on_theme_changed(self) -> None:
        self.updateGeometry()
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._set_position(1.0 if self.isChecked() else 0.0)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        colors = current().colors
        track_size = self._track_size()
        track = QRectF(
            2,
            (self.height() - track_size.height()) / 2,
            track_size.width(),
            track_size.height(),
        )
        radius = track.height() / 2

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.45)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(
            _mix(qcolor(colors.switch_off), qcolor(colors.accent), self._position)
        )
        painter.drawRoundedRect(track, radius, radius)

        knob_size = track.height() - 2 * _KNOB_INSET
        travel = track.width() - knob_size - 2 * _KNOB_INSET
        knob_x = track.left() + _KNOB_INSET + travel * self._position
        knob = QRectF(knob_x, track.top() + _KNOB_INSET, knob_size, knob_size)
        painter.setBrush(qcolor(colors.knob_shadow))
        painter.drawEllipse(knob.translated(QPointF(0, 1)))
        painter.setBrush(qcolor(colors.switch_knob))
        painter.drawEllipse(knob)

        if self.hasFocus() and self.focusPolicy() != Qt.FocusPolicy.NoFocus:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(qcolor(colors.focus_ring), 2))
            painter.drawRoundedRect(
                track.adjusted(-1, -1, 1, 1), radius + 1, radius + 1
            )

        if self.text():
            # Full opacity: the palette already gives disabled text its color.
            painter.setOpacity(1.0)
            text_left = int(track.right()) + _TEXT_GAP
            text_rect = QRect(text_left, 0, self.width() - text_left, self.height())
            painter.setPen(self.palette().color(self.foregroundRole()))
            flags = Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextShowMnemonic
            painter.drawText(text_rect, int(flags), self.text())


__all__ = ["ToggleSwitch"]
