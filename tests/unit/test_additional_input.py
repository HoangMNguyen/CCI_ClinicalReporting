import pandas as pd

from clinical_reporting.core.report import CLReport
from clinical_reporting.ui.tabs.additional_input import AdditionalInputTabMixin


class DummyWidget(AdditionalInputTabMixin):
    """Lightweight stand-in to exercise the mixin logic without Qt."""

    def __init__(self):
        # Initialize mixin state expected by the helpers.
        self.additional_inputs = {}
        self.additional_form_names = {}
        self.additional_column_names = {}
        self._additional_form_keys = set()
        self.report = CLReport()
        self.update_all_ui_calls = 0

    def update_all_ui(self):
        self.update_all_ui_calls += 1


def test_strip_upcc_prefix():
    widget = DummyWidget()
    assert widget._strip_upcc_prefix("UPCC-12345") == "12345"
    assert widget._strip_upcc_prefix("UPCC 987") == "987"
    assert widget._strip_upcc_prefix("NO_PREFIX") == "NO_PREFIX"
    assert widget._strip_upcc_prefix(123) == 123  # non-string unaffected


def test_build_additional_data_map_cleans_subject_and_drops_unnamed():
    widget = DummyWidget()
    file_path = "/tmp/sample.csv"
    widget.additional_inputs[file_path] = pd.DataFrame(
        {
            "Subject": ["UPCC-111", "UPCC222"],
            "keep": [1, 2],
            "Unnamed: 0": [0, 0],
        }
    )
    widget.additional_form_names[file_path] = "FormX"
    widget.additional_column_names[(file_path, "Subject")] = "Subject"

    result = widget._build_additional_data_map()

    assert "FormX" in result
    df = result["FormX"]
    assert list(df.columns) == ["Subject", "keep"]
    assert df["Subject"].tolist() == ["111", "222"]


def test_apply_additional_inputs_preserves_available_selections_only():
    widget = DummyWidget()

    # Base report with one form and selections.
    base_df = pd.DataFrame({"Subject": ["S1", "S2"], "A1": [1, 2]})
    widget.report.set_data({"FormA": base_df})
    widget.report.add_selected_form("FormA")
    widget.report.selected_forms["FormA"].set_form_item_state("A1", selected=True)
    widget.report.set_common_item_state("A1", selected=True)
    widget.report.set_common_item_state("Subject", selected=True)

    # Additional form without A1 so common items will shrink to Subject only.
    add_path = "/tmp/formB.csv"
    widget.additional_inputs[add_path] = pd.DataFrame(
        {"Subject": ["S1", "S2"], "B1": [10, 20]}
    )
    widget.additional_form_names[add_path] = "FormB"

    widget.click_apply_additional_forms()

    # Form selection preserved when still available.
    assert "FormA" in widget.report.selected_forms
    # Form item selection preserved for existing items.
    assert "A1" in widget.report.selected_forms["FormA"].get_selected_form_items()
    # Common items re-identified; A1 no longer common, Subject remains selected.
    assert "Subject" in widget.report.get_selected_common_items()
    assert "A1" not in widget.report.get_selected_common_items()
    # New form should now be available after add.
    assert "FormB" in widget.report.available_forms
    # UI refresh was invoked.
    assert widget.update_all_ui_calls == 1
