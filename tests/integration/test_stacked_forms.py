"""Stacked forms in a report: built with its data, saved with its setting."""

import json

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from clinical_reporting import session, steps
from clinical_reporting.models import JoinHow
from clinical_reporting.stacking import Match, StackedForm
from clinical_reporting.validation import (
    JOIN_BLOCKING_ISSUE_CODES,
    ReportValidationError,
    report_issues_message,
)

VISITS = StackedForm(
    "VISITS",
    ("SV", "DSSVLTFU"),
    (Match("Visit Name", {"SV": "Event Group Name", "DSSVLTFU": "Event Label"}),),
)


def _data():
    return {
        "DM": pd.DataFrame(
            {"Subject": ["001", "002", "003"], "Site": ["A", "A", "B"], "Age": [41, 62, 35]}
        ),
        "SV": pd.DataFrame(
            {
                "Subject": ["001", "002"],
                "Site": ["A", "A"],
                "Event Group Name": ["Screening", "Week 1"],
                "Visit Status": ["Done", "Missed"],
            }
        ),
        "DSSVLTFU": pd.DataFrame(
            {"Subject": ["003"], "Site": ["B"], "Event Label": ["Follow-up"]}
        ),
    }


def _report_with_visits():
    report = session.new_report("DEMO01", _data())
    session.apply_stacked_forms(report, [VISITS])
    return report


def test_a_stacked_form_is_a_form_like_any_other():
    report = _report_with_visits()

    assert report.get_available_forms_list() == ["DM", "SV", "DSSVLTFU", "VISITS"]
    assert set(report.loaded_data) == {"DM", "SV", "DSSVLTFU"}
    assert_frame_equal(
        report.data["VISITS"],
        pd.DataFrame(
            {
                "Subject": ["001", "002", "003"],
                "Site": ["A", "A", "B"],
                "Visit Name": ["Screening", "Week 1", "Follow-up"],
            }
        ),
    )


def test_a_stacked_form_never_takes_away_a_common_item():
    report = session.new_report("DEMO01", _data())
    before = list(report.static_available_common_items)

    session.apply_stacked_forms(report, [VISITS])

    assert before == ["Subject", "Site"]
    assert report.static_available_common_items == ["Subject", "Site"]


def test_applying_stacked_forms_keeps_the_selections():
    report = session.new_report("DEMO01", _data())
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)

    session.apply_stacked_forms(report, [VISITS])

    assert report.get_selected_forms_list() == ["DM"]
    assert report.selected_forms["DM"].get_selected_form_items() == ["Age"]
    assert report.get_selected_common_items() == ["Subject"]


def test_the_report_runs_with_a_stacked_form_joined_filtered_and_renamed():
    report = _report_with_visits()
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    report.add_selected_form("VISITS")
    report.selected_forms["VISITS"].set_form_item_state("Visit Name", selected=True)
    report.update_join_items("VISITS", ["Subject"], 2, JoinHow.INNER)
    report.update_selected_items_order_list()
    report.add_static_filter_item("VISITS.Visit Name", "!=", "Week 1")
    report.set_rename_item("VISITS.Visit Name", "Visit")

    result = report.create_report()

    assert_frame_equal(
        result.reset_index(drop=True),
        pd.DataFrame(
            {
                "Subject": ["001", "003"],
                "DM.Age": [41, 35],
                "Visit": ["Screening", "Follow-up"],
            }
        ),
    )


def test_stacked_forms_are_rebuilt_with_the_data():
    report = _report_with_visits()
    cut = {**_data(), "SV": _data()["SV"].head(1)}

    session.replace_base_data(report, cut, additional_keys=set())

    assert report.data["VISITS"]["Subject"].tolist() == ["001", "003"]


def test_a_setting_brings_its_stacked_forms_before_its_selections():
    source = _report_with_visits()
    source.add_selected_form("VISITS")
    source.selected_forms["VISITS"].set_form_item_state("Visit Name", selected=True)
    source.update_join_items("VISITS", [], 1, JoinHow.LEFT)
    settings = json.loads(json.dumps(source.settings_to_dict("visits")))

    report = session.new_report("DEMO01", _data())
    missing = report.apply_config(settings)

    assert missing == {"forms": [], "items": []}
    assert report.stacked_forms == [VISITS]
    assert report.get_selected_forms_list() == ["VISITS"]
    assert report.selected_forms["VISITS"].get_selected_form_items() == ["Visit Name"]
    assert settings["stacked_forms"] == [
        {
            "name": "VISITS",
            "members": ["SV", "DSSVLTFU"],
            "matches": [
                {
                    "name": "Visit Name",
                    "items": {"SV": "Event Group Name", "DSSVLTFU": "Event Label"},
                }
            ],
        }
    ]


def test_a_setting_without_stacked_forms_saves_as_before():
    report = _report_with_visits()
    session.apply_stacked_forms(report, [])
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    report.update_selected_items_order_list()

    saved = report.settings_to_dict("monthly")

    expected = {
        "study_name": "DEMO01",
        "setting_name": "monthly",
        "selected_forms": {
            "DM": {
                "name": "DM",
                "selected_form_items": ["Age"],
                "join_items": [],
                "join_order": 1,
                "join_how": "Left join",
            }
        },
        "selected_common_items": ["Subject"],
        "new_items": [],
        "rename_dict": {},
        "static_filter_items": [],
        "dynamic_filter_items": [],
        "selected_items_order_list": ["Subject", "DM.Age"],
        "order_list_customized": False,
    }
    assert json.dumps(saved) == json.dumps(expected)


def test_loading_a_setting_without_stacked_forms_removes_them():
    report = _report_with_visits()

    report.apply_config(session.new_report("DEMO01", _data()).settings_to_dict("old"))

    assert report.stacked_forms == []
    assert set(report.data) == {"DM", "SV", "DSSVLTFU"}


def test_missing_members_and_matched_items_are_reported():
    source = _report_with_visits()
    with_lb = StackedForm("VISITS", ("SV", "DSSVLTFU", "LB"), VISITS.matches)
    session.apply_stacked_forms(source, [with_lb])
    settings = source.settings_to_dict("visits")
    data = _data()
    data["DSSVLTFU"] = data["DSSVLTFU"].rename(columns={"Event Label": "Label"})

    report = session.new_report("DEMO01", data)
    missing = report.apply_config(settings)

    assert missing == {"forms": ["LB"], "items": ["DSSVLTFU.Event Label"]}
    assert report.data["VISITS"]["Visit Name"].isna().tolist() == [False, False, True]
    message = steps.stacked_missing_message(report)
    assert message.kind == "warning"
    assert message == (
        "VISITS is built without LB, which isn't loaded. In VISITS, DSSVLTFU has no "
        "Event Label: the matched item is blank on its rows."
    )
    assert steps.step_statuses(report)[steps.STACKED] == steps.StepStatus(
        steps.WARNING, tip=message
    )


def test_a_stacked_form_named_like_a_loaded_form_stops_the_report():
    report = session.new_report("DEMO01", _data())
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.update_join_items("DM", [], 1, JoinHow.LEFT)

    session.apply_stacked_forms(report, [StackedForm("DM", ("SV", "DSSVLTFU"))])

    message = "DM is both a stacked form and a loaded form. Rename the stacked form on Stacked forms."
    assert [(i.code, i.message, i.field) for i in report.validate()] == [
        ("stacked_form_name_clash", message, "stacked_forms")
    ]
    assert report_issues_message(report, JOIN_BLOCKING_ISSUE_CODES) is not None
    assert steps.step_statuses(report)[steps.STACKED] == steps.StepStatus(
        steps.ERROR, tip=message
    )
    with pytest.raises(ReportValidationError):
        report.create_report()


# Data that changes after Apply can make a saved stacked form ambiguous. Each
# way the data is set again (a saved setting, a new cut-off, additional
# inputs) must then stop the report instead of quietly taking other values.

CONFLICT = "stacked_form_conflict"


def _conflicts(report):
    return [
        (issue.code, issue.message, issue.field)
        for issue in report.validate()
        if issue.code == CONFLICT
    ]


def _runnable(report):
    """*report* with DM's Age selected, so it runs unless something stops it."""
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    return report


def test_a_setting_whose_match_is_now_an_item_every_member_has_stops_the_report():
    source = _report_with_visits()
    source.add_selected_form("VISITS")
    source.selected_forms["VISITS"].set_form_item_state("Visit Name", selected=True)
    source.update_join_items("VISITS", [], 1, JoinHow.LEFT)
    settings = json.loads(json.dumps(source.settings_to_dict("visits")))
    data = _data()
    for member in ("SV", "DSSVLTFU"):
        data[member] = data[member].assign(**{"Visit Name": "new"})

    report = session.new_report("DEMO01", data)
    report.apply_config(settings)

    message = (
        "VISITS: every member now has an item called Visit Name, also the name of a "
        "match. Rename the match on Stacked forms."
    )
    assert _conflicts(report) == [(CONFLICT, message, "stacked_forms")]
    # The selections stay for once the match is renamed.
    assert report.selected_forms["VISITS"].get_selected_form_items() == ["Visit Name"]
    assert report_issues_message(report, JOIN_BLOCKING_ISSUE_CODES) is not None
    assert steps.step_statuses(report)[steps.STACKED] == steps.StepStatus(
        steps.ERROR, tip=message
    )
    conflict = steps.stacked_conflict_message(report)
    assert conflict == f"{message} The report can't be exported until this is fixed."
    assert conflict.kind == "error"
    with pytest.raises(ReportValidationError):
        report.create_report()


def test_a_member_with_two_items_of_one_match_after_a_reload_stops_the_report():
    report = _runnable(_report_with_visits())
    report.create_report()
    reloaded = _data()
    reloaded["SV"] = reloaded["SV"].assign(**{"Event Label": ["x", "y"]})

    session.replace_base_data(report, reloaded, additional_keys=set())

    message = (
        "VISITS: SV now has both Event Group Name and Event Label, which the match "
        "Visit Name lines up. Unmatch it and match again on Stacked forms."
    )
    assert _conflicts(report) == [(CONFLICT, message, "stacked_forms")]
    with pytest.raises(ReportValidationError):
        report.create_report()


def test_an_additional_member_with_two_items_of_one_match_stops_the_report():
    labs = StackedForm(
        "LABS",
        ("LB", "LAB"),
        (Match("Date", {"LB": "Event Date", "LAB": "Collection Date"}),),
    )
    base = {
        "DM": _data()["DM"],
        "LB": pd.DataFrame(
            {"Subject": ["001"], "Site": ["A"], "Event Date": ["2026-01-05"]}
        ),
    }
    lab = pd.DataFrame(
        {"Subject": ["002"], "Site": ["A"], "Collection Date": ["2026-01-06"]}
    )
    report = session.new_report("DEMO01", {**base, "LAB": lab})
    session.apply_stacked_forms(report, [labs])
    assert _conflicts(report) == []

    # Additional input's Apply sets the data again, the file now with both dates.
    report.set_data({**base, "LAB": lab.assign(**{"Event Date": ["2026-01-07"]})})

    message = (
        "LABS: LAB now has both Event Date and Collection Date, which the match Date "
        "lines up. Unmatch it and match again on Stacked forms."
    )
    assert _conflicts(report) == [(CONFLICT, message, "stacked_forms")]
    assert report_issues_message(report, JOIN_BLOCKING_ISSUE_CODES) is not None


def test_a_member_that_now_gives_another_of_the_matchs_items_is_warned_about():
    settings = _report_with_visits().settings_to_dict("visits")
    data = _data()
    data["DSSVLTFU"] = data["DSSVLTFU"].rename(
        columns={"Event Label": "Event Group Name"}
    )

    report = session.new_report("DEMO01", data)
    missing = report.apply_config(settings)

    assert missing == {"forms": [], "items": ["DSSVLTFU.Event Label"]}
    assert report.data["VISITS"]["Visit Name"].tolist() == [
        "Screening",
        "Week 1",
        "Follow-up",
    ]
    message = steps.stacked_missing_message(report)
    assert message == (
        "In VISITS, DSSVLTFU has no Event Label: Visit Name takes its Event Group "
        "Name instead."
    )
    assert message.kind == "warning"
    assert _conflicts(report) == []
    assert steps.step_statuses(report)[steps.STACKED] == steps.StepStatus(
        steps.WARNING, tip=message
    )
