"""Tests for the report actions in clinical_reporting.session."""

import pandas as pd

from clinical_reporting import session
from clinical_reporting.report import CLReport
from clinical_reporting.session import capture_selection, restore_selection


def _forms():
    return {
        "DM": pd.DataFrame({"Subject": ["001", "002"], "Age": [54, 61]}),
        "AE": pd.DataFrame({"Subject": ["001", "002"], "Term": ["Nausea", "Fatigue"]}),
    }


class _StubReport:
    def __init__(self, result):
        self.result = result

    def create_report(self):
        return self.result


def test_new_report_starts_with_subject_selected():
    report = session.new_report("DEMO01", _forms())

    assert report.study_name == "DEMO01"
    assert set(report.available_forms) == {"DM", "AE"}
    assert report.get_selected_common_items() == ["Subject"]


def test_replacing_base_data_keeps_additional_forms_and_selections():
    report = CLReport()
    report.set_data(
        {**_forms(), "Labs": pd.DataFrame({"Subject": ["001"], "Hb": [12]})}
    )
    report.add_selected_form("DM")
    report.add_selected_form("Labs")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    only_dm = {"DM": pd.DataFrame({"Subject": ["001"], "Age": [54]})}

    session.replace_base_data(report, only_dm, additional_keys={"Labs"})

    assert set(report.data) == {"DM", "Labs"}
    assert len(report.data["DM"]) == 1
    assert set(report.selected_forms) == {"DM", "Labs"}
    assert report.selected_forms["DM"].get_selected_form_items() == ["Age"]


def test_without_base_data_keeps_only_additional_forms():
    report = CLReport()
    report.set_data(
        {**_forms(), "Labs": pd.DataFrame({"Subject": ["001"], "Hb": [12]})}
    )
    report.add_selected_form("DM")
    report.add_selected_form("Labs")
    report.static_filter_items = [("DM.Age", ">", "50")]

    fresh = session.without_base_data(report, additional_keys={"Labs"})

    assert fresh is not report
    assert set(fresh.data) == {"Labs"} and set(fresh.selected_forms) == {"Labs"}
    assert fresh.static_filter_items == []
    assert session.without_base_data(report, additional_keys=set()).data == {}


def test_build_report_returns_none_when_nothing_matches():
    assert session.build_report(_StubReport(None)) is None
    assert session.build_report(_StubReport(pd.DataFrame())) is None

    rows = session.build_report(_StubReport(pd.DataFrame({"A": [1, 2]}, index=[5, 9])))

    assert rows.index.tolist() == [0, 1]


def test_export_writes_the_rows_or_nothing(tmp_path):
    target = tmp_path / "report.xlsx"

    assert session.export_report(_StubReport(pd.DataFrame()), str(target)) is None
    assert not target.exists()

    written = session.export_report(_StubReport(pd.DataFrame({"A": [1]})), str(target))

    assert written == str(target) and target.stat().st_size > 0


def test_selection_is_restored_after_rebuilding_the_data():
    data = {
        "DM": pd.DataFrame({"Subject": ["01"], "Site": ["A"], "Age": [42]}),
        "AE": pd.DataFrame({"Subject": ["01"], "Site": ["A"], "Term": ["Rash"]}),
    }
    report = CLReport()
    report.set_data(data)
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.set_common_item_state("Subject", selected=True)
    state = capture_selection(report)

    # A rebuild (for example a cut-off reload) creates fresh form objects.
    report.set_data({name: df.copy() for name, df in data.items()})
    assert report.get_selected_forms_list() == []
    restore_selection(report, state)

    assert report.get_selected_forms_list() == ["DM"]
    assert report.selected_forms["DM"].get_selected_form_items() == ["Age"]
    assert "Subject" in report.get_selected_common_items()
