"""Regression tests for ``WidgetBaseMixin._safe_disconnect``.

PySide6 emits a ``RuntimeWarning`` (routed through Python's ``warnings``
machinery, not as an exception) when ``disconnect`` is called on a signal that
has no matching connection. The helper must swallow both that warning and any
``RuntimeError``/``TypeError`` so repopulating tables stays quiet.

These use a fake signal so the contract is verified without a live Qt event
loop / display.
"""

import warnings

from clinical_reporting.ui.base import WidgetBaseMixin


class _FakeSignal:
    """Stand-in for a bound Qt signal with controllable disconnect behaviour."""

    def __init__(self, behavior: str = "ok"):
        self.behavior = behavior
        self.disconnect_args: list[tuple] = []

    def disconnect(self, *args):
        self.disconnect_args.append(args)
        if self.behavior == "raise":
            raise RuntimeError("Failed to disconnect (None) from signal ...")
        if self.behavior == "warn":
            warnings.warn("Failed to disconnect (None) from signal ...", RuntimeWarning)


def test_safe_disconnect_suppresses_runtime_warning():
    signal = _FakeSignal("warn")
    # Treat any leaking RuntimeWarning as an error to prove it is suppressed.
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        WidgetBaseMixin._safe_disconnect(signal)
    assert signal.disconnect_args == [()]


def test_safe_disconnect_swallows_runtime_error():
    signal = _FakeSignal("raise")
    # Must not propagate.
    WidgetBaseMixin._safe_disconnect(signal)
    assert signal.disconnect_args == [()]


def test_safe_disconnect_without_slot_calls_bare_disconnect():
    signal = _FakeSignal("ok")
    WidgetBaseMixin._safe_disconnect(signal)
    assert signal.disconnect_args == [()]


def test_safe_disconnect_forwards_specific_slot():
    signal = _FakeSignal("ok")
    slot = object()
    WidgetBaseMixin._safe_disconnect(signal, slot)
    assert signal.disconnect_args == [(slot,)]
