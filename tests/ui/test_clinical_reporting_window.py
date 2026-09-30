"""The Clinical Reporting window as a whole (beyond its background tasks)."""

import sys

import shiboken6
from PySide6.QtCore import SIGNAL

from cci_ui.theme.manager import theme_events
from clinical_reporting import feedback
from clinical_reporting.ui.window import Widget


def _theme_listeners() -> int:
    return theme_events().receivers(SIGNAL("changed()"))


def test_the_window_follows_theme_changes_until_it_is_deleted(qapp, monkeypatch):
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: raised.append(args[1]))
    # A first window lets any module-wide theme listeners connect for good.
    shiboken6.delete(Widget())
    before = _theme_listeners()

    window = Widget()
    assert _theme_listeners() > before
    shiboken6.delete(window)
    theme_events().changed.emit()

    assert _theme_listeners() == before
    assert raised == []


def test_a_theme_change_only_recolors(qapp):
    window = Widget()
    shown = feedback.warning("Cannot run:\n- Static filter 1 must have an item.")
    window.label_run_confirmation.setText(shown)
    try:
        theme_events().changed.emit()

        assert window.label_run_confirmation.text() == shown
    finally:
        shiboken6.delete(window)
