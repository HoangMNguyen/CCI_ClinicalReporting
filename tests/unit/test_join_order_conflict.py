"""Tests for join-order conflict detection and run guarding."""

import types

import pandas as pd

from clinical_reporting.models import CLForm, JoinHow
from clinical_reporting.report import CLReport
from clinical_reporting.ui.output import RunAndSaveMixin
from clinical_reporting.ui.window import WidgetBaseMixin


def _report_with_orders(orders: dict) -> CLReport:
    """Build a report whose selected forms carry the given join orders."""
    report = CLReport()
    report.selected_forms = {}
    for name, order in orders.items():
        form = CLForm(name)
        if order is not None:
            form.set_join_order(order)
        report.selected_forms[name] = form
    return report


# ---------------------------------------------------------------------------
# Core detection


def test_get_join_order_conflicts_flags_shared_orders():
    report = _report_with_orders({"DM": 1, "VS": 2, "AE": 2})
    assert report.get_join_order_conflicts() == {2: ["AE", "VS"]}


def test_get_join_order_conflicts_empty_when_unique():
    report = _report_with_orders({"DM": 1, "VS": 2, "AE": 3})
    assert report.get_join_order_conflicts() == {}


def test_get_join_order_conflicts_ignores_unset_orders():
    # Forms without a configured order default to "join last" and are not
    # treated as conflicting with each other.
    report = _report_with_orders({"DM": None, "VS": None, "AE": 1})
    assert report.get_join_order_conflicts() == {}


# ---------------------------------------------------------------------------
# Run guarding (mixin helpers, no QApplication required)


class _FakeButton:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, value):  # noqa: N802 (Qt naming convention)
        self.enabled = value


class _FakeLabel:
    def __init__(self):
        self._text = ""

    def setText(self, text):  # noqa: N802
        self._text = text or ""

    def text(self):
        return self._text


class DummyRunWidget(RunAndSaveMixin, WidgetBaseMixin):
    """Compose just enough of the widget to exercise the run guard."""

    def __init__(self, report: CLReport):
        self.report = report
        self.button = _FakeButton()
        self.label_run_confirmation = _FakeLabel()
        self.ui = types.SimpleNamespace(pushButton_run=self.button)


def test_conflict_message_none_when_unique():
    widget = DummyRunWidget(_report_with_orders({"DM": 1, "VS": 2}))
    assert widget._join_order_conflict_message() is None


def test_conflict_message_describes_shared_order():
    widget = DummyRunWidget(_report_with_orders({"DM": 2, "VS": 2}))
    message = widget._join_order_conflict_message()
    assert message is not None
    assert message.startswith("Cannot run:")
    assert "order 2" in message
    assert "DM" in message and "VS" in message


def test_refresh_disables_run_and_shows_hint_on_conflict():
    widget = DummyRunWidget(_report_with_orders({"DM": 2, "VS": 2}))
    widget._refresh_run_availability()
    assert widget.button.enabled is False
    assert widget.label_run_confirmation.text().startswith("Cannot run:")


def test_refresh_enables_and_clears_own_hint_when_resolved():
    widget = DummyRunWidget(_report_with_orders({"DM": 2, "VS": 2}))
    widget._refresh_run_availability()
    assert widget.button.enabled is False

    # Resolve the conflict and refresh: button re-enabled, stale hint cleared.
    widget.report.selected_forms["VS"].set_join_order(1)
    widget._refresh_run_availability()
    assert widget.button.enabled is True
    assert widget.label_run_confirmation.text() == ""


def test_refresh_preserves_unrelated_status_message():
    widget = DummyRunWidget(_report_with_orders({"DM": 1, "VS": 2}))
    widget.label_run_confirmation.setText("Preview generated successfully.")
    widget._refresh_run_availability()
    assert widget.button.enabled is True
    assert widget.label_run_confirmation.text() == "Preview generated successfully."


def test_report_validation_message_lists_actionable_core_issues():
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame({"Subject": ["001"], "Age": [41]}),
            "VS": pd.DataFrame({"Subject": ["001"], "Pulse": [90]}),
        }
    )
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    report.add_selected_form("VS")
    report.selected_forms["VS"].set_form_item_state("Pulse", selected=True)
    report.update_join_items("VS", [], 2, JoinHow.LEFT)
    report.set_common_item_state("Subject", selected=True)

    message = DummyRunWidget(report)._report_validation_message()

    assert message is not None
    assert message.startswith("Cannot run:")
    assert "VS" in message
    assert "at least one join item" in message
