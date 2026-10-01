"""Remember each tool's window size, position, and layout between runs.

On first launch a window opens at its preferred size, reduced to 90% of the
screen the mouse is on, and centred. After that it reopens where it was,
maximized or not; Qt moves it back on screen if that monitor is gone.
Values are stored per tool in the settings shared by all CCI tools.

:meth:`WindowState.remember` does it all for a tool's main window: it
places the window (and its shell's sidebar) now and saves both whenever
the window closes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Tuple

from PySide6.QtCore import QByteArray, QEvent, QObject, QRect, QSettings
from PySide6.QtGui import QCursor, QGuiApplication, QScreen
from PySide6.QtWidgets import QWidget

from cci_ui.theme.manager import shared_settings

if TYPE_CHECKING:
    from cci_ui.widgets.shell import AppShell

#: Share of the screen a first-launch window may take at most.
FIRST_LAUNCH_SCREEN_SHARE = 0.9
#: Keys of the stored values, under ``windows/<app id>/``.
GEOMETRY_KEY = "geometry"
SIDEBAR_WIDTH_KEY = "sidebarWidth"
SIDEBAR_COLLAPSED_KEY = "sidebarCollapsed"


def fitting_min_size(min_size: Tuple[int, int], screen: QScreen) -> Tuple[int, int]:
    """*min_size*, but never larger than *screen*'s usable area."""
    area = screen.availableGeometry()
    return min(min_size[0], area.width()), min(min_size[1], area.height())


def first_launch_geometry(
    size: Tuple[int, int], screen: QScreen, min_size: Tuple[int, int] = (0, 0)
) -> QRect:
    """*size* limited to 90% of *screen*'s usable area, centred on it.

    The result is never smaller than *min_size* (itself limited to the
    screen), so the window Qt ends up with is the one that was centred.
    """
    area = screen.availableGeometry()
    min_width, min_height = fitting_min_size(min_size, screen)
    width = max(min_width, min(size[0], int(area.width() * FIRST_LAUNCH_SCREEN_SHARE)))
    height = max(
        min_height, min(size[1], int(area.height() * FIRST_LAUNCH_SCREEN_SHARE))
    )
    rect = QRect(0, 0, width, height)
    rect.moveCenter(area.center())
    return rect


class WindowState:
    """Stored window geometry and other layout values for one tool."""

    def __init__(self, app_id: str, settings: Optional[QSettings] = None):
        self._settings = settings if settings is not None else shared_settings()
        self._prefix = f"windows/{app_id}/"

    def value(
        self, key: str, default: Any = None, as_type: Optional[type] = None
    ) -> Any:
        """The stored value, converted to *as_type* if given.

        Convert numbers and flags: INI files and the registry may return them
        as text ("260", "true").
        """
        if as_type is None:
            return self._settings.value(self._prefix + key, default)
        return self._settings.value(self._prefix + key, default, as_type)

    def set_value(self, key: str, value: Any) -> None:
        self._settings.setValue(self._prefix + key, value)

    def restore(
        self,
        window: QWidget,
        *,
        first_size: Tuple[int, int],
        min_size: Tuple[int, int],
    ) -> bool:
        """Size and place *window*; return True if a saved geometry was used.

        On screens smaller than *min_size* the minimum shrinks to fit, so the
        window never opens partly off screen.
        """
        screen = (
            QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        )
        if screen is None:
            window.setMinimumSize(*min_size)
            window.resize(*first_size)
            return False
        window.setMinimumSize(*fitting_min_size(min_size, screen))
        saved = self.value(GEOMETRY_KEY)
        if isinstance(saved, QByteArray) and not saved.isEmpty():
            if window.restoreGeometry(saved):
                return True
        window.setGeometry(first_launch_geometry(first_size, screen, min_size))
        return False

    def save(self, window: QWidget) -> None:
        """Remember *window*'s geometry (:meth:`remember` calls it on close)."""
        self.set_value(GEOMETRY_KEY, window.saveGeometry())
        self._settings.sync()

    def restore_sidebar(self, shell: AppShell) -> bool:
        """Give *shell*'s sidebar its saved width and collapsed state, if saved."""
        if shell.sidebar is None or self.value(SIDEBAR_WIDTH_KEY) is None:
            return False
        shell.restore_sidebar(
            self.value(SIDEBAR_WIDTH_KEY, shell.sidebar_width(), int),
            self.value(SIDEBAR_COLLAPSED_KEY, False, bool),
        )
        return True

    def save_sidebar(self, shell: AppShell) -> None:
        """Remember *shell*'s sidebar width and whether it is collapsed."""
        if shell.sidebar is None:
            return
        self.set_value(SIDEBAR_WIDTH_KEY, shell.sidebar_width())
        self.set_value(SIDEBAR_COLLAPSED_KEY, shell.is_sidebar_collapsed())
        self._settings.sync()

    def remember(
        self,
        window: QWidget,
        *,
        first_size: Tuple[int, int],
        min_size: Tuple[int, int],
        shell: Optional[AppShell] = None,
    ) -> None:
        """Place *window* (and *shell*'s sidebar) as last time; save them on close.

        Call before showing the window.
        """
        self.restore(window, first_size=first_size, min_size=min_size)
        if shell is not None:
            self.restore_sidebar(shell)
        _SaveOnClose(self, window, shell)


class _SaveOnClose(QObject):
    """Saves a window's state when it closes; owned by the window."""

    def __init__(
        self, state: WindowState, window: QWidget, shell: Optional[AppShell]
    ) -> None:
        super().__init__(window)
        self._state = state
        self._shell = shell
        window.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.parent() and event.type() == QEvent.Type.Close:
            self._state.save(watched)
            if self._shell is not None:
                self._state.save_sidebar(self._shell)
        return False


__all__ = [
    "FIRST_LAUNCH_SCREEN_SHARE",
    "GEOMETRY_KEY",
    "SIDEBAR_COLLAPSED_KEY",
    "SIDEBAR_WIDTH_KEY",
    "WindowState",
    "first_launch_geometry",
    "fitting_min_size",
]
