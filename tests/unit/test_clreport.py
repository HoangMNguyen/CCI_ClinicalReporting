import types

import pytest

from clinical_reporting.models import CLForm
from clinical_reporting.report import CLReport


# Lightweight stand-in for pandas DataFrame objects used during form setup.
class DummyTable:
    def __init__(self, columns):
        self.columns = columns


@pytest.fixture(scope="module", autouse=True)
def ensure_numpy_stub():
    """Provide a numpy stub when the dependency is not installed."""

    import sys

    if "numpy" not in sys.modules:
        sys.modules["numpy"] = types.SimpleNamespace(datetime64=object)


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


def test_study_name_and_data_accessors(dummy_data):
    report = CLReport()
    report.set_study_name("StudyA")
    assert report.study_name == "StudyA"

    report.set_data(dummy_data)
    assert report.get_data() == dummy_data


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
    report.remove_available_form("DM")
    assert "DM" not in report.get_available_forms_list()

    report.remove_all_available_forms()
    assert report.get_available_forms_list() == []


def test_order_and_rename_helpers():
    report = CLReport()
    report.set_order_list(["Subject"])
    assert report.get_order_list() == ["Subject"]

    report.set_rename_dict({"Subject": "ID"})
    assert report.get_rename_dict() == {"Subject": "ID"}

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

    report.remove_all_available_common_items()
    assert report.get_available_common_items() == []


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


def test_file_path_and_selected_items_setters():
    report = CLReport()
    report.set_file_path("settings.json")
    assert report.file_path == "settings.json"

    report.set_selected_items_order_list(["Subject"])
    assert report.get_selected_items_order_list() == ["Subject"]


def test_serialize_and_deserialize_form_roundtrip():
    form = CLForm("DM")
    form.available_form_items = ["Age"]
    form.selected_form_items = ["Subject"]
    form.join_items = ["Subject"]
    form.join_order = 1
    form.join_how = "Left join"

    payload = CLReport._serialize_form(form)
    restored = CLReport._deserialize_form("DM", payload)

    assert restored.get_available_form_items() == ["Age"]
    assert restored.get_selected_form_items() == ["Subject"]
    assert restored.get_join_items() == ["Subject"]
    assert restored.get_join_order() == 1
    assert restored.get_join_how() == "Left join"


def test_join_list_helpers():
    report = CLReport()
    form = CLForm("DM")
    form.set_join_items(["Subject"])
    form.set_join_order(1)
    form.set_join_how("Inner join")
    report.selected_forms = {"DM": form}

    join_list = report.get_join_list()
    assert join_list == ["DM", ["Subject"], 1, "Inner join"]

    join_dict = report.get_join_list_dict()
    assert join_dict == {"DM": {"items": ["Subject"], "order": 1, "how": "Inner join"}}

    report.update_join_list([("DM", ["Subject", "Visit"], 2, "Left join")])
    assert report.selected_forms["DM"].get_join_items() == ["Subject", "Visit"]
    assert report.selected_forms["DM"].get_join_order() == 2
    assert report.selected_forms["DM"].get_join_how() == "Left join"


def test_add_join_item_and_update_join_items():
    report = CLReport()
    form = CLForm("VS")
    report.selected_forms = {"VS": form}

    report.add_join_item("VS", "Subject", 3, "Outer join")
    assert form.get_join_items() == ["Subject"]
    assert form.get_join_order() == 3
    assert form.get_join_how() == "Outer join"

    report.update_join_items("VS", ["Subject", "Visit"], 1, "Left join")
    assert form.get_join_items() == ["Subject", "Visit"]
    assert form.get_join_order() == 1


def test_get_all_selected_items():
    report = CLReport()
    form = CLForm("DM")
    form.selected_form_items = ["Age"]
    report.selected_forms = {"DM": form}
    report.selected_common_items = ["Subject"]

    items = report.get_all_selected_items()
    assert set(items) == {"Subject", "Age"}


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


def test_dynamic_filter_management():
    report = CLReport()

    report.add_dynamic_filter_item("DM.Age", ">", "VS.Pulse")
    assert report.get_dynamic_filter_items() == [("DM.Age", ">", "VS.Pulse")]

    report.update_dynamic_filter_item(0, "DM.Age", ">=", "VS.Pulse")
    assert report.get_dynamic_filter_items() == [("DM.Age", ">=", "VS.Pulse")]

    report.update_dynamic_filter_item(5, "DM.Weight", "=", "VS.Weight")
    assert report.get_dynamic_filter_items()[-1] == ("DM.Weight", "=", "VS.Weight")

    report.remove_dynamic_filter_item(item1="DM.Age")
    assert report.get_dynamic_filter_items() == [("DM.Weight", "=", "VS.Weight")]

    report.set_dynamic_filter_items([("Subject", "=", "Subject")])
    assert report.get_dynamic_filter_items() == [("Subject", "=", "Subject")]
