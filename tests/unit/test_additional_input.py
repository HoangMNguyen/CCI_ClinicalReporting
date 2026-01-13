import pandas as pd

from clinical_reporting.core.report import CLReport
from clinical_reporting.ui.tabs import additional_input as additional_input_module
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


def test_strip_prefix():
    widget = DummyWidget()
    assert widget._strip_prefix("UPCC-12345") == "12345"
    assert widget._strip_prefix("UPCC 987") == "987"
    assert widget._strip_prefix("100-555") == "555"
    assert widget._strip_prefix("NO_PREFIX") == "NO_PREFIX"
    assert widget._strip_prefix(123) == 123  # non-string unaffected


def test_build_additional_data_map_cleans_subject_and_drops_unnamed():
    widget = DummyWidget()
    file_path = "/tmp/sample.csv"
    widget.additional_inputs[file_path] = pd.DataFrame(
        {
            "Subject": ["UPCC-111", "UPCC222", "100-333"],
            "keep": [1, 2, 3],
            "Unnamed: 0": [0, 0, 0],
        }
    )
    widget.additional_form_names[file_path] = "FormX"
    widget.additional_column_names[(file_path, "Subject")] = "Subject"

    result = widget._build_additional_data_map()

    assert "FormX" in result
    df = result["FormX"]
    assert list(df.columns) == ["Subject", "keep"]
    assert df["Subject"].tolist() == ["111", "222", "333"]


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


def test_renaming_additional_form_replaces_old_entry():
    widget = DummyWidget()
    file_path = "/tmp/RSC.csv"
    widget.additional_inputs[file_path] = pd.DataFrame({"Subject": ["S1"], "A": [1]})

    # Initial apply with explicit form name to avoid dotted default
    widget.additional_form_names[file_path] = "RSC"
    widget.click_apply_additional_forms()
    assert "RSC" in widget.report.get_available_forms_list()

    # Rename to RSC_clean and re-apply; the old name should be removed
    widget.additional_form_names[file_path] = "RSC_clean"
    widget.click_apply_additional_forms()

    forms = widget.report.get_available_forms_list()
    assert "RSC_clean" in forms
    assert "RSC" not in forms
    assert set(widget.report.data.keys()) == {"RSC_clean"}


def test_warn_on_additional_form_conflicts_detects_duplicates(monkeypatch):
    widget = DummyWidget()
    widget.additional_inputs["/tmp/a.csv"] = pd.DataFrame({"Subject": ["S1"]})
    widget.additional_inputs["/tmp/b.csv"] = pd.DataFrame({"Subject": ["S2"]})
    widget.additional_form_names["/tmp/a.csv"] = "DupForm"
    widget.additional_form_names["/tmp/b.csv"] = "DupForm"

    calls = []

    def fake_warning(parent, title, message):
        calls.append((title, message))

    monkeypatch.setattr(additional_input_module.QMessageBox, "warning", fake_warning)

    assert widget._warn_on_additional_form_conflicts(set()) is True
    assert calls
    assert "DupForm" in calls[0][1]


def test_warn_on_additional_form_conflicts_detects_dots(monkeypatch):
    widget = DummyWidget()
    widget.additional_inputs["/tmp/a.csv"] = pd.DataFrame({"Subject": ["S1"]})
    widget.additional_form_names["/tmp/a.csv"] = "Form.With.Dot"

    calls = []

    def fake_warning(parent, title, message):
        calls.append((title, message))

    monkeypatch.setattr(additional_input_module.QMessageBox, "warning", fake_warning)

    assert widget._warn_on_additional_form_conflicts(set()) is True
    assert calls
    assert "Form.With.Dot" in calls[0][1]


def test_apply_additional_inputs_aborts_on_form_name_conflict(monkeypatch):
    widget = DummyWidget()
    base_df = pd.DataFrame({"Subject": ["S1"], "A1": [1]})
    widget.report.set_data({"FormA": base_df})

    add_path = "/tmp/formA.csv"
    widget.additional_inputs[add_path] = pd.DataFrame({"Subject": ["S1"], "B1": [2]})
    widget.additional_form_names[add_path] = "FormA"

    def fake_warning(parent, title, message):
        return None

    monkeypatch.setattr(additional_input_module.QMessageBox, "warning", fake_warning)

    widget.click_apply_additional_forms()

    assert set(widget.report.data.keys()) == {"FormA"}
    assert widget.report.data["FormA"].equals(base_df)
    assert widget.update_all_ui_calls == 0
