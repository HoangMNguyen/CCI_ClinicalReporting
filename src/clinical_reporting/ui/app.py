"""Application entry point for the Clinical Reporting desktop tool."""

from __future__ import annotations

import logging
from typing import Any, Dict

from cci_ui.app import create_app
from cci_ui.theme.tokens import LAYOUT
from cci_ui.window_state import WindowState
from clinical_reporting import __version__, telemetry
from clinical_reporting.ui.main_ui import APP_NAME
from clinical_reporting.ui.window import Widget

#: Settings key and Windows taskbar id of this tool.
APP_ID = "clinical-reporting"
#: Smallest window that keeps every page usable (a 1080p laptop at 150%).
MIN_SIZE = LAYOUT.min_window
#: Size on first launch (at most 90% of the screen).
FIRST_SIZE = LAYOUT.first_launch


def _self_test_extra() -> Dict[str, Any]:
    """The self-test's own checks: whether the exe has its telemetry.json."""
    return {"telemetry_bundled": telemetry.has_bundled_configuration()}


def main() -> int:
    """Start the desktop app and run it until its window closes."""
    # Configure logging for the desktop app. WARNING keeps the console quiet
    # during normal use while still surfacing real problems; set the level to
    # DEBUG to see the detailed filter/join diagnostics.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app, theme = create_app(
        app_id=APP_ID,
        name=APP_NAME,
        version=__version__,
        self_test_extra=_self_test_extra,
    )
    widget = Widget(theme=theme)
    # Reopens where it was, with the sidebar as it was; saved on close.
    WindowState(APP_ID).remember(
        widget, first_size=FIRST_SIZE, min_size=MIN_SIZE, shell=widget.ui.shell
    )
    widget.show()
    return app.exec()
