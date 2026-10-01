"""Common items a later form doesn't join on (clinical_reporting.report_columns).

Such a form has its own values for the item, so they go out as ``FORM.item``
next to the plain column instead of pandas' ``_x``/``_y`` copies, and every
column list the report shows before running matches what the engine puts out.
"""

import pandas as pd
import pytest

from clinical_reporting import report_columns, session, steps
from clinical_reporting.models import JoinHow
from clinical_reporting.report import CLReport

# Made-up data: one demographics row per subject, then visit-level forms.
DATA = {
    "DM": pd.DataFrame(
        {
            "Subject": ["01", "02"],
            "Visit": ["Screening", "Screening"],
            "Sex": ["F", "M"],
        }
    ),
    "AE": pd.DataFrame(
        {
            "Subject": ["01", "01", "02"],
            "Visit": ["C1D1", "C1D8", "C1D1"],
            "Term": ["Nausea", "Rash", "Fatigue"],
        }
    ),
    "VS": pd.DataFrame(
        {
            "Subject": ["01", "01", "02"],
            "Visit": ["Screening", "C1D1", "Screening"],
            "Pulse": [70, 72, 80],
        }
    ),
    "LB": pd.DataFrame(
        {"Subject": ["01", "02"], "Visit": ["Screening", "C1D1"], "ALT": [21, 35]}
    ),
}
ITEMS = {"DM": "Sex", "AE": "Term", "VS": "Pulse", "LB": "ALT"}


def _report(joins, how=JoinHow.LEFT):
    """A report on DATA's forms in *joins* order: {form: join items}."""
    report = CLReport()
    report.set_data({name: DATA[name] for name in joins})
    report.set_common_item_state("Subject", selected=True)
    report.set_common_item_state("Visit", selected=True)
    for order, (name, keys) in enumerate(joins.items(), start=1):
        report.add_selected_form(name)
        report.selected_forms[name].set_form_item_state(ITEMS[name], selected=True)
        report.update_join_items(name, keys, order, how)
    report.update_selected_items_order_list()
    return report


def test_a_common_item_a_form_does_not_join_on_keeps_its_own_values():
    report = _report({"DM": [], "AE": ["Subject"]})

    out = report.create_report()

    assert list(out.columns) == ["Subject", "Visit", "DM.Sex", "AE.Visit", "AE.Term"]
    assert list(out["Visit"]) == ["Screening"] * 3
    assert list(out["AE.Visit"]) == ["C1D1", "C1D8", "C1D1"]


def test_a_later_form_can_join_on_that_common_item():
    report = _report({"DM": [], "AE": ["Subject"], "VS": ["Subject", "Visit"]})

    out = report.create_report()

    # VS matches the plain Visit, which keeps DM's values.
    assert list(out["VS.Pulse"]) == [70, 70, 80]


def test_forms_joining_on_every_common_item_are_unchanged():
    report = _report({"DM": [], "VS": ["Subject", "Visit"], "LB": ["Subject", "Visit"]})

    out = report.create_report()

    assert list(out.columns) == ["Subject", "Visit", "DM.Sex", "VS.Pulse", "LB.ALT"]
    assert report_columns.unjoined_common_items(report) == {}


@pytest.mark.parametrize("how", JoinHow.ALL)
@pytest.mark.parametrize(
    "joins",
    [
        {"DM": [], "AE": ["Subject"]},
        {"DM": [], "AE": ["Subject"], "VS": ["Subject", "Visit"]},
        {"VS": [], "DM": ["Subject"], "AE": ["Subject", "Visit"], "LB": ["Subject"]},
    ],
)
def test_the_listed_columns_are_the_columns_the_engine_puts_out(joins, how):
    report = _report(joins, how)

    out = report.create_report()

    assert list(out.columns) == report_columns.output_identifiers(report)
    assert list(out.columns) == report.get_selected_items_order_list()
    assert not [name for name in out.columns if name.endswith(("_x", "_y"))]


def test_the_unjoined_column_can_be_renamed_and_filtered():
    report = _report({"DM": [], "AE": ["Subject"]})
    report.set_rename_item("AE.Visit", "AE visit")
    report.add_dynamic_filter_item("AE.Visit", "!=", "Visit")
    report.add_static_filter_item("AE.Visit", "=", "C1D1")

    assert report.validate() == []
    out = report.create_report()

    assert list(out["AE visit"]) == ["C1D1", "C1D1"]


def test_renaming_it_to_the_plain_name_is_a_duplicate_output_name():
    report = _report({"DM": [], "AE": ["Subject"]})
    report.set_rename_item("AE.Visit", "Visit")

    assert "duplicate_output_name" in [issue.code for issue in report.validate()]


def test_a_rename_is_parked_while_the_form_joins_on_the_item():
    report = _report({"DM": [], "AE": ["Subject"]})
    report.set_rename_item("AE.Visit", "AE visit")

    report.update_join_items("AE", ["Subject", "Visit"], 2, JoinHow.LEFT)
    assert report.get_rename_dict() == {}
    assert report.validate() == []

    report.update_join_items("AE", ["Subject"], 2, JoinHow.LEFT)
    assert report.get_rename_dict() == {"AE.Visit": "AE visit"}


def test_a_form_without_join_items_yet_lists_no_unjoined_items():
    report = _report({"DM": [], "AE": ["Subject"]})
    report.update_join_items("AE", [], 2, JoinHow.LEFT)

    assert report_columns.unjoined_common_items(report) == {}
    assert "missing_join_items" in [issue.code for issue in report.validate()]


def test_a_customized_order_takes_in_the_new_column_next_to_its_form():
    report = _report({"DM": [], "AE": ["Subject", "Visit"]})
    report.set_selected_items_order_list(["AE.Term", "Subject", "Visit", "DM.Sex"])

    report.update_join_items("AE", ["Subject"], 2, JoinHow.LEFT)
    report.update_selected_items_order_list()

    assert report.get_selected_items_order_list() == [
        "AE.Visit",
        "AE.Term",
        "Subject",
        "Visit",
        "DM.Sex",
    ]


def test_settings_saved_before_the_change_still_run():
    old = _report({"DM": [], "AE": ["Subject"]}).settings_to_dict("old")
    old["selected_items_order_list"] = ["Subject", "Visit", "DM.Sex", "AE.Term"]
    old["order_list_customized"] = True

    report = CLReport()
    report.set_data({"DM": DATA["DM"], "AE": DATA["AE"]})
    report.load_setting_from_dict(old)
    report.reconcile_with_current_data()
    report.update_selected_items_order_list()

    out = report.create_report()
    # AE.Visit goes where it would by default: after DM's columns, before AE's.
    assert list(out.columns) == ["Subject", "Visit", "DM.Sex", "AE.Visit", "AE.Term"]


def test_the_joins_page_says_which_columns_hold_a_forms_own_values():
    report = _report({"DM": [], "AE": ["Subject"], "VS": ["Subject", "Visit"]})

    message = steps.joins_message(report)

    assert message.kind == "info"
    assert "AE.Visit" in message and "VS.Visit" not in message
    assert message.details == "AE.Visit"  # The whole list, when it's shortened.


def test_forms_without_a_valid_join_order_go_last():
    report = _report({"DM": [], "AE": ["Subject"], "VS": ["Subject"]})
    report.selected_forms["DM"].set_join_order(None)

    assert report_columns.forms_in_join_order(report.selected_forms) == [
        "AE",
        "VS",
        "DM",
    ]


def test_reloading_the_data_keeps_where_the_user_put_those_columns():
    report = _report({"DM": [], "AE": ["Subject"]})
    report.set_selected_items_order_list(
        ["AE.Visit", "Subject", "Visit", "DM.Sex", "AE.Term"]
    )
    report.add_static_filter_item("AE.Visit", "!=", "C1D8")

    # As after a new cut-off date: the same forms, read again.
    session.replace_base_data(report, {"DM": DATA["DM"], "AE": DATA["AE"]}, [])

    assert report.get_selected_items_order_list() == [
        "AE.Visit",
        "Subject",
        "Visit",
        "DM.Sex",
        "AE.Term",
    ]
    assert report.get_static_filter_items() == [("AE.Visit", "!=", "C1D8")]


def test_a_filter_on_a_plain_common_item_filters_every_forms_copy():
    """As before the FORM.item names: before joining, on every form that has it.

    To filter only one form's own copy, filter FORM.item.
    """
    report = _report({"DM": [], "AE": ["Subject"]})
    report.add_static_filter_item("Visit", "!=", "C1D8")

    out = report.create_report()

    assert list(out["AE.Visit"]) == ["C1D1", "C1D1"]


def test_a_setting_without_join_items_reads_as_none_chosen():
    settings = _report({"DM": [], "AE": ["Subject"]}).settings_to_dict("old")
    settings["selected_forms"]["AE"]["join_items"] = None
    report = CLReport()
    report.set_data({"DM": DATA["DM"], "AE": DATA["AE"]})

    report.load_setting_from_dict(settings)

    assert report.selected_forms["AE"].get_join_items() == []
    assert "missing_join_items" in [issue.code for issue in report.validate()]


def _wide_report(ae_items):
    """DM and AE with three common items; AE joins on all of them."""
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame(
                {"Subject": ["01"], "Site": ["A"], "Visit": ["V1"], "Sex": ["F"]}
            ),
            "AE": pd.DataFrame(
                {
                    "Subject": ["01"],
                    "Site": ["A"],
                    "Visit": ["V2"],
                    "Term": ["Rash"],
                    "Grade": ["1"],
                    "Start": ["2026-01-02"],
                    "End": ["2026-01-03"],
                }
            ),
        }
    )
    for item in ("Subject", "Site", "Visit"):
        report.set_common_item_state(item, selected=True)
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Sex", selected=True)
    report.add_selected_form("AE")
    for item in ae_items:
        report.selected_forms["AE"].set_form_item_state(item, selected=True)
    report.update_join_list(
        [
            ("DM", [], 1, JoinHow.LEFT),
            ("AE", ["Subject", "Site", "Visit"], 2, JoinHow.LEFT),
        ]
    )
    return report


def test_a_forms_new_common_item_copies_go_next_to_its_columns():
    report = _wide_report(["Term"])
    report.set_selected_items_order_list(
        ["AE.Term", "Subject", "Site", "Visit", "DM.Sex"]
    )

    report.update_join_items("AE", ["Subject"], 2, JoinHow.LEFT)
    report.update_selected_items_order_list()

    assert report.get_selected_items_order_list() == [
        "AE.Site",
        "AE.Visit",
        "AE.Term",
        "Subject",
        "Site",
        "Visit",
        "DM.Sex",
    ]


def test_form_items_selected_together_stay_together_in_a_customized_order():
    report = _wide_report(["Term", "End"])
    report.set_selected_items_order_list(
        ["AE.Term", "Subject", "Site", "Visit", "DM.Sex", "AE.End"]
    )

    report.selected_forms["AE"].set_form_item_state("Grade", selected=True)
    report.selected_forms["AE"].set_form_item_state("Start", selected=True)
    report.update_selected_items_order_list()

    assert report.get_selected_items_order_list() == [
        "AE.Term",
        "AE.Grade",
        "AE.Start",
        "Subject",
        "Site",
        "Visit",
        "DM.Sex",
        "AE.End",
    ]
