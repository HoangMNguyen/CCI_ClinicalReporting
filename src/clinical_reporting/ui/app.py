"""Application entry point for the Clinical Reporting desktop tool."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from clinical_reporting.ui.window import Widget


def main() -> int:
    """Entry point used by local testing."""
    # Configure logging for the desktop app. WARNING keeps the console quiet
    # during normal use while still surfacing real problems; set the level to
    # DEBUG to see the detailed filter/join diagnostics.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
