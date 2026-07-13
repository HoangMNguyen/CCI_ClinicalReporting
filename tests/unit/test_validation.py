"""Regression tests for pre-execution report validation."""

import pandas as pd
import pytest

from clinical_reporting.models import JoinHow
from clinical_reporting.pipeline import ReportEngine
from clinical_reporting.report import CLReport
from clinical_reporting.validation import ReportValidationError


def _valid_two_form_report() -> CLReport:
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
    report.update_join_items("VS", ["Subject"], 2, JoinHow.LEFT)
    report.set_common_item_state("Subject", selected=True)
    return report


def _issue_codes(report: CLReport) -> set[str]:
    return {issue.code for issue in report.validate()}


def test_valid_report_has_no_issues():
    assert _valid_two_form_report().validate() == []


def test_missing_join_items_are_rejected_instead_of_silently_skipping_form():
    report = _valid_two_form_report()
    report.selected_forms["VS"].clear_join_items()

    assert "missing_join_items" in _issue_codes(report)
    with pytest.raises(ReportValidationError) as exc_info:
        report.create_report()

    assert any(issue.code == "missing_join_items" for issue in exc_info.value.issues)
    assert "VS" in str(exc_info.value)


def test_direct_engine_use_cannot_bypass_validation():
    report = _valid_two_form_report()
    report.selected_forms["VS"].set_join_how("Bogus join")

    with pytest.raises(ReportValidationError) as exc_info:
        ReportEngine(report).run()

    assert any(issue.code == "invalid_join_how" for issue in exc_info.value.issues)


def test_invalid_filter_operator_and_missing_item_are_reported_together():
    report = _valid_two_form_report()
    report.static_filter_items = [("DM.Missing", "approximately", "10")]

    codes = _issue_codes(report)
    assert "invalid_static_operator" in codes
    assert "missing_filter_item" in codes


def test_ambiguous_unqualified_filter_requires_form_name():
    report = _valid_two_form_report()
    report.data["DM"]["Status"] = ["Open"]
    report.data["VS"]["Status"] = ["Open"]
    for form_name in ("DM", "VS"):
        form = report.selected_forms[form_name]
        form.column_order.append("Status")
        form.set_form_item_state("Status", selected=True)
    report.static_filter_items = [("Status", "=", "Open")]

    assert "ambiguous_filter_item" in _issue_codes(report)


def test_duplicate_rename_targets_are_rejected():
    report = _valid_two_form_report()
    report.rename_dict = {"DM.Age": "Value", "VS.Pulse": "Value"}

    assert "duplicate_output_name" in _issue_codes(report)


def test_validation_issues_are_serialization_friendly():
    report = CLReport()
    payload = [issue.to_dict() for issue in report.validate()]

    assert {item["code"] for item in payload} == {"no_data", "no_selected_forms"}
    assert all(set(item) == {"code", "message", "field"} for item in payload)
