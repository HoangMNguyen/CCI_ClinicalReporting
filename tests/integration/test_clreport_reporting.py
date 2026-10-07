import pandas as pd
from pandas.testing import assert_frame_equal

from clinical_reporting.models import CLForm
from clinical_reporting.report import CLReport


def _init_form(name, *, selected_items, join_order, join_how="Left join"):
    form = CLForm(name)
    form.selected_form_items = selected_items
    form.join_items = ["Subject", "Visit"]
    form.join_order = join_order
    form.join_how = join_how
    return form


def test_create_report_applies_filters_and_formatting():
    report = CLReport()
    dm_df = pd.DataFrame(
        {
            "Subject": ["001", "002", "003"],
            "Visit": ["Screening", "Screening", "Screening"],
            "Age": [75, 41, 29],
        }
    )
    vs_df = pd.DataFrame(
        {
            "Subject": ["001", "002", "003"],
            "Visit": ["Screening", "Screening", "Screening"],
            "Pulse": [70, 90, 55],
            "Assessment Date": pd.to_datetime(
                ["2024-01-05", "2024-02-10", "2024-02-11"]
            ),
        }
    )

    report.data = {"DM": dm_df, "VS": vs_df}
    report.selected_common_items = ["Subject", "Visit"]

    dm_form = _init_form("DM", selected_items=["Age"], join_order=1)
    vs_form = _init_form(
        "VS",
        selected_items=["Pulse", "Assessment Date"],
        join_order=2,
        join_how="Inner join",
    )
    report.selected_forms = {"DM": dm_form, "VS": vs_form}

    report.static_filter_items = [("Age", ">", "30")]
    report.dynamic_filter_items = [("VS.Pulse", ">", "DM.Age")]
    report.order_list = ["Subject", "Visit", "DM.Age", "VS.Pulse"]
    report.rename_dict = {"VS.Pulse": "PulseBPM"}

    result = report.create_report()

    expected = pd.DataFrame(
        {
            "Subject": ["002"],
            "Visit": ["Screening"],
            "DM.Age": [41],
            "PulseBPM": [90],
            "VS.Assessment Date": ["2/10/2024"],
        }
    )

    assert_frame_equal(result.reset_index(drop=True), expected)
