"""Building widgets never flashes stray windows on screen.

A widget made visible before it has a parent opens as its own top-level
window, and on Windows each one appears on screen for a moment. At start-up
that looked like the app flickering for a second or two. Components show or
hide a child only once it has a parent (see the ``cci_ui.widgets`` package
docstring). Building the gallery (the components it shows) and the Clinical
Reporting window, without showing them, must show no window at all.
"""

import shiboken6
from PySide6.QtWidgets import QApplication

from cci_ui import gallery
from clinical_reporting.ui.window import Widget


def test_building_every_component_shows_no_window(make_manager, shown_windows):
    window, _shell = gallery.build_gallery(make_manager())
    try:
        QApplication.processEvents()
        assert [label for _widget, label in shown_windows] == []
    finally:
        shiboken6.delete(window)


def test_building_the_clinical_reporting_window_shows_no_window(shown_windows):
    window = Widget()
    try:
        QApplication.processEvents()
        assert [label for _widget, label in shown_windows] == []
    finally:
        shiboken6.delete(window)
