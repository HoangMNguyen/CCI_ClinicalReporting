"""Remember each tool's window size, position, and layout between runs.

On first launch a window opens at its preferred size, reduced to 90% of the
screen the mouse is on, and centred. After that it reopens where it was,
maximized or not; Qt moves it back on screen if that monitor is gone.
Values are stored per tool in the settings shared by all CCI tools.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from PySide6.QtCore import QByteArray, QRect, QSettings
from PySide6.QtGui import QCursor, QGuiApplication, QScreen
from PySide6.QtWidgets import QWidget

from cci_ui.theme.manager import shared_settings

#: Share of the screen a first-launch window may take at most.
FIRST_LAUNCH_SCREEN_SHARE = 0.9


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

    def value(self, key: str, default: Any = None) -> Any:
        return self._settings.value(self._prefix + key, default)

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
        saved = self.value("geometry")
        if isinstance(saved, QByteArray) and not saved.isEmpty():
            if window.restoreGeometry(saved):
                return True
        window.setGeometry(first_launch_geometry(first_size, screen, min_size))
        return False

    def save(self, window: QWidget) -> None:
        """Remember *window*'s geometry (call from its ``closeEvent``)."""
        self.set_value("geometry", window.saveGeometry())
        self._settings.sync()


__all__ = [
    "FIRST_LAUNCH_SCREEN_SHARE",
    "WindowState",
    "first_launch_geometry",
    "fitting_min_size",
]
