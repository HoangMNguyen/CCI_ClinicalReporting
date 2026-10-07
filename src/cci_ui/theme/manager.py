"""Apply the theme to the running app and keep it in step with user choices.

:class:`ThemeManager` owns the appearance mode (System, Light, Dark) and the
density (Comfortable, Compact). Both are shared by all CCI tools through
:func:`shared_settings`, so switching one tool to Dark switches the others
the next time they start. Custom widgets read the active colors and sizes
with :func:`current` at paint time and refresh when
``theme_events().changed`` fires.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtWidgets import QApplication, QWidget

from cci_ui.theme.glyphs import export_glyphs
from cci_ui.theme.palette import to_qpalette
from cci_ui.theme.qss import build_stylesheet
from cci_ui.theme.tokens import (
    COMFORTABLE,
    LIGHT,
    ColorTokens,
    Density,
    Metrics,
    Scheme,
    colors_for,
    metrics_for,
)

logger = logging.getLogger(__name__)

SETTINGS_ORGANIZATION = "CCI"
SETTINGS_APPLICATION = "CCI Suite"
MODE_KEY = "appearance/mode"
DENSITY_KEY = "appearance/density"

#: Screens with less usable height than this default to Compact density.
COMPACT_BELOW_HEIGHT = 800


class ThemeMode(str, Enum):
    """What the user picked in the Display settings."""

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True)
class Theme:
    """The theme currently applied to the app."""

    scheme: Scheme
    density: Density
    colors: ColorTokens
    metrics: Metrics


_current = Theme(Scheme.LIGHT, Density.COMFORTABLE, LIGHT, COMFORTABLE)


def current() -> Theme:
    """The theme currently applied (light and comfortable before any is applied)."""
    return _current


class ThemeEvents(QObject):
    """Tells custom widgets that colors or sizes changed, without a manager handle."""

    #: Emitted after the palette and stylesheet for a new scheme or density apply.
    changed = Signal()


_events: Optional[ThemeEvents] = None


def theme_events() -> ThemeEvents:
    """The process-wide :class:`ThemeEvents`; connect widgets' refresh to ``changed``."""
    global _events
    if _events is None:
        _events = ThemeEvents()
    return _events


def shared_settings() -> QSettings:
    """Settings shared by every CCI tool for this Windows user."""
    return QSettings(
        QSettings.Format.NativeFormat,
        QSettings.Scope.UserScope,
        SETTINGS_ORGANIZATION,
        SETTINGS_APPLICATION,
    )


def repolish(widget: QWidget) -> None:
    """Re-apply stylesheet rules after changing a dynamic property on *widget*."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_invalid(widget: QWidget, invalid: bool) -> None:
    """Mark *widget*'s value as invalid, or clear the mark.

    The stylesheet draws invalid combo boxes in the danger color (see the
    ``invalid`` rule in :mod:`cci_ui.theme.qss`); add rules there before
    marking other kinds of input. Restyles only when the state changes.
    """
    invalid = bool(invalid)  # The rule matches the stored value "true" only.
    if bool(widget.property("invalid")) != invalid:
        widget.setProperty("invalid", invalid)
        repolish(widget)


class ThemeManager(QObject):
    """Applies the palette and stylesheet for the chosen mode and density."""

    #: Emitted with ``"light"`` or ``"dark"`` when the colors on screen change.
    themeChanged = Signal(str)

    def __init__(
        self,
        app: QApplication,
        *,
        settings: Optional[QSettings] = None,
        persist: bool = True,
    ) -> None:
        super().__init__(app)
        self._app = app
        self._settings = settings if settings is not None else shared_settings()
        self._persist = persist
        self._mode = self._read_mode()
        self._density = self._read_density()
        self._applied: Optional[Theme] = None
        self._applying = False
        app.styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)

    # ------------------------------------------------------------------
    # Current choices

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    @property
    def density(self) -> Density:
        return self._density

    @property
    def scheme(self) -> Scheme:
        """The scheme on screen: the user's choice, or the system's in System mode."""
        if self._mode is ThemeMode.LIGHT:
            return Scheme.LIGHT
        if self._mode is ThemeMode.DARK:
            return Scheme.DARK
        return self._system_scheme()

    def set_mode(self, mode: ThemeMode) -> None:
        mode = ThemeMode(mode)
        if mode is self._mode:
            return
        self._mode = mode
        self._write(MODE_KEY, mode.value)
        self.apply()

    def set_density(self, density: Density) -> None:
        density = Density(density)
        if density is self._density:
            return
        self._density = density
        self._write(DENSITY_KEY, density.value)
        self.apply()

    # ------------------------------------------------------------------
    # Applying

    def apply(self) -> None:
        """Apply palette and stylesheet for the current choices; emit what changed."""
        global _current
        if self._applying:
            return
        self._applying = True
        try:
            # Clear or set Qt's override first: in System mode the scheme must
            # be read after the override is gone, or a previous Light/Dark
            # choice would stick (the change signal is ignored while applying).
            self._sync_native_scheme()
            scheme = self.scheme
            theme = Theme(
                scheme, self._density, colors_for(scheme), metrics_for(self._density)
            )
            self._app.setPalette(to_qpalette(theme.colors))
            self._app.setStyleSheet(
                build_stylesheet(theme.colors, theme.metrics, _glyphs_for(theme))
            )
            previous, self._applied, _current = self._applied, theme, theme
        finally:
            self._applying = False

        scheme_changed = previous is None or previous.scheme is not theme.scheme
        density_changed = previous is None or previous.density is not theme.density
        if scheme_changed:
            self.themeChanged.emit(theme.scheme.value)
        if scheme_changed or density_changed:
            theme_events().changed.emit()

    def _sync_native_scheme(self) -> None:
        """Tell Qt the chosen scheme so native parts (the title bar) match."""
        hints = self._app.styleHints()
        if self._mode is ThemeMode.SYSTEM:
            hints.unsetColorScheme()
        elif self._mode is ThemeMode.DARK:
            hints.setColorScheme(Qt.ColorScheme.Dark)
        else:
            hints.setColorScheme(Qt.ColorScheme.Light)

    def _system_scheme(self) -> Scheme:
        system = self._app.styleHints().colorScheme()
        return Scheme.DARK if system == Qt.ColorScheme.Dark else Scheme.LIGHT

    def _on_color_scheme_changed(self, _scheme) -> None:
        # Our own overrides also emit this; only follow Windows in System mode,
        # and only when the scheme really changed (this is what prevents loops).
        if self._mode is not ThemeMode.SYSTEM or self._applied is None:
            return
        if self._system_scheme() is not self._applied.scheme:
            self.apply()

    # ------------------------------------------------------------------
    # Persistence

    def _read_mode(self) -> ThemeMode:
        try:
            return ThemeMode(self._settings.value(MODE_KEY, ThemeMode.SYSTEM.value))
        except ValueError:
            return ThemeMode.SYSTEM

    def _read_density(self) -> Density:
        stored = self._settings.value(DENSITY_KEY, None)
        try:
            return Density(stored) if stored else default_density(self._app)
        except ValueError:
            return default_density(self._app)

    def _write(self, key: str, value: str) -> None:
        if self._persist:
            self._settings.setValue(key, value)
            self._settings.sync()


def _glyphs_for(theme: Theme) -> Optional[Dict[str, str]]:
    """Stylesheet images for *theme*, or ``None`` (Qt's defaults) if they can't be written."""
    try:
        return export_glyphs(theme.colors)
    except OSError:
        logger.warning(
            "Could not write stylesheet images; using Qt's own", exc_info=True
        )
        return None


def default_density(app: QApplication) -> Density:
    """Compact on short screens (laptops at 125-150%), Comfortable elsewhere."""
    screen = app.primaryScreen()
    if (
        screen is not None
        and screen.availableGeometry().height() < COMPACT_BELOW_HEIGHT
    ):
        return Density.COMPACT
    return Density.COMFORTABLE


__all__ = [
    "DENSITY_KEY",
    "MODE_KEY",
    "SETTINGS_APPLICATION",
    "SETTINGS_ORGANIZATION",
    "Theme",
    "ThemeEvents",
    "ThemeManager",
    "ThemeMode",
    "current",
    "default_density",
    "repolish",
    "set_invalid",
    "shared_settings",
    "theme_events",
]
