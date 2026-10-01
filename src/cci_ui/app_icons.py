"""The tools' app icons: a white line icon on a rounded square of the tool's color.

:data:`APP_ICONS` gives each tool (by its app id, as passed to
:func:`cci_ui.app.create_app`) a glyph from the bundled icons and a color.
The ``.ico`` files in ``assets/app-icons`` are drawn from it, one image per
size (the smallest drawn on whole pixels). Draw them again after changing it::

    python -m cci_ui.app_icons

:func:`cci_ui.assets.app_icon_path` finds a tool's icon, from source or
inside a built executable. The executables' file icons come from the same
files (``build_support.app_icon``), and :func:`~cci_ui.app.create_app` makes
it the window icon of the tools that use it.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Sequence

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter

from cci_ui.icons import IconName
from cci_ui.theme.glyphs import render_image
from cci_ui.theme.tokens import Color


class AppIcon(NamedTuple):
    """What one tool's icon shows."""

    glyph: str  # A bundled icon, drawn white.
    color: str  # The square's color, "#RRGGBB".


#: Each tool's icon, by app id.
APP_ICONS: Dict[str, AppIcon] = {
    "clinical-reporting": AppIcon(IconName.APP_CLINICAL_REPORTING, "#0071E3"),
    "cci-automation": AppIcon(IconName.APP_CCI_AUTOMATION, "#5856D6"),
    "safety-automation": AppIcon(IconName.APP_SAFETY, "#FF9500"),
    "peer-review-automation": AppIcon(IconName.APP_PEER_REVIEW, "#34C759"),
}
#: The image sizes in each ``.ico`` file (Windows picks the one it needs).
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 256)
#: Where the icon files are kept in the source tree (whatever ``CCI_UI_ASSETS``
#: says), and so where :func:`main` writes them.
SOURCE_FOLDER = Path(__file__).resolve().parent / "assets" / "app-icons"

_WHITE = Color.hex("#FFFFFF")


def _stroke(size: int) -> str:
    """Line weight in the glyph's 24-unit grid: heavier when small."""
    if size <= 24:
        return "2.5"  # At 16 and 20 px, half the grid (see _glyph_side): ~1 px.
    return "2.25" if size <= 48 else "2"


def _glyph_side(size: int, square: float) -> int:
    """The glyph's size, centred on whole pixels.

    In the smallest icons it is 12 px, half the glyphs' 24-unit grid, so
    their lines stay close to whole pixels instead of blurring across two.
    """
    if size <= 20:
        return 12
    side = round(square * 0.6)
    return side + (size - side) % 2  # An even margin each side: no half pixels.


def render_app_icon(app_icon: AppIcon, size: int) -> QImage:
    """Draw *app_icon* as a *size* × *size* image."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    margin = round(size * 0.06)
    square = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    radius = square.width() * 0.225
    color = QColor(app_icon.color)
    fill = QLinearGradient(square.topLeft(), square.bottomLeft())
    fill.setColorAt(0, color.lighter(110))
    fill.setColorAt(1, color.darker(108))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(fill)
    painter.drawRoundedRect(square, radius, radius)
    glyph_side = _glyph_side(size, square.width())
    glyph = render_image(
        app_icon.glyph, _WHITE, QSize(glyph_side, glyph_side), stroke=_stroke(size)
    )
    offset = (size - glyph_side) // 2
    painter.drawImage(QRectF(offset, offset, glyph_side, glyph_side), glyph)
    painter.end()
    return image


def ico_bytes(images: Sequence[QImage]) -> bytes:
    """An ``.ico`` file holding *images*, each stored as PNG."""
    pngs: List[bytes] = []
    for image in images:
        if not 0 < image.width() <= 256 or not 0 < image.height() <= 256:
            raise ValueError(f"Icon images are 1 to 256 px, not {image.size()}")
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise ValueError(f"Could not encode a {image.size()} icon image")
        pngs.append(bytes(data))
    offset = 6 + 16 * len(images)  # After the header and the directory.
    directory = b""
    for image, png in zip(images, pngs):
        # A size of 256 is written as 0; planes 1, 32 bits per pixel.
        width, height = image.width() % 256, image.height() % 256  # 1..256 only.
        directory += struct.pack(
            "<BBBBHHII", width, height, 0, 0, 1, 32, len(png), offset
        )
        offset += len(png)
    return struct.pack("<HHH", 0, 1, len(images)) + directory + b"".join(pngs)


def write_app_icons(folder: Path) -> List[Path]:
    """Write every tool's ``.ico`` file into *folder*; return their paths."""
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for app_id, app_icon in APP_ICONS.items():
        images = [render_app_icon(app_icon, size) for size in ICON_SIZES]
        target = folder / f"{app_id}.ico"
        target.write_bytes(ico_bytes(images))
        written.append(target)
    return written


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841
    for path in write_app_icons(SOURCE_FOLDER):
        print(path)
    return 0


__all__ = [
    "APP_ICONS",
    "ICON_SIZES",
    "SOURCE_FOLDER",
    "AppIcon",
    "ico_bytes",
    "render_app_icon",
    "write_app_icons",
]


if __name__ == "__main__":
    sys.exit(main())
