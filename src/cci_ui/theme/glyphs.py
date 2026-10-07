"""Render the bundled line icons in any token color.

The icons (Lucide, ISC license) are SVG files drawn with ``currentColor``;
:func:`render_pixmap` swaps in a token color and draws them at the exact
device-pixel size, so they stay sharp at 125%, 150%, and 200% scaling.

Qt stylesheets can't recolor images, so :func:`export_glyphs` also writes the
few small images the stylesheet needs (combo arrows, the checkbox tick) as
PNG files in the current scheme's colors, into the user's cache folder
(outside any synced project folder). Set ``CCI_UI_GLYPHS`` to use another
folder, as the tests do.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, NamedTuple, Optional

from PySide6.QtCore import QByteArray, QRectF, QSize, QStandardPaths, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from cci_ui.assets import asset
from cci_ui.theme.tokens import Color, ColorTokens

logger = logging.getLogger(__name__)

GLYPHS_ENV = "CCI_UI_GLYPHS"

#: Slightly lighter than Lucide's default 2px, closer to Apple's line weight.
STROKE_WIDTH = "1.75"

#: Bump when the way glyph files are drawn changes, so old files aren't reused.
_GLYPH_FORMAT = 1


class Glyph(NamedTuple):
    """One stylesheet image: which icon, in which color token, how big."""

    icon: str
    token: str
    size: int
    #: Line weight in the icon's 24-unit grid; small glyphs need a heavier line.
    stroke: str = STROKE_WIDTH


#: Stylesheet placeholder -> the image it stands for.
GLYPHS: Dict[str, Glyph] = {
    "glyph_chevron_down": Glyph("chevron-down", "text_secondary", 14, "2.25"),
    "glyph_chevron_down_disabled": Glyph("chevron-down", "text_disabled", 14, "2.25"),
    "glyph_check": Glyph("check", "on_accent", 12, "3"),
    "glyph_calendar_prev": Glyph("chevron-left", "text_primary", 16, "2"),
    "glyph_calendar_next": Glyph("chevron-right", "text_primary", 16, "2"),
}

_pixmap_cache: Dict[tuple, QPixmap] = {}


def icon_path(name: str) -> Path:
    """The SVG file of the icon called *name* (e.g. ``"folder-open"``)."""
    return asset("icons", f"{name}.svg")


@lru_cache(maxsize=None)
def _svg_source(name: str) -> str:
    return icon_path(name).read_text(encoding="utf-8")


def _colored_svg(name: str, color: Color, stroke: str) -> QByteArray:
    source = _svg_source(name).replace("currentColor", color.hex_rgb)
    source = source.replace('stroke-width="2"', f'stroke-width="{stroke}"')
    return QByteArray(source.encode("utf-8"))


def render_image(
    name: str,
    color: Color,
    size: QSize,
    scale: float = 1.0,
    stroke: str = STROKE_WIDTH,
) -> QImage:
    """Draw icon *name* in *color* into an image of *size* logical pixels.

    The image has ``size * scale`` device pixels. Icons are square, so in a
    non-square *size* the icon is drawn centred at the shorter side's size.
    """
    width = max(1, round(size.width() * scale))
    height = max(1, round(size.height() * scale))
    side = min(width, height)
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(_colored_svg(name, color, stroke))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setOpacity(color.a)
    renderer.render(
        painter, QRectF((width - side) / 2, (height - side) / 2, side, side)
    )
    painter.end()
    image.setDevicePixelRatio(scale)
    return image


def render_pixmap(name: str, color: Color, size: QSize, scale: float = 1.0) -> QPixmap:
    """Cached :class:`QPixmap` version of :func:`render_image`."""
    key = (name, color, size.width(), size.height(), round(scale, 3))
    pixmap = _pixmap_cache.get(key)
    if pixmap is None:
        pixmap = QPixmap.fromImage(render_image(name, color, size, scale))
        _pixmap_cache[key] = pixmap
    return pixmap


def glyph_root() -> Path:
    """Folder that holds the exported stylesheet images."""
    override = os.environ.get(GLYPHS_ENV)
    if override:
        return Path(override)
    location = QStandardPaths.StandardLocation.GenericCacheLocation
    base = QStandardPaths.writableLocation(location) or tempfile.gettempdir()
    return Path(base) / "CCI" / "cci_ui-glyphs"


def _write_image_atomically(image: QImage, target: Path) -> None:
    """Write *image* so no reader ever sees a half-written file."""
    handle, temp_name = tempfile.mkstemp(
        prefix=target.stem, suffix=".png", dir=target.parent
    )
    os.close(handle)
    try:
        if not image.save(temp_name, "PNG"):
            raise OSError(f"Could not write {target}")
        try:
            os.replace(temp_name, target)
        except PermissionError:
            # Windows refuses while another tool is reading the file; that
            # file is a finished copy of the same image, so keep using it.
            if QImage(str(target)).isNull():
                raise
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def export_glyphs(colors: ColorTokens, root: Optional[Path] = None) -> Dict[str, str]:
    """Write the stylesheet images for *colors*; return placeholder -> file path.

    Each image is written at 1x and 2x (``name@2x.png``, which Qt picks up by
    itself on high-DPI screens). Files are reused across runs: the folder
    name is a hash of everything they depend on, and a missing or unreadable
    file is written again.
    """
    specs = {
        key: (glyph, getattr(colors, glyph.token)) for key, glyph in GLYPHS.items()
    }
    fingerprint = repr(
        (
            _GLYPH_FORMAT,
            sorted(specs.items()),
            sorted((g.icon, _svg_source(g.icon)) for g, _ in specs.values()),
        )
    )
    folder = (root or glyph_root()) / hashlib.sha1(fingerprint.encode()).hexdigest()[
        :12
    ]
    folder.mkdir(parents=True, exist_ok=True)

    paths = {}
    for key, (glyph, color) in specs.items():
        path = folder / f"{key}.png"
        for scale, target in ((1.0, path), (2.0, folder / f"{key}@2x.png")):
            if target.exists() and not QImage(str(target)).isNull():
                continue
            size = QSize(glyph.size, glyph.size)
            image = render_image(glyph.icon, color, size, scale, glyph.stroke)
            _write_image_atomically(image, target)
        paths[key] = path.as_posix()
    return paths


__all__ = [
    "GLYPHS",
    "GLYPHS_ENV",
    "Glyph",
    "export_glyphs",
    "glyph_root",
    "icon_path",
    "render_image",
    "render_pixmap",
]
