"""Launch the Clinical Reporting desktop application."""

from __future__ import annotations

import sys

from clinical_reporting.ui.app import main
from clinical_reporting.ui.window import Widget

__all__ = ["Widget", "main"]


if __name__ == "__main__":  # pragma: no cover - process entry point
    sys.exit(main())
