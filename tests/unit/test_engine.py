"""Tests for pipeline.ReportEngine and its decomposed helpers.

The end-to-end report output is also covered by the integration suite; these
focus on the individual steps the ~285-line ``create_report`` was broken into,
and confirm ``CLReport.create_report`` still delegates to the engine.
"""

import pandas as pd
from pandas.testing import assert_frame_equal

from clinical_reporting import report_columns
from clinical_reporting.pipeline import ReportEngine
from clinical_reporting.report import CLReport


def _two_form_report():
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame({"Subject": ["001", "002", "003"], "Age": [75, 41, 29]}),
            "VS": pd.DataFrame(
                {"Subject": ["001", "002", "003"], "Pulse": [70, 90, 55]}
            ),
        }
    )
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.selected_forms["DM"].set_join_order(1)

    report.add_selected_form("VS")
    report.selected_forms["VS"].set_form_item_state("Pulse", selected=True)
    report.selected_forms["VS"].set_join_items(["Subject"])
    report.selected_forms["VS"].set_join_order(2)
    report.selected_forms["VS"].set_join_how("Left join")

    report.set_common_item_state("Subject", selected=True)
    return report


def test_engine_run_joins_forms_in_order():
    df = ReportEngine(_two_form_report()).run()
    assert list(df.columns) == ["Subject", "DM.Age", "VS.Pulse"]
    assert len(df) == 3


def test_create_report_delegates_to_engine():
    report = _two_form_report()
    assert_frame_equal(
        report.create_report().reset_index(drop=True),
        ReportEngine(report).run().reset_index(drop=True),
    )


def test_forms_join_in_join_order():
    report = _two_form_report()
    assert report_columns.forms_in_join_order(report.selected_forms) == ["DM", "VS"]
    report.selected_forms["DM"].set_join_order(5)
    assert report_columns.forms_in_join_order(report.selected_forms) == ["VS", "DM"]


def test_resolve_filter_column_direct_suffix_and_missing():
    cols = ["Subject", "DM.Age", "VS.Pulse"]
    # Direct match.
    assert ReportEngine._resolve_filter_column("DM.Age", cols) == "DM.Age"
    # Unqualified operand resolved by item suffix.
    assert ReportEngine._resolve_filter_column("Pulse", cols) == "VS.Pulse"
    # Not present at all.
    assert ReportEngine._resolve_filter_column("Missing", cols) is None
    # Qualified but not present -> no suffix fallback.
    assert ReportEngine._resolve_filter_column("XX.Age", cols) is None


def test_reorder_columns_prefers_order_list_over_selected_items():
    report = _two_form_report()
    report.order_list = ["VS.Pulse", "Subject", "DM.Age"]
    report.selected_items_order_list = ["DM.Age", "Subject", "VS.Pulse"]
    df = report.create_report()
    assert list(df.columns) == ["VS.Pulse", "Subject", "DM.Age"]


def test_reorder_falls_back_to_selected_items_order_list():
    report = _two_form_report()
    report.order_list = []
    report.selected_items_order_list = ["VS.Pulse", "Subject", "DM.Age"]
    df = report.create_report()
    assert list(df.columns) == ["VS.Pulse", "Subject", "DM.Age"]


def test_engine_applies_static_dynamic_filters_and_rename():
    report = _two_form_report()
    # Static keeps Age > 30 (drops 003). Dynamic keeps Pulse > Age (only 002).
    report.static_filter_items = [("DM.Age", ">", "30")]
    report.dynamic_filter_items = [("VS.Pulse", ">", "DM.Age")]
    report.rename_dict = {"VS.Pulse": "PulseBPM"}

    df = report.create_report().reset_index(drop=True)
    assert df["Subject"].tolist() == ["002"]
    assert "PulseBPM" in df.columns
    assert "VS.Pulse" not in df.columns


def test_engine_formats_date_columns_as_short_strings():
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame(
                {
                    "Subject": ["001", "002"],
                    "Visit Date": pd.to_datetime(["2024-01-05", "2024-02-10"]),
                }
            )
        }
    )
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_join_order(1)
    report.set_common_item_state("Subject", selected=True)
    report.set_common_item_state("Visit Date", selected=True)

    df = report.create_report().reset_index(drop=True)
    assert df["Visit Date"].tolist() == ["1/5/2024", "2/10/2024"]
