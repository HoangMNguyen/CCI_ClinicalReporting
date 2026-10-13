"""Coalesced items in a report: built with its data, saved with its setting."""

import json
from dataclasses import replace

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from clinical_reporting import coalescing, session
from clinical_reporting.coalescing import KEEP_EARLIER, CoalescedItem, Fill
from clinical_reporting.models import JoinHow
from clinical_reporting.stacking import StackedForm
from clinical_reporting.validation import (
    EXPORT_BLOCKING_ISSUE_CODES,
    ReportValidationError,
)

RACE = CoalescedItem("DM", "Race", "Race", (Fill("Race Other Specify", "=", "Other"),))
VISITS = StackedForm("VISITS", ("SV", "UV"))
VISIT_DATE = CoalescedItem("SV", "Visit Date", "Visit Date", (Fill("Visit Date Text"),))


def _data():
    return {
        "DM": pd.DataFrame(
            {
                "Subject": ["001", "002", "003"],
                "Site": ["A", "A", "B"],
                "Race": ["White", "Other", None],
                "Age": [41, 62, 35],
                "Race Other Specify": [None, "Hispanic", None],
            }
        ),
        "SV": pd.DataFrame(
            {
                "Subject": ["001", "002"],
                "Site": ["A", "A"],
                "Visit Date": ["2026-01-05", None],
                "Visit Date Text": [None, "early Feb"],
            }
        ),
        "UV": pd.DataFrame(
            {
                "Subject": ["003"],
                "Site": ["B"],
                "Visit Date": [None],
                "Visit Date Text": ["mid Mar"],
            }
        ),
    }


def test_a_coalesced_item_takes_the_place_of_its_items():
    report = session.new_report("DEMO01", _data())

    session.apply_coalesced_items(report, [RACE])

    assert_frame_equal(
        report.data["DM"],
        pd.DataFrame(
            {
                "Subject": ["001", "002", "003"],
                "Site": ["A", "A", "B"],
                "Race": ["White", "Hispanic", None],
                "Age": [41, 62, 35],
            }
        ),
    )
    assert "Race Other Specify" in report.loaded_data["DM"].columns
    assert report.coalesced_items == [RACE]


def test_a_stacked_form_is_coalesced_but_not_through_its_members():
    report = session.new_report("DEMO01", _data())
    session.apply_stacked_forms(report, [VISITS])

    session.apply_coalesced_items(report, [VISIT_DATE])

    # VISITS is stacked from SV as loaded, before SV's items are coalesced.
    assert report.data["SV"]["Visit Date"].tolist() == ["2026-01-05", "early Feb"]
    assert "Visit Date Text" in report.data["VISITS"].columns

    session.apply_coalesced_items(report, [replace(VISIT_DATE, form="VISITS")])

    assert report.data["VISITS"]["Visit Date"].tolist() == [
        "2026-01-05",
        "early Feb",
        "mid Mar",
    ]


def test_applying_coalesced_items_keeps_the_selections_that_still_exist():
    report = session.new_report("DEMO01", _data())
    report.add_selected_form("DM")
    for item in ("Race", "Age", "Race Other Specify"):
        report.selected_forms["DM"].set_form_item_state(item, selected=True)

    session.apply_coalesced_items(report, [RACE])

    assert report.get_selected_forms_list() == ["DM"]
    assert report.selected_forms["DM"].get_selected_form_items() == ["Race", "Age"]


def test_a_coalesced_item_can_become_a_common_item():
    data = _data()
    data["DM"] = data["DM"].assign(
        **{"Consent Date": ["2026-01-02", None, None], "Screen Date": [None] * 3}
    )
    consent = CoalescedItem("DM", "Visit Date", "Consent Date", (Fill("Screen Date"),))
    report = session.new_report("DEMO01", data)

    session.apply_coalesced_items(report, [consent])

    assert report.static_available_common_items == ["Subject", "Site", "Visit Date"]


def test_a_setting_brings_its_coalesced_items_before_its_selections():
    source = session.new_report("DEMO01", _data())
    session.apply_coalesced_items(source, [RACE])
    source.add_selected_form("DM")
    source.selected_forms["DM"].set_form_item_state("Race", selected=True)
    source.update_join_items("DM", [], 1, JoinHow.LEFT)
    settings = json.loads(json.dumps(source.settings_to_dict("race")))

    report = session.new_report("DEMO01", _data())
    missing = session.apply_saved_setting(report, settings)

    assert missing == {"forms": [], "items": []}
    assert report.coalesced_items == [RACE]
    assert report.selected_forms["DM"].get_selected_form_items() == ["Race"]
    assert settings["coalesced_items"] == [
        {
            "form": "DM",
            "name": "Race",
            "first": "Race",
            "fills": [
                {"item": "Race Other Specify", "operator": "=", "value": "Other"}
            ],
            "on_overlap": "refuse",
        }
    ]


def test_loading_a_setting_without_coalesced_items_removes_them():
    report = session.new_report("DEMO01", _data())
    session.apply_coalesced_items(report, [RACE])

    session.apply_saved_setting(
        report, session.new_report("DEMO01", _data()).settings_to_dict("old")
    )

    assert report.coalesced_items == []
    assert "Race Other Specify" in report.data["DM"].columns


def test_later_data_without_some_items_builds_from_the_rest_and_says_so():
    unit = CoalescedItem("LB", "Unit", "Unit", (Fill("Unit Other"),))
    settings = coalescing.to_settings(
        session.new_report("DEMO01", _data()).settings_to_dict("race"), [RACE, unit]
    )
    data = _data()
    data["DM"] = data["DM"].drop(columns="Race Other Specify")
    report = session.new_report("DEMO01", data)

    missing = session.apply_saved_setting(report, settings)

    assert missing == {"forms": ["LB"], "items": ["DM.Race Other Specify"]}
    assert list(report.data["DM"].columns) == ["Subject", "Site", "Race", "Age"]
    assert report.data["DM"]["Race"].fillna("<empty>").tolist() == [
        "White",
        "Other",
        "<empty>",
    ]


def _report_with_race(*items):
    """A report of DM's Race, coalesced by *items* (RACE when none given)."""
    report = session.new_report("DEMO01", _data())
    session.apply_coalesced_items(report, items or [RACE])
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Race", selected=True)
    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    report.update_selected_items_order_list()
    return report


def _conflicts(report):
    return [
        issue.message
        for issue in report.validate()
        if issue.code == "coalesced_item_conflict"
    ]


def test_later_overlaps_stop_the_report_until_the_earlier_value_is_kept():
    report = _report_with_race()
    later = _data()
    later["DM"].loc[0, "Race Other Specify"] = "Caucasian"

    session.replace_base_data(report, later, additional_keys=set())

    assert _conflicts(report) == [
        "Race in DM: 1 row has a value in Race Other Specify where Race already has "
        "one: 001 (White / Caucasian). Change a condition, or keep the earlier "
        "value, on Coalesced items."
    ]
    assert "coalesced_item_conflict" in EXPORT_BLOCKING_ISSUE_CODES
    with pytest.raises(ReportValidationError):
        report.create_report()

    session.apply_coalesced_items(report, [replace(RACE, on_overlap=KEEP_EARLIER)])

    assert _conflicts(report) == []
    assert report.create_report()["DM.Race"].fillna("<empty>").tolist() == [
        "White",
        "Hispanic",
        "<empty>",
    ]


def test_a_name_later_data_gives_another_item_stops_the_report():
    report = _report_with_race(replace(RACE, name="Race (all)"))
    later = _data()
    later["DM"]["Race (all)"] = ["x", "y", "z"]

    session.replace_base_data(report, later, additional_keys=set())

    assert _conflicts(report) == [
        "Race (all) in DM: DM now has its own Race (all). Rename the coalesced "
        "item on Coalesced items."
    ]
