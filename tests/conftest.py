import os
import sys
from pathlib import Path

import pytest

# Qt tests never need a visible screen; this must be set before any QApplication
# exists so the suite behaves the same on a desktop, a server, or CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Make the project root importable for all tests without duplicating path hacks.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
for entry in (PROJECT_ROOT, SRC_DIR):
    path_str = str(entry)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture(scope="session")
def qapp():
    """One QApplication shared by every Qt test in the session."""
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance()
    if app is None:
        app = widgets.QApplication([])
    return app
