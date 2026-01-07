"""Backward compatible entry point for launching the UI.

Historically this module contained the entire application.  The runtime
now lives under :mod:`clinical_reporting.app`, but the stub remains so
existing launch scripts that execute ``Clinical_Reporting.py`` keep
working without modification.
"""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from clinical_reporting.app.__main__ import Widget, main

__all__ = ["Widget", "main"]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
