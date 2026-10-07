"""Tests for the theme-aware icons and the stylesheet images."""

import gc
from pathlib import Path

import pytest
import shiboken6
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QImage

from cci_ui import icons
from cci_ui.assets import asset
from cci_ui.icons import IconName, icon
from cci_ui.theme import manager as theme_manager
from cci_ui.theme.glyphs import GLYPHS, GLYPHS_ENV, export_glyphs, glyph_root
from cci_ui.theme.manager import Theme
from cci_ui.theme.qss import build_stylesheet
from cci_ui.theme.tokens import COMFORTABLE, DARK, LIGHT, Density, Scheme


def _use(monkeypatch, colors, scheme):
    monkeypatch.setattr(
        theme_manager,
        "_current",
        Theme(scheme, Density.COMFORTABLE, colors, COMFORTABLE),
    )


def _solid_pixel_color(pixmap):
    """The color of the first fully opaque pixel, as ``#RRGGBB``."""
    image = pixmap.toImage()
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() == 255:
                return color.name().upper()
    raise AssertionError("icon rendered nothing opaque")


def test_every_icon_name_has_a_bundled_file_and_none_are_unused():
    bundled = {path.stem for path in asset("icons").glob("*.svg")}

    assert set(IconName.all()) | {g.icon for g in GLYPHS.values()} == bundled
    assert asset("icons", "LICENSE").is_file()


def _draws_something(pixmap):
    image = pixmap.toImage()
    return any(
        image.pixelColor(x, y).alpha() > 0
        for y in range(image.height())
        for x in range(image.width())
    )


@pytest.mark.parametrize("scale", [1.0, 1.25, 1.5, 2.0])
def test_icons_render_at_device_resolution_for_every_display_scale(qapp, scale):
    for name in IconName.all():
        pixmap = icon(name).pixmap(QSize(16, 16), scale)

        # Drawn at full device resolution, not upscaled from 16px.
        assert pixmap.width() == round(16 * scale), name
        assert _draws_something(pixmap), name


def test_icons_follow_the_theme_and_disabled_state(qapp, monkeypatch):
    save = icon(IconName.SAVE, "primary")

    _use(monkeypatch, LIGHT, Scheme.LIGHT)
    light = _solid_pixel_color(save.pixmap(QSize(32, 32)))
    disabled = _solid_pixel_color(save.pixmap(QSize(32, 32), QIcon.Mode.Disabled))
    _use(monkeypatch, DARK, Scheme.DARK)
    dark = _solid_pixel_color(save.pixmap(QSize(32, 32)))

    assert light == LIGHT.text_primary.hex_rgb
    assert disabled == LIGHT.text_disabled.hex_rgb
    assert dark == DARK.text_primary.hex_rgb


def _live_clones():
    return sum(1 for engine in icons._cloned_engines if shiboken6.isValid(engine))


def test_icons_survive_garbage_collection(qapp):
    before = _live_clones()
    copies = [icon(IconName.EXPORT, "on_accent") for _ in range(3)]
    for copy in copies:
        # Changing a shared icon makes Qt clone its engine, and a clone is only
        # referenced from Python, so it must be kept alive.
        copy.setIsMask(True)
    gc.collect()

    assert _live_clones() >= before + len(copies)
    for copy in copies:
        assert not copy.pixmap(QSize(16, 16)).isNull()


def test_changing_one_icon_leaves_the_others_alone(qapp):
    changed = icon(IconName.SAVE)
    changed.setIsMask(True)

    assert not icon(IconName.SAVE).isMask()


def test_icons_stay_square_in_a_wide_area(qapp):
    save = icon(IconName.SAVE)

    assert save.actualSize(QSize(48, 16)) == QSize(16, 16)
    assert save.pixmap(QSize(32, 16)).size() == QSize(16, 16)


def test_unknown_names_and_roles_are_rejected(qapp):
    with pytest.raises(FileNotFoundError):
        icon("no-such-icon")
    with pytest.raises(ValueError):
        icon(IconName.SAVE, role="loud")


def test_stylesheet_images_are_written_at_1x_and_2x(qapp, tmp_path):
    paths = export_glyphs(LIGHT, root=tmp_path)
    again = export_glyphs(LIGHT, root=tmp_path)
    dark = export_glyphs(DARK, root=tmp_path)

    assert paths == again and paths != dark
    assert set(paths) == set(GLYPHS)
    for path in paths.values():
        assert "\\" not in path
        assert Path(path).is_file()
        assert Path(path.replace(".png", "@2x.png")).is_file()

    sheet = build_stylesheet(LIGHT, COMFORTABLE, paths)
    assert "${" not in sheet
    assert f'image: url("{paths["glyph_check"]}")' in sheet
    assert "QComboBox::down-arrow" in sheet


def test_a_broken_image_file_is_written_again(qapp, tmp_path):
    paths = export_glyphs(LIGHT, root=tmp_path)
    Path(paths["glyph_check"]).write_bytes(b"half a png")

    export_glyphs(LIGHT, root=tmp_path)

    assert not QImage(paths["glyph_check"]).isNull()


def test_image_folder_can_be_redirected(monkeypatch, tmp_path):
    monkeypatch.setenv(GLYPHS_ENV, str(tmp_path))

    assert glyph_root() == tmp_path


def test_without_images_the_stylesheet_keeps_qt_arrows():
    assert "down-arrow" not in build_stylesheet(LIGHT, COMFORTABLE)


def test_plain_date_fields_keep_their_full_text_width(tmp_path, qapp):
    sheet = build_stylesheet(LIGHT, COMFORTABLE, export_glyphs(LIGHT, root=tmp_path))

    # Only date fields with a calendar popup have a drop-down to make room for.
    assert 'QDateEdit[calendarPopup="true"] {' in sheet
    assert "QComboBox, QDateEdit {" not in sheet
