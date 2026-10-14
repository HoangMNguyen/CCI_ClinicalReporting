"""Tests for applying and remembering the appearance and density choices."""

from PySide6.QtCore import QRect
from PySide6.QtGui import QPalette

from cci_ui.theme import manager as theme_manager
from cci_ui.theme.manager import DENSITY_KEY, MODE_KEY, DensityMode, ThemeMode
from cci_ui.theme.tokens import DARK, LIGHT, Density, Scheme


def _window_color(app):
    return app.palette().color(QPalette.ColorRole.Window).name().upper()


class _Screen:
    """A screen with *height* usable pixels."""

    def __init__(self, height):
        self._height = height

    def availableGeometry(self):  # noqa: N802 (Qt API)
        return QRect(0, 0, 1366, self._height)


class _Window:
    """A main window that opens on a screen *height* pixels tall."""

    def __init__(self, height):
        self._screen = _Screen(height)

    def screen(self):
        return self._screen


def test_choices_are_applied_and_survive_a_restart(make_manager, ini_settings):
    manager = make_manager()
    manager.set_mode(ThemeMode.DARK)
    manager.set_density(Density.COMPACT)

    assert _window_color(manager.parent()) == DARK.bg_window.hex_rgb
    assert theme_manager.current().metrics.control_h == 24
    assert ini_settings.value(MODE_KEY) == "dark"
    assert ini_settings.value(DENSITY_KEY) == "compact"

    restarted = make_manager()
    assert restarted.mode is ThemeMode.DARK
    assert restarted.density is Density.COMPACT


def test_theme_changed_fires_once_per_real_change(make_manager):
    manager = make_manager()
    manager.set_mode(ThemeMode.LIGHT)
    manager.apply()
    seen = []
    manager.themeChanged.connect(seen.append)

    manager.set_mode(ThemeMode.DARK)
    manager.set_mode(ThemeMode.DARK)
    manager.set_density(Density.COMPACT)

    assert seen == ["dark"]


def test_system_mode_follows_windows_and_overrides_ignore_it(make_manager, monkeypatch):
    manager = make_manager()
    system = {"scheme": Scheme.LIGHT}
    monkeypatch.setattr(manager, "_system_scheme", lambda: system["scheme"])
    manager.set_mode(ThemeMode.SYSTEM)
    manager.apply()

    system["scheme"] = Scheme.DARK
    manager._on_color_scheme_changed(None)
    assert manager.scheme is Scheme.DARK
    assert _window_color(manager.parent()) == DARK.bg_window.hex_rgb

    manager.set_mode(ThemeMode.LIGHT)
    system["scheme"] = Scheme.DARK
    manager._on_color_scheme_changed(None)
    assert _window_color(manager.parent()) == LIGHT.bg_window.hex_rgb


def test_unknown_system_scheme_means_light(make_manager):
    # The offscreen test platform reports no color scheme at all.
    manager = make_manager()
    manager.set_mode(ThemeMode.SYSTEM)

    assert manager.scheme is Scheme.LIGHT


def test_bad_stored_values_fall_back_to_defaults(make_manager, ini_settings):
    ini_settings.setValue(MODE_KEY, "sepia")
    ini_settings.setValue(DENSITY_KEY, "tiny")

    manager = make_manager()

    assert manager.mode is ThemeMode.SYSTEM
    assert manager.density_mode is DensityMode.AUTOMATIC


def test_density_is_automatic_until_the_user_picks_one(make_manager, ini_settings):
    never_picked = make_manager()
    ini_settings.setValue(DENSITY_KEY, "automatic")
    picked_automatic = make_manager()

    assert never_picked.density_mode is DensityMode.AUTOMATIC
    assert picked_automatic.density_mode is DensityMode.AUTOMATIC


def test_automatic_density_follows_the_screen_the_window_opens_on(make_manager):
    manager = make_manager()
    manager.set_density(DensityMode.COMFORTABLE)
    manager.set_density(DensityMode.AUTOMATIC)

    manager.measure_screen_of(_Window(720))
    short = manager.density, theme_manager.current().metrics.header_h
    manager.measure_screen_of(_Window(1040))
    tall = manager.density, theme_manager.current().metrics.header_h

    assert short == (Density.COMPACT, 36)
    assert tall == (Density.COMFORTABLE, 44)


def test_a_picked_density_ignores_the_screen(make_manager):
    manager = make_manager()
    manager.set_density(DensityMode.COMPACT)

    manager.measure_screen_of(_Window(1040))

    assert manager.density is Density.COMPACT
    assert theme_manager.current().metrics.header_h == 36


def test_preview_tools_do_not_overwrite_the_users_choice(make_manager, ini_settings):
    manager = make_manager(persist=False)
    manager.set_mode(ThemeMode.DARK)

    assert ini_settings.value(MODE_KEY) is None


def test_switching_back_to_system_reads_windows_after_clearing_the_override(
    make_manager, monkeypatch
):
    # Simulate Qt: while an override is set, the color scheme reports it; once
    # cleared, it reports Windows' own scheme (Dark here).
    manager = make_manager()
    override = {"scheme": None}

    def sync_native_scheme():
        overrides = {ThemeMode.LIGHT: Scheme.LIGHT, ThemeMode.DARK: Scheme.DARK}
        override["scheme"] = overrides.get(manager.mode)

    monkeypatch.setattr(manager, "_sync_native_scheme", sync_native_scheme)
    monkeypatch.setattr(
        manager, "_system_scheme", lambda: override["scheme"] or Scheme.DARK
    )

    manager.set_mode(ThemeMode.LIGHT)
    manager.set_mode(ThemeMode.SYSTEM)

    assert manager.scheme is Scheme.DARK
    assert _window_color(manager.parent()) == DARK.bg_window.hex_rgb
