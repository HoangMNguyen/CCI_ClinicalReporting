"""Locate files bundled with :mod:`cci_ui` (fonts, icons).

Works when running from source and inside a PyInstaller build, where every
``.spec`` file copies ``src/cci_ui/assets`` to ``cci_ui/assets`` next to the
unpacked program (``build_support.ui_datas()``). Set ``CCI_UI_ASSETS`` to a
folder to override both.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def assets_root() -> Path:
    """The folder that holds the bundled assets."""
    override = os.environ.get("CCI_UI_ASSETS")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "cci_ui" / "assets"
    return Path(__file__).resolve().parent / "assets"


def asset(*parts: str) -> Path:
    """Path to one bundled asset, e.g. ``asset("fonts", "Inter-Regular.ttf")``."""
    return assets_root().joinpath(*parts)


def app_icon_path(app_id: str) -> Path:
    """The ``.ico`` file of the tool *app_id* (it may not exist).

    The icons are drawn by :mod:`cci_ui.app_icons`.
    """
    return asset("app-icons", f"{app_id}.ico")


__all__ = ["app_icon_path", "asset", "assets_root"]
