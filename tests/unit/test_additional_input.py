import types

import pandas as pd
import pytest
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import (
    QApplication,
    QListWidget,
    QPushButton,
    QTableWidget,
)
from tests.unit.fakes import FakeBanner

from clinical_reporting import data, steps
from clinical_reporting.report import CLReport
from clinical_reporting.ui import additional_input_tab as additional_input_module
from clinical_reporting.ui.additional_input_tab import AdditionalInputTabMixin
from clinical_reporting.ui.base import WidgetBaseMixin


class DummyWidget(AdditionalInputTabMixin, WidgetBaseMixin):
    """Lightweight stand-in to exercise the mixin logic without Qt."""

    def __init__(self):
        # Initialize mixin state expected by the helpers.
        self.additional_inputs = {}
        self.additional_form_names = {}
        self.additional_column_names = {}
        self._additional_form_keys = set()
        self.report = CLReport()
        self.ui = types.SimpleNamespace(banner_additional=FakeBanner())
        self.update_all_ui_calls = 0

    def update_all_ui(self):
        self.update_all_ui_calls += 1


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class DummyAdditionalInputUiWidget(AdditionalInputTabMixin, WidgetBaseMixin):
    """Qt-backed stand-in for additional-input table interactions."""

    def __init__(self):
        self.report = CLReport()
        column_table = QTableWidget()
        column_table.setColumnCount(2)
        form_table = QTableWidget()
        form_table.setColumnCount(2)
        self.ui = types.SimpleNamespace(
            pushButton_additional_file_add=QPushButton(),
            pushButton_additional_file_remove=QPushButton(),
            pushButton_apply_additional_files=QPushButton(),
            listWidget_additional_file=QListWidget(),
            tableWidget_update_form_name=form_table,
            tableWidget_update_column_name=column_table,
            banner_additional=FakeBanner(),
        )
        self._init_additional_input_tab()


def test_context_action_copies_selected_new_columns_to_updated_names(qapp):
    widget = DummyAdditionalInputUiWidget()
    file_path = "C:/tmp/lab.csv"
    widget.additional_inputs[file_path] = pd.DataFrame(
        {"Subject": ["001"], "Result": [1.0], "Unit": ["mg"]}
    )
    widget._refresh_additional_files_ui()
    widget._refresh_additional_tables()
    table = widget.ui.tableWidget_update_column_name

    selection_model = table.selectionModel()
    for row in (0, 2):
        selection_model.select(
            table.model().index(row, 0),
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )

    widget.copy_new_column_name_action.trigger()

    assert table.item(0, 1).text() == "Subject"
    assert table.item(1, 1).text() == ""
    assert table.item(2, 1).text() == "Unit"
    assert widget.additional_column_names == {
        (file_path, "Subject"): "Subject",
        (file_path, "Unit"): "Unit",
    }


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


def _build_two_form_widget():
    """Widget with two selected forms (DM, AE) sharing a Subject common item."""
    widget = DummyWidget()
    widget.report.set_data(
        {
            "DM": pd.DataFrame({"Subject": ["001", "002"], "Age": [30, 40]}),
            "AE": pd.DataFrame({"Subject": ["001", "002"], "Event": ["x", "y"]}),
        }
    )
    widget.report.add_selected_form("DM")
    widget.report.add_selected_form("AE")
    widget.report.set_common_item_state("Subject", selected=True)
    return widget


def test_apply_additional_inputs_preserves_join_configuration():
    widget = _build_two_form_widget()
    # Configure a non-default join order/items/strategy on the existing forms.
    widget.report.update_join_items("DM", [], 1, "Left join")
    widget.report.update_join_items("AE", ["Subject"], 2, "Inner join")

    # Add an additional form that still shares Subject (so it stays common).
    add_path = "/tmp/lab.csv"
    widget.additional_inputs[add_path] = pd.DataFrame(
        {"Subject": ["001", "002"], "Result": [1.0, 2.0]}
    )
    widget.additional_form_names[add_path] = "LAB"

    widget.click_apply_additional_forms()

    # The previously configured join order/items/strategy survive the merge.
    ae = widget.report.selected_forms["AE"]
    assert ae.get_join_order() == 2
    assert ae.get_join_items() == ["Subject"]
    assert ae.get_join_how() == "Inner join"
    assert widget.report.selected_forms["DM"].get_join_order() == 1
    # The new form is merged into the data and available for selection.
    assert "LAB" in widget.report.data
    assert "LAB" in widget.report.available_forms


def test_apply_additional_inputs_drops_stale_join_item():
    widget = _build_two_form_widget()
    widget.report.update_join_items("AE", ["Subject"], 2, "Inner join")

    # This additional form shares no column, so Subject is no longer common.
    add_path = "/tmp/other.csv"
    widget.additional_inputs[add_path] = pd.DataFrame(
        {"Key": ["a", "b"], "Result": [1.0, 2.0]}
    )
    widget.additional_form_names[add_path] = "OTHER"

    widget.click_apply_additional_forms()

    ae = widget.report.selected_forms["AE"]
    # Order/strategy are retained, but the now-invalid join item is dropped.
    assert ae.get_join_order() == 2
    assert ae.get_join_items() == []


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


def test_warn_on_additional_form_conflicts_detects_duplicates():
    widget = DummyWidget()
    widget.additional_inputs["/tmp/a.csv"] = pd.DataFrame({"Subject": ["S1"]})
    widget.additional_inputs["/tmp/b.csv"] = pd.DataFrame({"Subject": ["S2"]})
    widget.additional_form_names["/tmp/a.csv"] = "DupForm"
    widget.additional_form_names["/tmp/b.csv"] = "DupForm"

    assert widget._warn_on_additional_form_conflicts(set()) is True
    shown = widget.ui.banner_additional.value
    assert "DupForm" in shown and shown.kind == "warning"


def test_warn_on_additional_form_conflicts_detects_dots():
    widget = DummyWidget()
    widget.additional_inputs["/tmp/a.csv"] = pd.DataFrame({"Subject": ["S1"]})
    widget.additional_form_names["/tmp/a.csv"] = "Form.With.Dot"

    assert widget._warn_on_additional_form_conflicts(set()) is True
    assert "Form.With.Dot" in widget.ui.banner_additional.value


def test_apply_additional_inputs_aborts_on_form_name_conflict():
    widget = DummyWidget()
    base_df = pd.DataFrame({"Subject": ["S1"], "A1": [1]})
    widget.report.set_data({"FormA": base_df})

    add_path = "/tmp/formA.csv"
    widget.additional_inputs[add_path] = pd.DataFrame({"Subject": ["S1"], "B1": [2]})
    widget.additional_form_names[add_path] = "FormA"

    widget.click_apply_additional_forms()

    assert set(widget.report.data.keys()) == {"FormA"}
    assert widget.report.data["FormA"].equals(base_df)
    assert widget.update_all_ui_calls == 0
    shown = widget.ui.banner_additional.value
    assert shown.startswith("These form names can't be used: FormA.")
    assert "Conflicts with existing report forms" in shown.details


def test_applying_says_what_it_added_and_nothing_without_files():
    widget = DummyWidget()
    widget.click_apply_additional_forms()
    nothing = widget.ui.banner_additional.value
    widget.additional_inputs["/tmp/lab.csv"] = pd.DataFrame({"Subject": ["S1"]})
    widget.additional_form_names["/tmp/lab.csv"] = "LB"

    widget.click_apply_additional_forms()
    applied = widget.ui.banner_additional.value
    widget.additional_inputs.clear()
    widget.click_apply_additional_forms()

    assert nothing == "Add at least one file first." and nothing.kind == "warning"
    assert applied == "1 file applied. New forms: LB." and applied.kind == "success"
    assert widget.ui.banner_additional.value.startswith("The additional forms were")
    assert widget.update_all_ui_calls == 2


def test_a_new_zip_asks_for_the_applied_files_again():
    widget = DummyWidget()
    widget._forget_applied_additional_forms()  # Nothing applied: nothing to say.
    quiet = widget.ui.banner_additional.value
    widget._additional_form_keys = {"LB"}

    widget._forget_applied_additional_forms()

    assert quiet == "" and widget._additional_form_keys == set()
    shown = widget.ui.banner_additional.value
    assert shown.kind == "info" and "Apply the files again" in shown


def test_files_that_cannot_be_read_are_reported_and_the_rest_added(
    qapp, monkeypatch, tmp_path
):
    widget = DummyAdditionalInputUiWidget()
    good, bad = tmp_path / "labs.csv", tmp_path / "broken.csv"

    def load(path):
        if path.endswith("broken.csv"):
            raise ValueError("Error tokenizing data")
        return pd.DataFrame({"Subject": ["001"]})

    monkeypatch.setattr(
        additional_input_module.QFileDialog,
        "getOpenFileNames",
        lambda *_args: ([str(good), str(bad)], ""),
    )
    monkeypatch.setattr(data, "load_tabular_file", load)

    widget.click_add_additional_files()

    assert list(widget.additional_inputs) == [str(good.resolve())]
    assert widget.ui.listWidget_additional_file.count() == 1
    shown = widget.ui.banner_additional.value
    assert shown == "These files could not be read and were not added: broken.csv."
    assert shown.kind == "warning"
    assert "broken.csv: Error tokenizing data" in shown.details


def test_a_later_add_that_reads_everything_clears_the_warning(qapp):
    widget = DummyAdditionalInputUiWidget()
    widget._add_loaded_additional_files(({}, {"bad.csv": "Error tokenizing data"}))
    warned = widget.ui.banner_additional.value
    widget._add_loaded_additional_files(({"good.csv": pd.DataFrame()}, {}))

    assert warned.startswith("These files could not be read")
    assert widget.ui.banner_additional.value == ""


def test_a_later_add_keeps_other_messages(qapp):
    widget = DummyAdditionalInputUiWidget()
    widget.ui.banner_additional.setText(steps.APPLY_ADDITIONAL_AGAIN)

    widget._add_loaded_additional_files(({"good.csv": pd.DataFrame()}, {}))

    assert widget.ui.banner_additional.value == steps.APPLY_ADDITIONAL_AGAIN


def test_a_later_add_clears_the_nothing_to_apply_warning(qapp):
    widget = DummyAdditionalInputUiWidget()
    widget.click_apply_additional_forms()
    warned = widget.ui.banner_additional.value

    widget._add_loaded_additional_files(({"good.csv": pd.DataFrame()}, {}))

    assert warned == steps.ADD_FILES_FIRST
    assert widget.ui.banner_additional.value == ""
