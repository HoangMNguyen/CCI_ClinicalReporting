"""Fixtures for tests of the shared design system (cci_ui) and whole windows."""

import pytest
from PySide6.QtCore import QElapsedTimer, QEvent, QObject, QSettings
from PySide6.QtWidgets import QApplication, QWidget

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


@pytest.fixture
def settle(qapp):
    """Wait until a TaskRunner is idle: its jobs, their callbacks, and queued work.

    Waits in ``TaskRunner.wait``, which releases Python's GIL so the worker
    can run; a ``QTest.qWait`` loop keeps it and slows the worker down many
    times over.
    """

    def wait_until_idle(runner, timeout_ms=5000):
        timer = QElapsedTimer()
        timer.start()
        while runner.busy and timer.elapsed() < timeout_ms:
            runner.wait(max(1, timeout_ms - timer.elapsed()))
            QApplication.processEvents()
        assert not runner.busy, "the task runner is still busy"

    return wait_until_idle


class _ShownWindows(QObject):
    """Records each widget shown as its own window, as (widget, label)."""

    def __init__(self):
        super().__init__()
        self.shown = []

    def eventFilter(self, watched, event):  # noqa: N802 (Qt override)
        if (
            event.type() == QEvent.Type.Show
            and isinstance(watched, QWidget)
            and watched.isWindow()
        ):
            text = getattr(watched, "text", lambda: "")() or watched.accessibleName()
            self.shown.append((watched, f"{type(watched).__name__} {text!r}"))
        return False


@pytest.fixture
def shown_windows(qapp):
    """Widgets shown as their own window during the test, as (widget, label).

    A widget shown before it has a parent becomes a window and flashes on
    screen; see tests/ui/test_no_stray_windows.py.
    """
    watcher = _ShownWindows()
    qapp.installEventFilter(watcher)
    yield watcher.shown
    qapp.removeEventFilter(watcher)
