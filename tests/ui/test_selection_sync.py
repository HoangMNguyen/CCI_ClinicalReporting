"""Renames/filters for deselected forms and items are parked, not validated or saved."""

import json

import pandas as pd
import pytest

from clinical_reporting.models import JoinHow
from clinical_reporting.report import CLReport
from clinical_reporting.ui.base import WidgetBaseMixin


def _issue_codes(report):
    return {issue.code for issue in report.validate()}


@pytest.fixture
def report():
    """DM + AE joined on Subject, with a rename and filters on each form."""
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame({"Subject": ["001", "002"], "AGE": [30, 40]}),
            "AE": pd.DataFrame(
                {"Subject": ["001", "002"], "TERM": ["Headache", "Nausea"]}
            ),
        }
    )
    report.set_common_item_state("Subject", selected=True)
    report.add_all_selected_forms()
    report.selected_forms["DM"].set_form_item_state("AGE", selected=True)
    report.selected_forms["AE"].set_form_item_state("TERM", selected=True)
    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    report.update_join_items("AE", ["Subject"], 2, JoinHow.LEFT)
    report.set_rename_item("DM.AGE", "Age")
    report.set_rename_item("AE.TERM", "Adverse Event")
    report.set_rename_item("Subject", "ID")
    report.static_filter_items = [("DM.AGE", ">", "0"), ("AE.TERM", "!=", "x")]
    report.dynamic_filter_items = [
        ("DM.AGE", "!=", "AE.TERM"),
        ("Subject", "=", "Subject"),
    ]
    report.sync_with_selection()
    assert report.validate() == []
    return report


def test_removing_form_parks_its_renames_and_filters(report):
    report.add_available_form("AE")
    report.sync_with_selection()

    assert report.rename_dict == {"DM.AGE": "Age", "Subject": "ID"}
    assert report.static_filter_items == [("DM.AGE", ">", "0")]
    # A dynamic filter is parked when either operand is deselected.
    assert report.dynamic_filter_items == [("Subject", "=", "Subject")]
    assert report.validate() == []

    result = report.create_report()
    assert list(result.columns) == ["ID", "Age"]


def test_readding_form_restores_parked_renames_and_filters(report):
    report.add_available_form("AE")
    report.sync_with_selection()

    report.add_selected_form("AE")
    report.update_join_items("AE", ["Subject"], 2, JoinHow.LEFT)
    report.selected_forms["AE"].set_form_item_state("TERM", selected=True)
    report.sync_with_selection()

    assert report.rename_dict == {
        "DM.AGE": "Age",
        "AE.TERM": "Adverse Event",
        "Subject": "ID",
    }
    assert ("AE.TERM", "!=", "x") in report.static_filter_items
    assert ("DM.AGE", "!=", "AE.TERM") in report.dynamic_filter_items
    assert report.validate() == []


def test_deselecting_form_item_parks_and_restores_its_rename(report):
    report.selected_forms["AE"].set_form_item_state("TERM", selected=False)
    report.sync_with_selection()
    assert "AE.TERM" not in report.rename_dict
    assert "unknown_rename_item" not in _issue_codes(report)

    report.selected_forms["AE"].set_form_item_state("TERM", selected=True)
    report.sync_with_selection()
    assert report.rename_dict["AE.TERM"] == "Adverse Event"


def test_deselecting_common_item_parks_and_restores_its_rename():
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame({"Subject": ["001"], "Visit": ["V1"], "AGE": [30]}),
            "AE": pd.DataFrame({"Subject": ["001"], "Visit": ["V1"], "TERM": ["x"]}),
        }
    )
    report.set_common_item_state("Subject", selected=True)
    report.set_common_item_state("Visit", selected=True)
    report.set_rename_item("Visit", "Visit Name")

    report.set_common_item_state("Visit", selected=False)
    report.sync_with_selection()
    assert report.rename_dict == {}

    report.set_common_item_state("Visit", selected=True)
    report.sync_with_selection()
    assert report.rename_dict == {"Visit": "Visit Name"}


def test_active_rename_wins_over_parked_copy(report):
    report.selected_forms["AE"].set_form_item_state("TERM", selected=False)
    report.sync_with_selection()

    report.selected_forms["AE"].set_form_item_state("TERM", selected=True)
    report.set_rename_item("AE.TERM", "Event Term")
    report.sync_with_selection()

    assert report.rename_dict["AE.TERM"] == "Event Term"
    report.selected_forms["AE"].set_form_item_state("TERM", selected=False)
    report.sync_with_selection()
    report.selected_forms["AE"].set_form_item_state("TERM", selected=True)
    report.sync_with_selection()
    assert report.rename_dict["AE.TERM"] == "Event Term"


def test_the_order_list_is_pruned(report):
    report.set_selected_items_order_list(["AE.TERM", "Subject", "DM.AGE"])

    report.add_available_form("AE")
    report.sync_with_selection()

    assert report.selected_items_order_list == ["Subject", "DM.AGE"]
    assert "unknown_order_item" not in _issue_codes(report)


def test_saved_setting_excludes_removed_form_entries(report, tmp_path):
    report.add_available_form("AE")
    # No explicit sync: saving must never persist entries for removed forms.
    path = tmp_path / "setting.json"
    report.save_setting_to_json(str(path), setting_name="no AE")

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["rename_dict"] == {"DM.AGE": "Age", "Subject": "ID"}
    assert saved["static_filter_items"] == [["DM.AGE", ">", "0"]]
    assert saved["dynamic_filter_items"] == [["Subject", "=", "Subject"]]
    assert "AE" not in saved["selected_forms"]


def test_loading_a_setting_discards_parked_entries(report):
    report.add_available_form("AE")
    report.sync_with_selection()

    report.load_setting_from_dict({"selected_forms": {}, "rename_dict": {}})
    report.reconcile_with_current_data()
    report.add_selected_form("AE")
    report.selected_forms["AE"].set_form_item_state("TERM", selected=True)
    report.sync_with_selection()

    assert "AE.TERM" not in report.rename_dict
    assert report.static_filter_items == []


def test_malformed_filters_stay_active_for_validation():
    report = CLReport()
    report.static_filter_items = [("only-two", "=")]
    report.sync_with_selection()
    assert report.static_filter_items == [("only-two", "=")]
    assert "invalid_static_filter" in _issue_codes(report)


class _SyncHost(WidgetBaseMixin):
    """Host with the item-dependent table refreshes stubbed out."""

    def __init__(self, report):
        self.report = report

    def update_order_rename_table(self):
        self.rename_seen_by_table = dict(self.report.rename_dict)

    def update_static_filter_table(self):
        pass

    def update_dynamic_filter_table(self):
        pass


def test_item_dependent_refresh_parks_stale_renames_before_tables(report):
    host = _SyncHost(report)
    report.add_available_form("AE")

    host.update_items_dependent_ui()

    assert "AE.TERM" not in host.rename_seen_by_table
    assert "unknown_rename_item" not in _issue_codes(report)
