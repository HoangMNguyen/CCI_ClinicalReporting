"""Tests for preserving the input file/form column order.

Columns must keep the order they have in the loaded files instead of being
sorted alphabetically: common items stay leftmost (in first-form order), each
form's items follow in file order grouped by merge (join) order, and only the
Order & rename page may change the arrangement.
"""

import json

import pandas as pd
import pytest
from tests.unit.fakes import DummyTable

from clinical_reporting import session
from clinical_reporting.models import CLForm, JoinHow
from clinical_reporting.report import CLReport
from clinical_reporting.settings_store import write_settings_json


@pytest.fixture
def report_with_data():
    # Column names are deliberately not alphabetical.
    report = CLReport()
    report.set_data(
        {
            "DM": DummyTable(["Subject", "Visit", "Weight", "Age"]),
            "VS": DummyTable(["Visit", "Subject", "Pulse", "BP"]),
        }
    )
    return report


def test_common_items_keep_first_form_column_order(report_with_data):
    # "Subject" precedes "Visit" in the first form even though "Visit" would
    # come later alphabetically than e.g. "Subject"; no sorting is applied.
    assert report_with_data.static_available_common_items == ["Subject", "Visit"]
    assert report_with_data.get_available_common_items() == ["Subject", "Visit"]


def test_common_item_selection_order_does_not_change_column_order(report_with_data):
    report = report_with_data

    # Select in reverse file order; the lists stay in file order.
    report.set_common_item_state("Visit", selected=True)
    report.set_common_item_state("Subject", selected=True)
    assert report.get_selected_common_items() == ["Subject", "Visit"]

    # Deselecting returns the item to its file-order slot, not the end.
    report.set_common_item_state("Subject", selected=False)
    report.set_common_item_state("Visit", selected=False)
    assert report.get_available_common_items() == ["Subject", "Visit"]


def test_form_items_keep_file_order_regardless_of_selection_order(report_with_data):
    report = report_with_data
    report.add_selected_form("DM")
    form = report.selected_forms["DM"]

    assert form.get_available_form_items() == ["Weight", "Age"]

    form.set_form_item_state("Age", selected=True)
    form.set_form_item_state("Weight", selected=True)
    assert form.get_selected_form_items() == ["Weight", "Age"]

    form.set_form_item_state("Weight", selected=False)
    assert form.get_available_form_items() == ["Weight"]
    assert form.get_selected_form_items() == ["Age"]


def test_order_list_groups_forms_by_merge_order(report_with_data):
    report = report_with_data
    report.set_common_item_state("Subject", selected=True)
    report.add_selected_form("DM")
    report.add_selected_form("VS")

    # VS merges first even though DM was selected first.
    report.update_join_items("VS", [], 1, JoinHow.LEFT)
    report.update_join_items("DM", ["Subject"], 2, JoinHow.LEFT)

    for item in ["Age", "Weight"]:
        report.selected_forms["DM"].set_form_item_state(item, selected=True)
    for item in ["BP", "Pulse"]:
        report.selected_forms["VS"].set_form_item_state(item, selected=True)

    order = report.update_selected_items_order_list()
    assert order == ["Subject", "VS.Pulse", "VS.BP", "DM.Weight", "DM.Age"]


def test_new_common_item_is_inserted_left_of_form_items(report_with_data):
    report = report_with_data
    report.set_common_item_state("Subject", selected=True)
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Weight", selected=True)
    report.update_selected_items_order_list()
    assert report.get_selected_items_order_list() == ["Subject", "DM.Weight"]

    # A common item selected after form items still lands with the common
    # items on the left instead of being appended at the end.
    report.set_common_item_state("Visit", selected=True)
    order = report.update_selected_items_order_list()
    assert order == ["Subject", "Visit", "DM.Weight"]


def test_changing_join_order_regroups_default_order(report_with_data):
    report = report_with_data
    report.set_common_item_state("Subject", selected=True)
    report.add_selected_form("DM")
    report.add_selected_form("VS")
    report.selected_forms["DM"].set_form_item_state("Weight", selected=True)
    report.selected_forms["VS"].set_form_item_state("Pulse", selected=True)

    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    report.update_join_items("VS", ["Subject"], 2, JoinHow.LEFT)
    assert report.update_selected_items_order_list() == [
        "Subject",
        "DM.Weight",
        "VS.Pulse",
    ]

    # Swapping the join order re-derives the default: VS now merges first.
    report.update_join_items("VS", [], 1, JoinHow.LEFT)
    report.update_join_items("DM", ["Subject"], 2, JoinHow.LEFT)
    assert report.update_selected_items_order_list() == [
        "Subject",
        "VS.Pulse",
        "DM.Weight",
    ]


def test_manual_order_survives_join_order_changes(report_with_data):
    report = report_with_data
    report.set_common_item_state("Subject", selected=True)
    report.add_selected_form("DM")
    report.add_selected_form("VS")
    report.selected_forms["DM"].set_form_item_state("Weight", selected=True)
    report.selected_forms["VS"].set_form_item_state("Pulse", selected=True)
    report.update_selected_items_order_list()

    # User rearranges on the Order & rename page; join order changes mustn't undo it.
    report.set_selected_items_order_list(["DM.Weight", "Subject", "VS.Pulse"])
    report.update_join_items("VS", [], 1, JoinHow.LEFT)
    report.update_join_items("DM", ["Subject"], 2, JoinHow.LEFT)
    assert report.update_selected_items_order_list() == [
        "DM.Weight",
        "Subject",
        "VS.Pulse",
    ]


def test_customized_flag_roundtrips_through_settings(tmp_path, report_with_data):
    report = report_with_data
    report.set_common_item_state("Subject", selected=True)
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Weight", selected=True)
    report.set_selected_items_order_list(["DM.Weight", "Subject"])

    path = tmp_path / "setting.json"
    write_settings_json(path, report.settings_to_dict())

    loaded = CLReport()
    loaded.load_setting_from_dict(json.loads(path.read_text(encoding="utf-8")))
    assert loaded.order_list_customized is True
    assert loaded.get_selected_items_order_list() == ["DM.Weight", "Subject"]


def test_legacy_settings_with_saved_order_replay_exactly(report_with_data):
    # Settings from before the flag existed: a saved order is kept verbatim.
    report = report_with_data
    report.load_setting_from_dict(
        {
            "selected_forms": {"DM": {"name": "DM", "selected_form_items": ["Weight"]}},
            "selected_common_items": ["Subject"],
            "selected_items_order_list": ["DM.Weight", "Subject"],
        }
    )
    assert report.order_list_customized is True
    assert report.update_selected_items_order_list() == ["DM.Weight", "Subject"]


def _report_from_setting(order_settings):
    """A DM report (VS loaded, not selected) from a setting with *order_settings*."""
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame({"Subject": ["001"], "Weight": [70], "Age": [30]}),
            "VS": pd.DataFrame({"Subject": ["001"], "Pulse": [60]}),
        }
    )
    session.apply_saved_setting(
        report,
        {
            "selected_forms": {
                "DM": {
                    "name": "DM",
                    "selected_form_items": ["Weight", "Age"],
                    "join_items": [],
                    "join_order": 1,
                    "join_how": "Left join",
                }
            },
            "selected_common_items": ["Subject"],
            **order_settings,
        },
    )
    return report


def test_a_customized_order_wins_over_a_stale_order_list():
    report = _report_from_setting(
        {
            "order_list": ["Subject", "DM.Weight", "DM.Age"],
            "selected_items_order_list": ["DM.Age", "Subject", "DM.Weight"],
            "order_list_customized": True,
        }
    )

    assert list(report.create_report().columns) == ["DM.Age", "Subject", "DM.Weight"]


def test_an_order_list_alone_is_read_as_the_custom_order():
    report = _report_from_setting({"order_list": ["DM.Age", "Subject", "DM.Weight"]})

    assert report.get_selected_items_order_list() == ["DM.Age", "Subject", "DM.Weight"]
    assert report.order_list_customized is True
    assert list(report.create_report().columns) == ["DM.Age", "Subject", "DM.Weight"]


def test_an_order_list_beats_an_order_that_was_never_customized():
    # A setting re-saved since the flag existed: the default order, not customized.
    report = _report_from_setting(
        {
            "order_list": ["DM.Age", "Subject", "DM.Weight"],
            "selected_items_order_list": ["Subject", "DM.Weight", "DM.Age"],
            "order_list_customized": False,
        }
    )

    assert report.get_selected_items_order_list() == ["DM.Age", "Subject", "DM.Weight"]


def test_a_saved_setting_has_no_order_list():
    report = _report_from_setting({"order_list": ["DM.Age", "Subject", "DM.Weight"]})

    assert "order_list" not in report.settings_to_dict("x")


def test_customization_resets_when_nothing_survives(report_with_data):
    report = report_with_data
    report.set_common_item_state("Subject", selected=True)
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Weight", selected=True)
    report.set_selected_items_order_list(["DM.Weight", "Subject"])

    # Deselect everything: the manual arrangement has nothing left to apply.
    report.set_common_item_state("Subject", selected=False)
    report.selected_forms["DM"].set_form_item_state("Weight", selected=False)
    assert report.update_selected_items_order_list() == []
    assert report.order_list_customized is False


def test_manual_reordering_is_preserved_when_new_items_arrive(report_with_data):
    report = report_with_data
    report.set_common_item_state("Subject", selected=True)
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Weight", selected=True)
    report.update_selected_items_order_list()

    # User rearranges on the Order & rename page.
    report.set_selected_items_order_list(["DM.Weight", "Subject"])

    # A newly selected item slots in after its default predecessor without
    # disturbing the manual arrangement.
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    order = report.update_selected_items_order_list()
    assert order == ["DM.Weight", "DM.Age", "Subject"]


def test_reconcile_keeps_input_column_order(report_with_data):
    report = report_with_data
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)

    missing = report.reconcile_with_current_data()

    assert missing == {"forms": [], "items": []}
    assert report.static_available_common_items == ["Subject", "Visit"]
    assert report.get_available_common_items() == ["Subject", "Visit"]
    assert report.selected_forms["DM"].get_available_form_items() == ["Weight"]
    assert report.selected_forms["DM"].get_selected_form_items() == ["Age"]
    assert report.available_forms["VS"].get_available_form_items() == ["Pulse", "BP"]


def test_report_output_columns_follow_file_and_merge_order():
    data = {
        "DM": pd.DataFrame(
            {"Subject": ["001"], "Visit": [1], "Weight": [70], "Age": [30]}
        ),
        "VS": pd.DataFrame(
            {"Subject": ["001"], "Visit": [1], "Pulse": [60], "BP": [120]}
        ),
    }
    report = CLReport()
    report.set_data(data)
    report.set_common_item_state("Subject", selected=True)
    report.add_selected_form("DM")
    report.add_selected_form("VS")

    # Select items in non-file order to prove the output ignores click order.
    for item in ["Age", "Weight"]:
        report.selected_forms["DM"].set_form_item_state(item, selected=True)
    for item in ["BP", "Pulse"]:
        report.selected_forms["VS"].set_form_item_state(item, selected=True)

    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    report.update_join_items("VS", ["Subject"], 2, JoinHow.LEFT)
    report.update_selected_items_order_list()

    result = report.create_report()

    assert list(result.columns) == [
        "Subject",
        "DM.Weight",
        "DM.Age",
        "VS.Pulse",
        "VS.BP",
    ]


def test_clform_without_column_order_appends():
    # Forms built directly (e.g. deserialized before reconcile) fall back to
    # append semantics until a column order is known.
    form = CLForm("DM")
    form.available_form_items = ["Weight", "Age"]
    form.set_form_item_state("Weight", selected=True)
    form.set_form_item_state("Age", selected=True)
    assert form.get_selected_form_items() == ["Weight", "Age"]
