"""Shared start-up for every CCI tool.

:func:`create_app` is the one place the style, font, theme, display-scaling
policy, window icon, and crash reporting are set, so every tool that starts
with it looks and behaves the same. Call it before creating any window.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

from PySide6.QtCore import QSettings, Qt, QThread, QTimer
from PySide6.QtGui import QFontInfo, QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

import cci_ui.widgets  # noqa: F401  (registers component styles before apply())
from cci_ui.assets import app_icon_path, assets_root
from cci_ui.theme.fonts import load_bundled, ui_font
from cci_ui.theme.manager import SETTINGS_ORGANIZATION, ThemeManager

logger = logging.getLogger(__name__)

#: Set to a JSON file path to have the app report its setup there and quit;
#: used to check a PyInstaller build finds its fonts, style, icon, and the
#: tool's own bundled files.
SELF_TEST_ENV = "CCI_UI_SELFTEST"


def create_app(
    *,
    app_id: str,
    name: str,
    version: str = "",
    argv: Optional[Sequence[str]] = None,
    settings: Optional[QSettings] = None,
    persist: bool = True,
    install_excepthook: bool = True,
    self_test_extra: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Tuple[QApplication, ThemeManager]:
    """Create (or reuse) the QApplication and apply the CCI look.

    Call it once per process. If a QApplication already exists (tests,
    previews), it is reused as is: the display-scaling policy and Windows app
    id can only be set before one exists, so those two steps are skipped.

    Args:
        app_id: Short stable id, e.g. ``"clinical-reporting"``; Windows uses it
            to give each tool its own taskbar entry.
        name: Application name shown to users, e.g. ``"Clinical Reporting"``.
        version: The tool's version string.
        argv: Command-line arguments; defaults to ``sys.argv``.
        settings: Where appearance choices are stored; defaults to the
            settings shared by all CCI tools.
        persist: False for previews and the gallery, so trying another
            appearance there never changes the user's saved choice.
        install_excepthook: Show unexpected errors in a dialog instead of
            losing them (the built executables have no console).
        self_test_extra: The tool's own checks for the self-test report (see
            :data:`SELF_TEST_ENV`), e.g. that it found its bundled files. Their
            keys must differ from the shared ones, or the self-test fails.
    """
    app = QApplication.instance()
    if app is None:
        # Must happen before the application exists; keeps 125%/150% exact.
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        _set_windows_app_id(app_id)
        app = QApplication(list(argv) if argv is not None else sys.argv)

    app.setOrganizationName(SETTINGS_ORGANIZATION)
    app.setApplicationName(name)
    app.setApplicationVersion(version)
    # Fusion draws from the palette and honours the stylesheet everywhere,
    # unlike the native windows11 style; it also looks the same on Linux.
    # (Once a stylesheet is set, app.style() is Qt's stylesheet wrapper, so
    # keep the base style's name for the self-test.)
    style_name = app.setStyle("Fusion").objectName()
    load_bundled()
    app.setFont(ui_font())
    icon_file = app_icon_path(app_id)
    if icon_file.is_file():  # Previews and the gallery have none of their own.
        app.setWindowIcon(QIcon(str(icon_file)))

    theme = ThemeManager(app, settings=settings, persist=persist)
    theme.apply()

    if install_excepthook:
        _install_excepthook()
    self_test_path = os.environ.get(SELF_TEST_ENV)
    if self_test_path:
        QTimer.singleShot(
            1000,
            lambda: _run_self_test(
                app, theme, style_name, Path(self_test_path), self_test_extra
            ),
        )
    return app, theme


def _set_windows_app_id(app_id: str) -> None:
    """Give each tool its own taskbar icon instead of grouping under python.exe."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"CCI.{app_id}")
    except (AttributeError, OSError):
        logger.debug("Could not set the Windows app id", exc_info=True)


class _ErrorDialogHook:
    """``sys.excepthook`` that logs unexpected errors and shows them in a dialog.

    The built executables have no console, so an error raised in a button
    handler would otherwise vanish. Only one dialog is shown at a time (an
    error while painting could otherwise open dialogs endlessly), and only on
    the GUI thread; anything else goes to the previous hook as before.
    """

    def __init__(self, previous) -> None:
        self.previous = previous
        self.showing = False

    def __call__(self, exc_type, exc, tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            self.previous(exc_type, exc, tb)
            return
        logger.error("Unexpected error", exc_info=(exc_type, exc, tb))
        app = QApplication.instance()
        can_show = (
            app is not None
            and not self.showing
            and QGuiApplication.platformName() != "offscreen"
            and QThread.currentThread() is app.thread()
        )
        if not can_show:
            self.previous(exc_type, exc, tb)
            return
        self.showing = True
        try:
            box = QMessageBox(
                QMessageBox.Icon.Critical,
                "Something went wrong",
                str(exc) or exc_type.__name__,
            )
            box.setInformativeText(
                "The action didn't finish. If this keeps happening, copy the "
                "details and send them to the tool's maintainer."
            )
            box.setDetailedText("".join(traceback.format_exception(exc_type, exc, tb)))
            box.exec()
        finally:
            self.showing = False


def _install_excepthook() -> None:
    """Install :class:`_ErrorDialogHook` once per process."""
    if not isinstance(sys.excepthook, _ErrorDialogHook):
        sys.excepthook = _ErrorDialogHook(sys.excepthook)


def _self_test_report(app: QApplication, theme: ThemeManager, style_name: str) -> dict:
    """What the running app loaded: style, font, assets, theme, window icon.

    The tool's own checks are added by :func:`_run_self_test`.
    """
    return {
        "style": style_name,
        "font_family": QFontInfo(app.font()).family(),
        "assets_root": str(assets_root()),
        "assets_found": assets_root().is_dir(),
        "scheme": theme.scheme.value,
        "density": theme.density.value,
        "platform": QGuiApplication.platformName(),
        # Component stylesheet rules made it into the applied stylesheet.
        "components_styled": 'QFrame[cciRole="segmented"]' in app.styleSheet(),
        "window_icon": not app.windowIcon().isNull(),
    }


def _run_self_test(
    app: QApplication,
    theme: ThemeManager,
    style_name: str,
    path: Path,
    extra: Optional[Callable[[], Dict[str, Any]]] = None,
) -> None:
    """Write the self-test report to *path* and quit (exit code 1 on failure).

    If the tool's own checks (*extra*) fail, the report still holds the
    shared ones, plus an ``error`` saying what went wrong.
    """
    exit_code = 1
    try:
        report = _self_test_report(app, theme, style_name)
        try:
            if extra is not None:
                tool_checks = extra()
                clashing = report.keys() & tool_checks.keys()
                if clashing:
                    raise ValueError(f"Self-test keys used twice: {sorted(clashing)}")
                report.update(tool_checks)
            exit_code = 0
        except Exception as exc:
            logger.exception("The tool's self-test checks failed")
            report["error"] = f"{type(exc).__name__}: {exc}"
        # default=str: a tool check's value JSON can't hold still gets written.
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    except Exception:  # Report through the exit code; never leave the app open.
        exit_code = 1
        logger.exception("Self-test failed")
    finally:
        app.exit(exit_code)


__all__ = ["SELF_TEST_ENV", "create_app"]
