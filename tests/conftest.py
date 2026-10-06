import os
import sys
from pathlib import Path

import pytest

# Qt tests never need a visible screen; this must be set before any QApplication
# exists so the suite behaves the same on a desktop, a server, or CI. The
# desktop session's values are overruled rather than respected: a shell that
# exports QT_QPA_PLATFORM (some desktops set `wayland;xcb`) would otherwise put
# every test window on the user's screen and make sizes, focus and the colour
# scheme depend on the compositor, and the gtk3 platform theme aborts the
# process part-way through an offscreen run.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("QT_QPA_PLATFORMTHEME", None)

# The tests must never count runs on the production usage endpoint.
os.environ["CLINICAL_REPORTING_RUN_COUNTER_URL"] = ""
os.environ["CLINICAL_REPORTING_RUN_COUNTER_TOKEN"] = ""

# Make the project root importable for all tests without duplicating path hacks.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
for entry in (PROJECT_ROOT, SRC_DIR):
    path_str = str(entry)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture(scope="session", autouse=True)
def _glyph_folder(tmp_path_factory):
    """Keep the stylesheet images the theme writes out of the user's cache folder."""
    folder = tmp_path_factory.mktemp("cci_ui-glyphs")
    previous = os.environ.get("CCI_UI_GLYPHS")
    os.environ["CCI_UI_GLYPHS"] = str(folder)
    yield folder
    if previous is None:
        os.environ.pop("CCI_UI_GLYPHS", None)
    else:
        os.environ["CCI_UI_GLYPHS"] = previous


@pytest.fixture(scope="session")
def qapp():
    """One QApplication shared by every Qt test in the session."""
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance()
    if app is None:
        app = widgets.QApplication([])
    return app
