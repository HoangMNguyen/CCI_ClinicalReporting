import json

import pandas as pd

from clinical_reporting.models import CLForm
from clinical_reporting.report import CLReport


def _make_form(name, *, selected_items=None, join_items=None, join_order=None, join_how=None):
    form = CLForm(name)
    form.selected_form_items = list(selected_items or [])
    form.join_items = list(join_items or [])
    form.join_order = join_order
    form.join_how = join_how
    return form


def test_save_and_load_settings_roundtrip(tmp_path):
    report = CLReport()
    report.study_name = "TestStudy"
    report.selected_common_items = ["Subject"]
    report.new_items = ["BMI"]
    report.order_list = ["Subject", "DM.Age"]
    report.selected_items_order_list = ["Subject", "DM.Age"]
    report.rename_dict = {"DM.Age": "Age"}
    report.static_filter_items = [("Age", ">", "30")]
    report.dynamic_filter_items = [("DM.Age", ">", "DM.Weight")]

    dm_form = _make_form(
        "DM",
        selected_items=["Age"],
        join_items=["Subject"],
        join_order=1,
        join_how="Left join",
    )
    report.selected_forms = {"DM": dm_form}

    output_file = tmp_path / "settings.json"
    report.save_setting_to_json(str(output_file), setting_name="baseline")

    with open(output_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    assert "available_forms" not in payload
    assert payload["selected_forms"]["DM"]["selected_form_items"] == ["Age"]
    assert payload["selected_forms"]["DM"]["join_items"] == ["Subject"]
    assert payload["selected_common_items"] == ["Subject"]
    assert payload["static_filter_items"] == [["Age", ">", "30"]]
    assert payload["dynamic_filter_items"] == [["DM.Age", ">", "DM.Weight"]]

    loaded_report = CLReport()
    loaded_report.load_setting_from_json(str(output_file))

    loaded_form = loaded_report.selected_forms["DM"]
    assert loaded_form.get_selected_form_items() == ["Age"]
    assert loaded_form.get_join_items() == ["Subject"]
    assert loaded_form.get_join_order() == 1
    assert loaded_form.get_join_how() == "Left join"
    assert loaded_report.rename_dict == {"DM.Age": "Age"}
    assert loaded_report.selected_items_order_list == ["Subject", "DM.Age"]


def test_reconcile_with_current_data_reports_missing_forms_and_items():
    report = CLReport()
    dm_df = pd.DataFrame(
        {
            "Subject": ["001", "002"],
            "Shared": ["A", "B"],
            "Age": [30, 40],
        }
    )
    vs_df = pd.DataFrame(
        {
            "Subject": ["001", "003"],
            "Shared": ["A", "C"],
            "Pulse": [80, 90],
        }
    )
    report.data = {"DM": dm_df, "VS": vs_df}

    dm_form = _make_form("DM", selected_items=["Age", "DoesNotExist"], join_items=["Subject"])
    orphan_form = _make_form("LB", selected_items=["LabValue"])

    report.selected_forms = {"DM": dm_form, "LB": orphan_form}
    report.selected_common_items = ["Subject", "Shared", "Legacy"]
    report.order_list = ["Subject", "DM.DoesNotExist"]
    report.selected_items_order_list = ["Legacy", "DM.DoesNotExist"]
    report.static_filter_items = [("Legacy", "=", "foo"), ("DM.DoesNotExist", "=", "bar")]
    report.dynamic_filter_items = [("DM.Age", ">", "LB.LabValue")]
    report.rename_dict = {"Legacy": "Renamed"}

    result = report.reconcile_with_current_data()

    assert result == {
        "forms": ["LB"],
        "items": ["DM.DoesNotExist", "Legacy"],
    }

    assert "LB" not in report.selected_forms
    assert report.available_forms["VS"].get_name() == "VS"
    assert report.selected_common_items == ["Subject", "Shared"]
    assert report.selected_forms["DM"].get_selected_form_items() == ["Age"]
    assert report.order_list == ["Subject"]
    assert report.selected_items_order_list == []
    assert report.static_filter_items == []
    assert report.dynamic_filter_items == []
    assert report.rename_dict == {}
