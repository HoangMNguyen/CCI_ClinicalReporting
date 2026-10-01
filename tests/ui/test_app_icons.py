"""The tools' app icons (cci_ui.app_icons) and how the builds use them."""

import ctypes
import struct
import sys

import pytest
from PySide6.QtGui import QColor, QImage

from cci_ui.app_icons import APP_ICONS, ICON_SIZES, ico_bytes, render_app_icon
from cci_ui.assets import app_icon_path


def _entries(data: bytes):
    """(size, image) for each image in an ``.ico`` file's *data*."""
    _reserved, _kind, count = struct.unpack_from("<HHH", data, 0)
    entries = []
    for index in range(count):
        width, _height, *_rest, length, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + 16 * index
        )
        image = QImage.fromData(data[offset : offset + length])
        entries.append((width or 256, image))
    return entries


def _close(color: QColor, hex_rgb: str, tolerance: int = 40) -> bool:
    other = QColor(hex_rgb)
    return all(
        abs(a - b) <= tolerance for a, b in zip(color.getRgb()[:3], other.getRgb()[:3])
    )


def _largest_difference(first: QImage, second: QImage) -> int:
    # Premultiplied: a faint edge pixel's color can't swing with its alpha.
    first = first.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    second = second.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    return max(
        abs(a - b)
        for x in range(first.width())
        for y in range(first.height())
        for a, b in zip(
            first.pixelColor(x, y).getRgb(), second.pixelColor(x, y).getRgb()
        )
    )


def test_the_icon_files_are_drawn_from_app_icons_as_it_is(qapp):
    """Fails after changing APP_ICONS until ``python -m cci_ui.app_icons`` runs."""
    for app_id, app_icon in APP_ICONS.items():
        entries = _entries(app_icon_path(app_id).read_bytes())

        assert [size for size, _image in entries] == list(ICON_SIZES), app_id
        for size, image in entries:
            fresh = render_app_icon(app_icon, size)
            # A little leeway, for drawing that changes between Qt versions.
            assert _largest_difference(image, fresh) <= 8, (app_id, size)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows decodes the icons")
def test_windows_can_read_every_image_of_every_icon():
    user32 = ctypes.WinDLL("user32")  # Its own handle: the settings stay here.
    user32.CreateIconFromResourceEx.restype = ctypes.c_void_p
    user32.CreateIconFromResourceEx.argtypes = [
        ctypes.c_char_p,
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.DestroyIcon.argtypes = [ctypes.c_void_p]
    for app_id in APP_ICONS:
        data = app_icon_path(app_id).read_bytes()
        _reserved, _kind, count = struct.unpack_from("<HHH", data, 0)
        for index in range(count):
            width, *_rest, length, offset = struct.unpack_from(
                "<BBBBHHII", data, 6 + 16 * index
            )
            entry = data[offset : offset + length]
            # As Windows reads an icon resource (version 0x00030000).
            handle = user32.CreateIconFromResourceEx(
                entry, len(entry), 1, 0x00030000, width or 256, width or 256, 0
            )

            assert handle, (app_id, width)
            user32.DestroyIcon(handle)


def test_an_icon_is_a_white_glyph_on_a_rounded_square_of_the_tools_color(qapp):
    for app_id, app_icon in APP_ICONS.items():
        image = render_app_icon(app_icon, 64)
        glyph = {
            image.pixelColor(x, y).name() for x in range(16, 48) for y in range(16, 48)
        }

        assert image.pixelColor(0, 0).alpha() == 0, app_id  # Rounded corner.
        assert _close(image.pixelColor(32, 6), app_icon.color), app_id
        assert "#ffffff" in glyph, app_id


def test_ico_files_hold_png_images_of_their_sizes(qapp):
    images = [QImage(size, size, QImage.Format.Format_ARGB32) for size in (16, 256)]
    for image in images:
        image.fill(QColor("#0071E3"))

    entries = _entries(ico_bytes(images))

    assert [(size, image.width()) for size, image in entries] == [
        (16, 16),
        (256, 256),
    ]


def test_ico_files_take_images_up_to_256_px(qapp):
    with pytest.raises(ValueError):
        ico_bytes([QImage(300, 300, QImage.Format.Format_ARGB32)])
