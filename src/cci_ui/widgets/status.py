"""Telling the user how things went: banners, toasts, and error dialogs.

- :class:`StatusBanner` sits on a page, next to what it's about. It accepts
  the same ``setText``/``text`` calls as the labels it replaces, and reads the
  kind (info, success, warning, error) and details from a
  :class:`clinical_reporting.feedback.Message`-style string.
- :func:`show_toast` briefly shows a message at the bottom of the window, for
  results raised while the user is on another page.
- :func:`show_error` is a modal dialog for errors that stop the user.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.theme.fonts import mono_font
from cci_ui.theme.manager import current, repolish
from cci_ui.theme.palette import qcolor
from cci_ui.theme.qss import register_qss
from cci_ui.widgets.buttons import icon_button, make_button
from cci_ui.widgets.labels import ElidedLabel, IconLabel, WrappingLabel

KINDS = ("info", "success", "warning", "error")
#: Kind -> (icon, icon role).
KIND_ICONS = {
    "info": (IconName.INFO, "info"),
    "success": (IconName.SUCCESS, "success"),
    "warning": (IconName.WARNING, "warning"),
    "error": (IconName.ERROR, "danger"),
}

register_qss(
    """
QFrame[cciRole="banner"] {
    border: none;
    border-radius: ${radius_card}px;
    background: ${info_bg};
}
QFrame[cciRole="banner"][kind="success"] {
    background: ${success_bg};
}
QFrame[cciRole="banner"][kind="warning"] {
    background: ${warning_bg};
}
QFrame[cciRole="banner"][kind="error"] {
    background: ${danger_bg};
}
QPlainTextEdit[cciRole="details"] {
    background: ${bg_surface};
    border: 1px solid ${border_card};
    border-radius: ${radius_control}px;
}
QFrame[cciRole="toast"] {
    background: ${bg_surface};
    border: 1px solid ${border_card};
    border-radius: 17px;
}
"""
)


def check_kind(kind: str) -> None:
    """Raise ValueError unless *kind* is one of :data:`KINDS`."""
    if kind not in KINDS:
        raise ValueError(f"Unknown message kind {kind!r}; expected one of {KINDS}")


def _kind_of(text) -> str:
    kind = getattr(text, "kind", "info")
    return kind if kind in KINDS else "info"


class StatusBanner(QFrame):
    """An inline message tinted by kind, with optional details and action.

    Empty text hides it. ``setText(feedback.error("…", details=tb))`` shows an
    error with a "Show details" toggle that reveals the traceback and a Copy
    button; plain strings show as info.
    """

    #: Emitted when the user closes the banner with its ✕ button.
    dismissed = Signal()
    #: Emitted whenever a message is shown or cleared, even the same one again.
    messageChanged = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        dismissible: bool = True,
        announce: bool = True,
    ):
        super().__init__(parent)
        self._announce = announce
        self.setProperty("cciRole", "banner")
        self._text = ""
        self._kind = "info"
        self._details = ""
        self._showing = False
        self._action_callback: Optional[Callable[[], None]] = None

        self._icon = IconLabel(IconName.INFO, "info")
        # Wraps a long path too, so the banner never widens what holds it.
        self._label = WrappingLabel()
        self._label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._details_button = make_button("Show details", variant="plain")
        self._details_button.clicked.connect(self._toggle_details)
        self._details_view = QPlainTextEdit()
        self._details_view.setProperty("cciRole", "details")
        self._details_view.setReadOnly(True)
        self._details_view.setFont(mono_font())
        self._details_view.setMaximumHeight(160)
        self._copy_button = make_button("Copy details")
        self._copy_button.clicked.connect(self._copy_details)
        self._copy_reset = QTimer(self)
        self._copy_reset.setSingleShot(True)
        self._copy_reset.setInterval(1500)
        self._copy_reset.timeout.connect(
            lambda: self._copy_button.setText("Copy details")
        )
        self._details_box = QWidget()
        details_layout = QVBoxLayout(self._details_box)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.addWidget(self._details_view)
        details_layout.addWidget(self._copy_button, 0, Qt.AlignmentFlag.AlignLeft)
        self._details_box.setVisible(False)

        self.action_button = make_button("", variant="plain")
        self.action_button.setVisible(False)
        self.action_button.clicked.connect(self._run_action)
        self.dismiss_button = icon_button(IconName.CLOSE, "Dismiss")
        self.dismiss_button.clicked.connect(self._dismiss)

        text_column = QVBoxLayout()
        text_column.setSpacing(2)
        text_column.addWidget(self._label)
        text_column.addWidget(self._details_button, 0, Qt.AlignmentFlag.AlignLeft)
        text_column.addWidget(self._details_box)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(10)
        layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_column, 1)
        layout.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.dismiss_button, 0, Qt.AlignmentFlag.AlignTop)
        # Only after parenting (see cci_ui.widgets).
        self.dismiss_button.setVisible(dismissible)
        self.setVisible(False)

    @property
    def announce(self) -> bool:
        """Whether the window repeats this banner's messages elsewhere.

        Yes (the status bar, toasts) for results of what the user did; no for
        a summary of the page's current state that is set again often. The
        window reads it once, when it starts following its banners.
        """
        return self._announce

    def is_showing(self) -> bool:
        """Whether a message is set (true even before the banner has a parent)."""
        return self._showing

    def _set_showing(self, showing: bool) -> None:
        self._showing = showing
        # Without a parent, showing would open the banner as its own window;
        # it appears once it is placed in a layout (see event()).
        if self.parentWidget() is not None:
            self.setVisible(showing)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ParentChange and self.parentWidget() is not None:
            self.setVisible(self._showing)
        return super().event(event)

    # ------------------------------------------------------------------
    # QLabel-compatible API

    def text(self) -> str:
        """The message shown (a ``Message`` keeps its kind), or "" when hidden."""
        return self._text

    def setText(self, text: Optional[str]) -> None:  # noqa: N802 (QLabel API)
        if not text:
            self.clear()
            return
        self.show_message(text, _kind_of(text), getattr(text, "details", None))

    def clear(self) -> None:
        self._text = ""
        self._details = ""
        self._label.clear()
        self._set_showing(False)
        self.messageChanged.emit()

    # ------------------------------------------------------------------
    # Richer API

    def kind(self) -> str:
        return self._kind

    def details(self) -> str:
        """The text "Show details" reveals ("" when there is none)."""
        return self._details

    def show_message(
        self, text: str, kind: str = "info", details: Optional[str] = None
    ) -> None:
        check_kind(kind)
        self._text = text
        self._kind = kind
        self._details = details or ""
        self._label.setText(str(text))
        self._icon.set_icon(*KIND_ICONS[kind])
        self.setProperty("kind", kind)
        repolish(self)
        self._details_button.setVisible(bool(self._details))
        self._details_view.setPlainText(self._details)
        self._set_details_open(False)
        self._set_showing(True)
        self.messageChanged.emit()

    def set_action(self, text: str, callback: Optional[Callable[[], None]]) -> None:
        """Show a link button such as "Go to Joins"; pass no callback to hide it."""
        self._action_callback = callback
        self.action_button.setText(text)
        self.action_button.setVisible(bool(text and callback))

    def _run_action(self) -> None:
        if self._action_callback is not None:
            self._action_callback()

    def _dismiss(self) -> None:
        self.clear()
        self.dismissed.emit()

    def _toggle_details(self) -> None:
        self._set_details_open(not self._details_box.isVisible())

    def _set_details_open(self, open_: bool) -> None:
        self._details_box.setVisible(open_)
        self._details_button.setText("Hide details" if open_ else "Show details")

    def _copy_details(self) -> None:
        QApplication.clipboard().setText(self._details)
        self._copy_button.setText("Copied")
        self._copy_reset.start()


# ----------------------------------------------------------------------
# Toasts

#: At most this many toasts are stacked; older ones make room.
MAX_TOASTS = 3
#: Widest a toast gets; longer text is shortened in the middle.
TOAST_MAX_W = 520
#: Space kept free on each side of a toast in a narrow window.
_TOAST_SIDE_GAP = 24
_FADE_MS = 180


class _Toast(QWidget):
    """One pill-shaped message; fades in, waits, fades out, then deletes itself.

    At most :data:`TOAST_MAX_W` wide (less in a narrow window); text that
    doesn't fit is shortened in the middle, keeping a path's file name.
    """

    def __init__(self, text: str, kind: str, duration_ms: int, parent: QWidget):
        super().__init__(parent)
        pill = QFrame()
        pill.setProperty("cciRole", "toast")
        # Both effects are built without a parent: parented to their widgets as
        # well, they crashed PySide now and then when toasts were torn down. The
        # attributes keep them alive, since setGraphicsEffect doesn't.
        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setBlurRadius(24)
        self._shadow.setOffset(0, 6)
        self._shadow.setColor(qcolor(current().colors.shadow_toast))
        pill.setGraphicsEffect(self._shadow)
        row = QHBoxLayout(pill)
        row.setContentsMargins(14, 8, 16, 8)
        row.setSpacing(8)
        row.addWidget(IconLabel(*KIND_ICONS[kind]))
        self.label = ElidedLabel(text)
        row.addWidget(self.label)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 4, 12, 12)  # room for the shadow
        outer.addWidget(pill)
        self.setMaximumWidth(
            min(TOAST_MAX_W, max(160, parent.width() - 2 * _TOAST_SIDE_GAP))
        )
        self.setAccessibleName(text)

        self._opacity = QGraphicsOpacityEffect()
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_to(1.0)
        QTimer.singleShot(duration_ms, self.dismiss)

    def _fade_to(self, value: float) -> None:
        self._fade.stop()
        self._fade.setDuration(_FADE_MS)
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(value)
        self._fade.start()

    def dismiss(self) -> None:
        self._fade.finished.connect(self.deleteLater)
        self._fade_to(0.0)


class ToastHost(QWidget):
    """Stacks toasts at the bottom centre of *target*, above its other children."""

    def __init__(self, target: QWidget, bottom_margin: int = 18):
        super().__init__(target)
        # The busy overlay looks for this role to keep toasts above it.
        self.setProperty("cciRole", "toastHost")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, bottom_margin)
        self._layout.setSpacing(0)
        self._layout.addStretch(1)
        target.installEventFilter(self)
        self.setGeometry(target.rect())
        self.show()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return False

    def toasts(self) -> List[QWidget]:
        return [
            item.widget()
            for item in (self._layout.itemAt(i) for i in range(self._layout.count()))
            if item.widget() is not None
        ]

    def show_toast(self, text: str, kind: str = "success", duration_ms: int = 3000):
        check_kind(kind)
        for old in self.toasts()[: max(0, len(self.toasts()) - MAX_TOASTS + 1)]:
            old.hide()  # Before un-parenting (see cci_ui.widgets).
            old.setParent(None)
            old.deleteLater()
        toast = _Toast(text, kind, duration_ms, self)
        self._layout.addWidget(toast, 0, Qt.AlignmentFlag.AlignHCenter)
        self.raise_()
        return toast


def show_toast(
    anchor: QWidget, text: str, kind: str = "success", duration_ms: int = 3000
) -> QWidget:
    """Show a toast at the bottom of *anchor*'s window (creating its host once)."""
    window = anchor.window()
    host = window.findChild(
        ToastHost, options=Qt.FindChildOption.FindDirectChildrenOnly
    )
    if host is None:
        host = ToastHost(window, bottom_margin=current().metrics.status_h + 18)
    return host.show_toast(text, kind, duration_ms)


def show_error(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: str = "",
    *,
    informative: str = "",
) -> None:
    """A modal error; *details* (e.g. a traceback) sit behind "Show Details…".

    *informative* is a sentence under *message*, such as what to do next.
    """
    box = QMessageBox(QMessageBox.Icon.Critical, title, message, parent=parent)
    if informative:
        box.setInformativeText(informative)
    if details:
        box.setDetailedText(details)
    box.exec()


__all__ = [
    "KINDS",
    "KIND_ICONS",
    "MAX_TOASTS",
    "TOAST_MAX_W",
    "StatusBanner",
    "ToastHost",
    "check_kind",
    "show_error",
    "show_toast",
]
