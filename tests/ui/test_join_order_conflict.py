"""Tests for join-order conflict detection and run guarding."""

import types

import pandas as pd
from tests.unit.fakes import FakeBanner

from clinical_reporting.models import CLForm, JoinHow
from clinical_reporting.report import CLReport
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.pages.preview_export import PreviewExportMixin
from clinical_reporting.validation import (
    ReportValidationError,
    ReportValidationIssue,
    duplicate_join_orders,
)


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


def _join_orders(report: CLReport) -> dict:
    return {name: form.get_join_order() for name, form in report.selected_forms.items()}


# ---------------------------------------------------------------------------
# Core detection


def test_duplicate_join_orders_flags_shared_orders():
    report = _report_with_orders({"DM": 1, "VS": 2, "AE": 2})
    assert duplicate_join_orders(_join_orders(report)) == {2: ["AE", "VS"]}


def test_duplicate_join_orders_empty_when_unique():
    report = _report_with_orders({"DM": 1, "VS": 2, "AE": 3})
    assert duplicate_join_orders(_join_orders(report)) == {}


def test_duplicate_join_orders_ignores_unset_orders():
    # Forms without a configured order default to "join last" and are not
    # treated as conflicting with each other.
    report = _report_with_orders({"DM": None, "VS": None, "AE": 1})
    assert duplicate_join_orders(_join_orders(report)) == {}


# ---------------------------------------------------------------------------
# Run guarding (mixin helpers, no QApplication required)


class _FakeButton:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, value):  # noqa: N802 (Qt naming convention)
        self.enabled = value


class DummyRunWidget(PreviewExportMixin, WidgetBaseMixin):
    """Compose just enough of the widget to exercise the run guard."""

    def __init__(self, report: CLReport, folder="out"):
        self.report = report
        self.output_folder_name = folder
        self.button = _FakeButton()
        self.label_run_confirmation = FakeBanner()
        self.banner_run_state = FakeBanner()
        self.ui = types.SimpleNamespace(
            pushButton_run=self.button, banner_run_state=self.banner_run_state
        )


def _dm_vs_report(vs_join_items=()):
    """DM, then VS joined on *vs_join_items*."""
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
    report.update_join_items("VS", list(vs_join_items), 2, JoinHow.LEFT)
    report.set_common_item_state("Subject", selected=True)
    return report


def test_refresh_disables_run_and_names_the_step_when_a_join_item_is_missing():
    widget = DummyRunWidget(_dm_vs_report())

    widget._refresh_run_availability()

    assert widget.button.enabled is False
    assert widget.banner_run_state.text() == "Cannot run: Fix Joins first."


def test_refresh_enables_run_when_missing_join_item_is_selected():
    report = _dm_vs_report()
    widget = DummyRunWidget(report)
    widget._refresh_run_availability()
    assert widget.button.enabled is False

    report.update_join_items("VS", ["Subject"], 2, JoinHow.LEFT)
    widget._refresh_run_availability()

    assert widget.button.enabled is True
    assert widget.banner_run_state.text() == ""


def test_refresh_disables_run_without_an_output_folder():
    widget = DummyRunWidget(_dm_vs_report(["Subject"]), folder=None)

    widget._refresh_run_availability()

    assert widget.button.enabled is False
    assert widget.banner_run_state.text() == ""


def test_refresh_preserves_unrelated_status_message():
    widget = DummyRunWidget(_dm_vs_report(["Subject"]))
    widget.label_run_confirmation.setText("Preview generated successfully.")
    widget._refresh_run_availability()
    assert widget.button.enabled is True
    assert widget.label_run_confirmation.text() == "Preview generated successfully."


def test_report_validation_message_names_the_steps_to_fix():
    message = DummyRunWidget(_dm_vs_report())._report_validation_message()

    assert message == "Cannot run: Fix Joins first."
    assert message.kind == "warning"
    assert message.details == (
        "Joins: Form 'VS' needs at least one join item because it is not first."
    )


def test_report_errors_are_warnings_when_invalid_and_errors_otherwise():
    widget = DummyRunWidget(CLReport())
    invalid = ReportValidationError(
        [ReportValidationIssue("no_forms", "Select at least one form before running.")]
    )

    widget._show_report_error("Error saving report", invalid, "traceback")
    shown = widget.label_run_confirmation.text()
    assert shown.startswith("Cannot run:") and shown.kind == "warning"

    widget._show_report_error("Error saving report", OSError("disk full"), "tb")
    shown = widget.label_run_confirmation.text()
    assert shown == "Error saving report: disk full"
    assert shown.kind == "error" and shown.details == "tb"


def test_running_without_a_report_is_a_warning():
    message = DummyRunWidget(None)._report_validation_message()

    assert message == "Cannot run: no report is loaded."
    assert message.kind == "warning"
