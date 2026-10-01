"""Load the bundled Inter font and build the app fonts.

Inter ships with the apps (SIL Open Font License, see
``assets/fonts/OFL.txt``). If it can't be loaded, Qt falls back through
:data:`~cci_ui.theme.tokens.FONT_FAMILIES` to Segoe UI.
"""

from __future__ import annotations

import logging
from typing import List

from PySide6.QtGui import QFont, QFontDatabase

from cci_ui.assets import asset
from cci_ui.theme.tokens import BODY_PX, FONT_FAMILIES, MONO_FAMILIES

logger = logging.getLogger(__name__)

_loaded_families: List[str] = []


def load_bundled() -> List[str]:
    """Register the bundled font files with Qt once; return their families."""
    if _loaded_families:
        return list(_loaded_families)
    for path in sorted(asset("fonts").glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            logger.warning("Could not load bundled font %s", path)
            continue
        for family in QFontDatabase.applicationFontFamilies(font_id):
            if family not in _loaded_families:
                _loaded_families.append(family)
    return list(_loaded_families)


def ui_font(pixel_size: int = BODY_PX) -> QFont:
    """The interface font at *pixel_size* logical pixels."""
    font = QFont(list(FONT_FAMILIES))
    font.setPixelSize(pixel_size)
    return font


def mono_font(pixel_size: int = 12) -> QFont:
    """A monospaced font for error details and code."""
    font = QFont(list(MONO_FAMILIES))
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(pixel_size)
    return font


__all__ = ["load_bundled", "mono_font", "ui_font"]
