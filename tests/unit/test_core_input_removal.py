"""Tests for removing the selected Corelisting ZIP from the workspace."""

from unittest.mock import MagicMock

import pandas as pd
from tests.unit.fakes import FakePathPicker, FakeSection, FakeTableView

from clinical_reporting.report import CLReport
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.run_save_tab import RunAndSaveMixin
from clinical_reporting.ui.settings_tab import SettingsTabMixin


class _TextWidget:
    def __init__(self):
        self.text = None
        self.enabled = True

    def setText(self, text):
        self.text = text

    def setEnabled(self, enabled):
        self.enabled = enabled


class _ComboBox:
    def __init__(self):
        self.cleared = False
        self.enabled = True

    def clear(self):
        self.cleared = True

    def setEnabled(self, enabled):
        self.enabled = enabled


class _Ui:
    def __init__(self):
        self.pathPicker_input_file = FakePathPicker("corelisting.zip")
        self.section_input_file = FakeSection()
        self.tableView_preview = FakeTableView()
        self.banner_input_file = _TextWidget()
        self.pushButton_remove_input = _TextWidget()
        self.comboBox_saved_setting = _ComboBox()


class _RemovalWidget(SettingsTabMixin, RunAndSaveMixin, WidgetBaseMixin):
    def __init__(self):
        self.ui = _Ui()
        self.report = CLReport()
        self.study_name = "STUDY01"
        self._input_file_path = "corelisting.zip"
        self._applied_cut_off_date = "2026-01-01"
        self._last_loaded_setting_path = "settings.json"
        self._pending_saved_setting_reapply = True
        self._additional_form_keys = {"Extra"}
        self.label_setting = _TextWidget()
        self.label_run_confirmation = _TextWidget()
        self.label_save_confirmation = _TextWidget()
        self.update_all_ui_calls = 0
        self.update_items_dependent_ui_calls = 0

    def update_all_ui(self):
        self.update_all_ui_calls += 1

    def update_items_dependent_ui(self):
        self.update_items_dependent_ui_calls += 1


def test_settings_tab_connects_remove_input_button():
    widget = SettingsTabMixin()
    widget.ui = MagicMock()
    widget._input_file_path = None

    widget._init_settings_tab()

    widget.ui.pushButton_remove_input.clicked.connect.assert_called_once_with(
        widget.click_remove_input
    )
    widget.ui.pushButton_remove_input.setEnabled.assert_called_once_with(False)


def test_remove_input_clears_core_data_and_preserves_additional_forms():
    widget = _RemovalWidget()
    widget.report.set_study_name(widget.study_name)
    widget.report.set_data(
        {
            "CoreForm": pd.DataFrame({"Subject": ["001"], "CoreValue": [1]}),
            "Extra": pd.DataFrame({"Subject": ["001"], "ExtraValue": [2]}),
        }
    )
    widget.report.add_selected_form("CoreForm")
    widget.report.add_selected_form("Extra")
    widget.report.static_filter_items = [("CoreForm.CoreValue", "=", "1")]

    widget.click_remove_input()

    assert set(widget.report.data) == {"Extra"}
    assert set(widget.report.selected_forms) == {"Extra"}
    assert widget.ui.tableView_preview.model() is None  # The old preview goes.
    assert widget.report.static_filter_items == []
    assert widget.report.study_name is None
    assert widget.study_name is None
    assert widget._input_file_path is None
    assert widget._applied_cut_off_date is None
    assert widget._last_loaded_setting_path is None
    assert widget._pending_saved_setting_reapply is False
    assert widget.ui.pathPicker_input_file.path() == ""
    assert widget.ui.banner_input_file.text == ""
    assert widget.ui.pushButton_remove_input.enabled is False
    assert widget.ui.comboBox_saved_setting.cleared is True
    assert widget.ui.comboBox_saved_setting.enabled is False
    assert widget.update_all_ui_calls == 1
    # update_all_ui now refreshes the item-dependent tables itself, so the
    # removal path must not stack a second refresh on top of it.
    assert widget.update_items_dependent_ui_calls == 0


def test_remove_input_with_no_additional_forms_leaves_empty_report():
    widget = _RemovalWidget()
    widget._additional_form_keys = set()
    widget.report.set_data(
        {"CoreForm": pd.DataFrame({"Subject": ["001"], "CoreValue": [1]})}
    )

    widget.click_remove_input()

    assert widget.report.data == {}
    assert widget.report.available_forms == {}
    assert widget.report.selected_forms == {}

