import pandas as pd
import pytest
from tests.unit.fakes import DummyTable

from clinical_reporting.models import CLForm
from clinical_reporting.report import CLReport
from clinical_reporting.sample_data import sample_forms
from clinical_reporting.session import new_report


@pytest.fixture
def dummy_data():
    return {
        "DM": DummyTable(["Subject", "Age", "Sex"]),
        "VS": DummyTable(["Subject", "Pulse"]),
    }


@pytest.fixture
def report_with_data(dummy_data):
    report = CLReport()
    report.set_data(dummy_data)
    return report


def test_study_name_accessor():
    report = CLReport()
    report.set_study_name("StudyA")
    assert report.study_name == "StudyA"


def test_identify_common_items(dummy_data):
    report = CLReport()
    report.data = dummy_data

    report.identify_common_items()

    assert report.static_available_common_items == ["Subject"]


def test_set_data_populates_forms_and_common_items(report_with_data):
    report = report_with_data

    assert sorted(report.get_available_forms_list()) == ["DM", "VS"]
    assert report.get_selected_forms_list() == []
    assert report.get_available_common_items() == ["Subject"]


def test_add_selected_form_populates_items(report_with_data):
    report = report_with_data
    report.add_selected_form("DM")

    assert "DM" in report.get_selected_forms_list()
    assert "DM" not in report.get_available_forms_list()

    form = report.selected_forms["DM"]
    assert sorted(form.get_available_form_items()) == ["Age", "Sex"]


def test_remove_selected_form_and_add_available(report_with_data):
    report = report_with_data
    report.add_selected_form("VS")
    assert "VS" in report.get_selected_forms_list()

    report.add_available_form("VS")
    assert "VS" in report.get_available_forms_list()
    assert "VS" not in report.get_selected_forms_list()


def test_bulk_form_operations(report_with_data):
    report = report_with_data
    report.add_all_selected_forms()
    assert sorted(report.get_selected_forms_list()) == ["DM", "VS"]
    assert report.get_available_forms_list() == []

    report.remove_all_selected_forms()
    assert report.get_selected_forms_list() == []

    report.add_all_available_forms()
    report.remove_all_available_forms()
    assert report.get_available_forms_list() == []


def test_order_and_rename_helpers():
    report = CLReport()
    report.set_rename_item("Subject", "PatientID")
    assert report.get_rename_dict() == {"Subject": "PatientID"}

    report.set_rename_item("Subject", "")  # Removing mapping
    assert report.get_rename_dict() == {}

    report.remove_rename_item("Unknown")  # No error on missing key


def test_common_item_bulk_operations():
    report = CLReport()
    report.static_available_common_items = ["Subject", "Visit"]
    report.add_all_available_common_items()
    assert sorted(report.get_available_common_items()) == ["Subject", "Visit"]

    report.set_common_item_state("Subject", selected=True)
    assert report.get_selected_common_items() == ["Subject"]


def test_selected_items_order_update():
    report = CLReport()
    form = CLForm("DM")
    form.selected_form_items = ["Age"]
    report.selected_forms = {"DM": form}
    report.selected_common_items = ["Subject"]
    report.selected_items_order_list = ["Subject", "DM.Age"]

    assert report.update_selected_items_order_list() == ["Subject", "DM.Age"]

    form.selected_form_items.append("Sex")
    order = report.update_selected_items_order_list()
    assert order == ["Subject", "DM.Age", "DM.Sex"]


def test_selected_items_order_setter():
    report = CLReport()
    report.set_selected_items_order_list(["Subject"])
    assert report.get_selected_items_order_list() == ["Subject"]


def test_serialize_and_deserialize_form_roundtrip(dummy_data):
    report = CLReport()
    report.set_data(dummy_data)
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.update_join_items("DM", ["Subject"], 2, "Inner join")

    restored = CLReport()
    restored.set_data(dummy_data)
    restored.load_setting_from_dict(report.settings_to_dict("baseline"))

    form = restored.selected_forms["DM"]
    assert form.get_selected_form_items() == ["Age"]
    assert form.get_join_items() == ["Subject"]
    assert form.get_join_order() == 2
    assert form.get_join_how() == "Inner join"


def test_join_list_helpers():
    report = CLReport()
    form = CLForm("DM")
    form.set_join_items(["Subject"])
    form.set_join_order(1)
    form.set_join_how("Inner join")
    report.selected_forms = {"DM": form}

    join_dict = report.get_join_list_dict()
    assert join_dict == {"DM": {"items": ["Subject"], "order": 1, "how": "Inner join"}}

    report.update_join_list([("DM", ["Subject", "Visit"], 2, "Left join")])
    assert report.selected_forms["DM"].get_join_items() == ["Subject", "Visit"]
    assert report.selected_forms["DM"].get_join_order() == 2
    assert report.selected_forms["DM"].get_join_how() == "Left join"


def test_update_join_items():
    report = CLReport()
    form = CLForm("VS")
    report.selected_forms = {"VS": form}

    report.update_join_items("VS", ["Subject", "Visit"], 1, "Left join")
    assert form.get_join_items() == ["Subject", "Visit"]
    assert form.get_join_order() == 1


def test_every_selected_forms_joins_are_tidied_with_one_rule():
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame(columns=["Subject", "Site", "Age"]),
            "AE": pd.DataFrame(columns=["Subject", "Site", "Term"]),
            "VS": pd.DataFrame(columns=["Subject", "Site", "Pulse"]),
        }
    )
    for form in ("DM", "AE", "VS"):
        report.add_selected_form(form)
    report.set_common_item_state("Subject", selected=True)
    report.set_common_item_state("Site", selected=True)
    report.update_join_items("DM", ["Subject"], None, "Inner join")
    report.update_join_items("AE", ["Visit", "Site", "Site", "Subject"], 7, "Sideways")
    report.update_join_items("VS", ["Visit", "Subject"], "2", "Inner join")

    report.normalize_joins()

    assert report.get_join_list_dict() == {
        "DM": {"items": [], "order": 1, "how": "Left join"},
        "AE": {"items": ["Site"], "order": 3, "how": "Left join"},
        "VS": {"items": ["Subject"], "order": 2, "how": "Inner join"},
    }


def _demo_report(*forms):
    report = new_report("DEMO01", sample_forms())
    for form in forms:
        report.add_selected_form(form)
    return report


def test_a_newly_selected_form_joins_last_on_subject():
    report = _demo_report("DM", "AE", "VS")

    report.normalize_joins()

    assert report.get_join_list_dict() == {
        "DM": {"items": [], "order": 1, "how": "Left join"},
        "AE": {"items": ["Subject"], "order": 2, "how": "Left join"},
        "VS": {"items": ["Subject"], "order": 3, "how": "Left join"},
    }


def test_a_form_selected_after_a_removal_still_joins_last():
    report = _demo_report("DM", "AE", "VS", "CM")
    report.remove_selected_form("DM")
    report.remove_selected_form("AE")

    report.add_selected_form("LB")
    report.normalize_joins()

    assert {
        form: join["order"] for form, join in report.get_join_list_dict().items()
    } == {"VS": 1, "CM": 2, "LB": 3}


def test_tied_join_orders_are_renumbered_in_selection_order():
    report = _demo_report("DM", "AE", "VS")
    report.update_join_list(
        [
            ("DM", [], 2, "Left join"),
            ("AE", ["Subject"], 2, "Inner join"),
            ("VS", ["Subject"], 5, "Left join"),
        ]
    )

    report.normalize_joins()

    assert report.get_join_list_dict() == {
        "DM": {"items": [], "order": 1, "how": "Left join"},
        "AE": {"items": ["Subject"], "order": 2, "how": "Inner join"},
        "VS": {"items": ["Subject"], "order": 3, "how": "Left join"},
    }


def test_moving_a_form_up_swaps_it_with_the_form_before():
    report = _demo_report("DM", "AE", "VS")
    report.update_join_items("VS", ["Subject"], 3, "Inner join")

    report.move_join("VS", -1)

    assert report.get_join_list_dict() == {
        "DM": {"items": [], "order": 1, "how": "Left join"},
        "AE": {"items": ["Subject"], "order": 3, "how": "Left join"},
        "VS": {"items": ["Subject"], "order": 2, "how": "Inner join"},
    }


def test_the_form_moved_out_of_first_place_joins_on_subject():
    report = _demo_report("DM", "AE", "VS")
    report.set_common_item_state("Site", selected=True)
    report.update_join_items("AE", ["Site"], 2, "Inner join")

    report.move_join("DM", 1)

    assert report.get_join_list_dict() == {
        "DM": {"items": ["Subject"], "order": 2, "how": "Left join"},
        "AE": {"items": [], "order": 1, "how": "Left join"},
        "VS": {"items": ["Subject"], "order": 3, "how": "Left join"},
    }


def test_a_form_at_either_end_does_not_move_past_it():
    report = _demo_report("DM", "AE", "VS")
    report.normalize_joins()
    before = report.get_join_list_dict()

    report.move_join("DM", -1)
    report.move_join("VS", 1)
    report.move_join("LB", -1)  # Not selected.

    assert report.get_join_list_dict() == before


def test_without_subject_the_form_moved_out_of_first_place_joins_on_nothing():
    report = _demo_report("DM", "AE")
    report.set_common_item_state("Subject", selected=False)

    report.move_join("AE", -1)

    assert report.get_join_list_dict() == {
        "DM": {"items": [], "order": 2, "how": "Left join"},
        "AE": {"items": [], "order": 1, "how": "Left join"},
    }


def test_static_filter_management():
    report = CLReport()
    form = CLForm("DM")
    form.selected_form_items = ["Age"]
    report.selected_forms = {"DM": form}
    report.selected_common_items = ["Subject"]

    report.add_static_filter_item("Subject", "=", "001")
    report.add_static_filter_item("DM.Age", ">", "18")
    assert report.get_static_filter_items() == [
        ("Subject", "=", "001"),
        ("DM.Age", ">", "18"),
    ]

    report.remove_static_filter_item("Subject", operator="=", value="001")
    assert report.get_static_filter_items() == [("DM.Age", ">", "18")]

    report.set_static_filter_items([("Subject", "=", "002")])
    assert report.get_static_filter_items() == [("Subject", "=", "002")]


def test_a_filter_on_a_bare_item_name_needs_a_form_that_selected_it():
    report = CLReport()
    dm, vs = CLForm("DM"), CLForm("VS")
    dm.selected_form_items = ["Age"]
    vs.selected_form_items = ["Pulse"]
    report.selected_forms = {"DM": dm, "VS": vs}

    report.add_static_filter_item("Pulse", ">", "60")
    report.add_static_filter_item("Pulse", ">", "60")  # Not added twice.
    report.add_static_filter_item("Weight", "=", "70")  # No form selected it.

    assert report.get_static_filter_items() == [("Pulse", ">", "60")]


def test_dynamic_filter_management():
    report = CLReport()

    report.add_dynamic_filter_item("DM.Age", ">", "VS.Pulse")
    assert report.get_dynamic_filter_items() == [("DM.Age", ">", "VS.Pulse")]

    report.add_dynamic_filter_item("DM.Weight", "=", "VS.Weight")
    assert report.get_dynamic_filter_items()[-1] == ("DM.Weight", "=", "VS.Weight")

    report.remove_dynamic_filter_item(item1="DM.Age")
    assert report.get_dynamic_filter_items() == [("DM.Weight", "=", "VS.Weight")]

    report.set_dynamic_filter_items([("Subject", "=", "Subject")])
    assert report.get_dynamic_filter_items() == [("Subject", "=", "Subject")]
