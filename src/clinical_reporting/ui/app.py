"""Application entry point for the Clinical Reporting desktop tool."""

from __future__ import annotations

import logging
import sys

from cci_ui.app import create_app
from cci_ui.window_state import first_launch_geometry, fitting_min_size
from clinical_reporting import __version__
from clinical_reporting.ui.window import Widget

#: Smallest window that keeps every page usable (a 1080p laptop at 150%).
MIN_SIZE = (960, 600)


def main() -> int:
    """Start the desktop app and run it until its window closes."""
    # Configure logging for the desktop app. WARNING keeps the console quiet
    # during normal use while still surfacing real problems; set the level to
    # DEBUG to see the detailed filter/join diagnostics.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app, _theme = create_app(
        app_id="clinical-reporting", name="Clinical Reporting", version=__version__
    )
    widget = Widget()
    screen = app.primaryScreen()
    widget.setMinimumSize(*fitting_min_size(MIN_SIZE, screen))
    # At most 90% of the screen, centred (remembered sizes come with the shell).
    widget.setGeometry(first_launch_geometry((1280, 820), screen, MIN_SIZE))
    widget.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
