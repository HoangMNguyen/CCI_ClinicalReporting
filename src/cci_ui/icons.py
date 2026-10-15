"""Theme-aware icons for buttons, the sidebar, and status messages.

``icon(IconName.OPEN_FOLDER)`` returns a :class:`QIcon` that draws itself in
the current theme's colors every time it is painted, so icons switch with
light and dark mode without being recreated, and stay sharp at any display
scaling. Disabled buttons get the disabled text color automatically.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

import shiboken6
from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap

from cci_ui.theme.glyphs import icon_path, render_pixmap
from cci_ui.theme.manager import current
from cci_ui.theme.tokens import Color


class IconName:
    """Names of the bundled icons, grouped by where they are used."""

    # Clinical Reporting steps
    SOURCE_DATA = "database"
    ADDITIONAL_INPUT = "file-plus-2"
    STACKED_FORMS = "layers"
    COALESCED_ITEMS = "blend"
    FORMS = "clipboard-list"
    COMMON_ITEMS = "list-checks"
    FORM_ITEMS = "list-tree"
    FILTERS = "funnel"
    JOINS = "merge"
    COMPARISONS = "git-compare"
    ORDER_RENAME = "arrow-up-down"
    PREVIEW_EXPORT = "sheet"
    # CCI Automation workflows
    ENROLLMENT = "users"
    DSMB = "clipboard-check"
    FORMAT_TOOLS = "wrench"
    # Window chrome and display settings
    SIDEBAR = "panel-left"
    BREADCRUMB = "chevron-right"
    DISPLAY = "contrast"
    APPEARANCE_SYSTEM = "monitor"
    APPEARANCE_LIGHT = "sun"
    APPEARANCE_DARK = "moon"
    HELP = "circle-question-mark"
    # Status
    SUCCESS = "circle-check"
    WARNING = "triangle-alert"
    ERROR = "circle-x"
    INFO = "info"
    # Actions
    SEARCH = "search"
    CLOSE = "x"
    OPEN_FOLDER = "folder-open"
    ADD = "plus"
    REMOVE = "minus"
    ADD_SELECTED = "chevron-right"
    ADD_ALL = "chevrons-right"
    REMOVE_SELECTED = "chevron-left"
    REMOVE_ALL = "chevrons-left"
    MOVE_TOP = "arrow-up-to-line"
    MOVE_UP = "arrow-up"
    MOVE_DOWN = "arrow-down"
    MOVE_BOTTOM = "arrow-down-to-line"
    NEXT = "arrow-right"
    REFRESH = "refresh-cw"
    EXPORT = "file-down"
    SAVE = "save"
    ZIP_FILE = "file-archive"
    RUN = "play"
    # Tables and grids
    TICK = "check"
    SECTION_OPEN = "chevron-down"
    SECTION_CLOSED = "chevron-right"
    EDIT = "pencil"
    # App icon glyphs (see cci_ui.app_icons)
    APP_CLINICAL_REPORTING = "table-2"
    APP_CCI_AUTOMATION = "workflow"
    APP_SAFETY = "shield-check"
    APP_PEER_REVIEW = "file-check-2"

    @classmethod
    def all(cls) -> List[str]:
        """Every icon name defined above."""
        return sorted(
            {
                value
                for key, value in vars(cls).items()
                if key.isupper() and isinstance(value, str)
            }
        )


#: Icon role -> color token. ``secondary`` suits most buttons and the sidebar.
ROLE_COLORS: Dict[str, str] = {
    "primary": "text_primary",
    "secondary": "text_secondary",
    "tertiary": "text_tertiary",
    "accent": "accent",
    "on_accent": "on_accent",
    "success": "success",
    "warning": "warning",
    "danger": "danger",
    "info": "info_text",
}

# A QIcon made from an engine owns it, but an engine returned from clone()
# (Qt clones when an icon is modified) is only referenced from Python and
# would be deleted too early; keep those alive, dropping ones Qt has deleted.
_cloned_engines: List[QIconEngine] = []


def _square(size: QSize) -> QSize:
    side = min(size.width(), size.height())
    return QSize(side, side)


class _ThemedSvgEngine(QIconEngine):
    """Draws one SVG icon in the color the current theme gives its role."""

    def __init__(self, name: str, role: str) -> None:
        super().__init__()
        self._name = name
        self._role = role

    def _color(self, mode: QIcon.Mode) -> Color:
        colors = current().colors
        if mode == QIcon.Mode.Disabled and self._role != "on_accent":
            return colors.text_disabled
        return getattr(colors, ROLE_COLORS[self._role])

    def actualSize(  # noqa: N802 (Qt override)
        self, size: QSize, mode: QIcon.Mode, state: QIcon.State
    ) -> QSize:
        return _square(size)

    def scaledPixmap(  # noqa: N802 (Qt override)
        self, size: QSize, mode: QIcon.Mode, state: QIcon.State, scale: float
    ) -> QPixmap:
        return render_pixmap(self._name, self._color(mode), _square(size), scale)

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        return self.scaledPixmap(size, mode, state, 1.0)

    def paint(
        self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State
    ) -> None:
        device = painter.device()
        scale = device.devicePixelRatioF() if device is not None else 1.0
        target = QRect(QPoint(0, 0), _square(rect.size()))
        target.moveCenter(rect.center())
        painter.drawPixmap(target, self.scaledPixmap(target.size(), mode, state, scale))

    def clone(self) -> QIconEngine:
        engine = _ThemedSvgEngine(self._name, self._role)
        _cloned_engines[:] = [e for e in _cloned_engines if shiboken6.isValid(e)]
        _cloned_engines.append(engine)
        return engine

    def key(self) -> str:
        return "cci-themed-svg"

    def iconName(self) -> str:  # noqa: N802 (Qt override)
        return self._name


@lru_cache(maxsize=None)
def _shared_icon(name: str, role: str) -> QIcon:
    if role not in ROLE_COLORS:
        raise ValueError(
            f"Unknown icon role {role!r}; expected one of {sorted(ROLE_COLORS)}"
        )
    if not icon_path(name).is_file():
        raise FileNotFoundError(f"No bundled icon named {name!r}")
    return QIcon(_ThemedSvgEngine(name, role))


def icon(name: str, role: str = "secondary") -> QIcon:
    """A theme-aware icon; *role* picks its color (see :data:`ROLE_COLORS`).

    Each name and role is built once; callers get their own cheap copy, so
    changing one (e.g. ``setIsMask``) never affects the others.
    """
    return QIcon(_shared_icon(name, role))


__all__ = ["ROLE_COLORS", "IconName", "icon"]
