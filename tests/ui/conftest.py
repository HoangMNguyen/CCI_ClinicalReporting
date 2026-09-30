"""Fixtures for tests of the shared design system (cci_ui)."""

import pytest
from PySide6.QtCore import QSettings

from cci_ui.theme import manager as theme_manager


@pytest.fixture
def themed_app(qapp, monkeypatch):
    """The shared QApplication, restored to how it looked before the test."""
    saved = {
        "sheet": qapp.styleSheet(),
        "palette": qapp.palette(),
        "font": qapp.font(),
        "organization": qapp.organizationName(),
        "name": qapp.applicationName(),
        "version": qapp.applicationVersion(),
    }
    monkeypatch.setattr(theme_manager, "_current", theme_manager.current())
    yield qapp
    qapp.setStyleSheet(saved["sheet"])
    qapp.setPalette(saved["palette"])
    qapp.setFont(saved["font"])
    qapp.setOrganizationName(saved["organization"])
    qapp.setApplicationName(saved["name"])
    qapp.setApplicationVersion(saved["version"])
    qapp.styleHints().unsetColorScheme()


@pytest.fixture
def ini_settings(tmp_path):
    """Appearance settings in a throwaway INI file instead of the registry."""
    return QSettings(str(tmp_path / "appearance.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def make_manager(themed_app, ini_settings):
    """Build ThemeManagers that are disconnected from the app after the test."""
    created = []

    def make(settings=None, **kwargs):
        manager = theme_manager.ThemeManager(
            themed_app, settings=settings or ini_settings, **kwargs
        )
        created.append(manager)
        return manager

    yield make
    for manager in created:
        manager.setParent(None)
        manager.deleteLater()
