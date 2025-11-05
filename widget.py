"""Compatibility wrapper for the Clinical Reporting main widget.

Historically the entire UI implementation lived in this module.  The
codebase now organises the logic into the :mod:`ui` package; this file is
kept so existing imports (``from widget import Widget``) continue to work
without modification.
"""

from __future__ import annotations

from ui.main_widget import Widget, main

__all__ = ["Widget", "main"]


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import sys

    sys.exit(main())

