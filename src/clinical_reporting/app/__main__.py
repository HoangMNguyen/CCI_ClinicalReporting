"""
Historically the entire UI implementation lived in this module.  The
codebase now organises the logic into the :mod:`ui` package; this file is
kept so existing imports (``from widget import Widget``) continue to work
without modification.
"""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PACKAGE_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from clinical_reporting.ui.main_widget import Widget, main

__all__ = ["Widget", "main"]


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import sys

    sys.exit(main())
