"""Tests for retaining the selected settings directory in folder dialogs."""

import pandas as pd
from tests.unit.fakes import FakeBanner, FakeCheckBox, FakePathPicker

from clinical_reporting import data
from clinical_reporting.ui import dialogs
from clinical_reporting.ui.pages import additional_input, source_data
from clinical_reporting.ui.pages.additional_input import AdditionalInputMixin
from clinical_reporting.ui.pages.preview_export import PreviewExportMixin
from clinical_reporting.ui.pages.source_data import SourceDataMixin


class _WorkspaceWidget(SourceDataMixin):
    def __init__(self):
        self.settings_directory = None
        self.output_folder_name = None
        self.label_save_confirmation = None
        self.ui = type(
            "Ui",
            (),
            {
                "checkBox_saved_setting": FakeCheckBox(False),
                "pathPicker_output_folder": FakePathPicker(),
                "pathPicker_settings_folder": FakePathPicker(),
            },
        )()

    def _get_default_settings_directory(self):
        return "C:/Users/test/Documents"

    def _set_label_text(self, _label, _text):
        pass


class _OutputWidget(PreviewExportMixin):
    def __init__(self):
        self.settings_directory = None
        self.label_save_confirmation = None
        self.ui = type(
            "Ui",
            (),
            {
                "checkBox_save_current_setting": FakeCheckBox(True),
                "checkBox_saved_setting": FakeCheckBox(False),
            },
        )()

    def _get_default_settings_directory(self):
        return "C:/Users/test/Documents"

    def _set_label_text(self, _label, _text):
        pass


class _AdditionalInputWidget(AdditionalInputMixin):
    def __init__(self):
        self._additional_input_directory = None
        self.additional_inputs = {}
        self.ui = type("Ui", (), {})()
        self.ui.banner_additional = FakeBanner()

    def _refresh_additional_files_ui(self):
        pass

    def _refresh_additional_tables(self):
        pass

    def _update_additional_buttons_state(self):
        pass

    def apply_data_steps(self):
        pass  # The window's: brings the Data steps to the report.


def _assert_dialog_remembers_selection(monkeypatch, module, widget, click_method):
    initial_directories = []
    selections = iter(("D:/Study/Settings", "E:/Other/Settings"))

    def choose_directory(_parent, _title, initial_directory):
        initial_directories.append(initial_directory)
        return next(selections)

    monkeypatch.setattr(module.QFileDialog, "getExistingDirectory", choose_directory)

    click_method(widget)
    click_method(widget)

    assert initial_directories == [
        "C:/Users/test/Documents",
        "D:/Study/Settings",
    ]
    assert widget.settings_directory == "E:/Other/Settings"


def test_saved_settings_folder_dialog_remembers_last_selection(monkeypatch):
    widget = _WorkspaceWidget()

    _assert_dialog_remembers_selection(
        monkeypatch,
        dialogs,
        widget,
        SourceDataMixin.click_setting_location,
    )


def test_output_settings_folder_dialog_remembers_last_selection(monkeypatch):
    widget = _OutputWidget()

    # Both buttons share dialogs.choose_settings_directory, so the dialog
    # is patched on the dialogs module for the Preview & export page too.
    _assert_dialog_remembers_selection(
        monkeypatch,
        dialogs,
        widget,
        PreviewExportMixin.click_output_setting_folder,
    )


def test_settings_folder_selection_is_shared_between_first_and_last_pages(monkeypatch):
    class _LinkedWidget(_WorkspaceWidget, PreviewExportMixin):
        def __init__(self):
            super().__init__()
            self.ui.checkBox_save_current_setting = FakeCheckBox(True)

    widget = _LinkedWidget()
    initial_directories = []
    selections = iter(("D:/Shared/Settings", "E:/Updated/Settings"))

    def choose_directory(_parent, _title, initial_directory):
        initial_directories.append(initial_directory)
        return next(selections)

    monkeypatch.setattr(
        dialogs.QFileDialog,
        "getExistingDirectory",
        choose_directory,
    )

    widget.click_setting_location()
    widget.click_output_setting_folder()

    assert initial_directories == [
        "C:/Users/test/Documents",
        "D:/Shared/Settings",
    ]
    assert widget.settings_directory == "E:/Updated/Settings"


def test_turning_on_saved_settings_remembers_the_default_folder(
    sample_window, monkeypatch, tmp_path
):
    """With no folder chosen yet, turning saved settings on remembers ~/Documents."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    sample_window.ui.checkBox_saved_setting.setChecked(True)

    assert sample_window.settings_directory == str(tmp_path / "Documents")


def test_output_folder_dialog_remembers_last_selection(monkeypatch):
    widget = _WorkspaceWidget()
    initial_directories = []
    selections = iter(("D:/Study/Reports", "E:/Other/Reports"))

    def choose_directory(_parent, _title, initial_directory):
        initial_directories.append(initial_directory)
        return next(selections)

    monkeypatch.setattr(
        source_data.QFileDialog,
        "getExistingDirectory",
        choose_directory,
    )

    widget.click_output_file()
    widget.click_output_file()

    assert initial_directories[1] == "D:/Study/Reports"
    assert widget.output_folder_name == "E:/Other/Reports"
    assert widget.ui.pathPicker_output_folder.path() == "E:/Other/Reports"


def test_additional_input_dialog_remembers_last_file_directory(monkeypatch, tmp_path):
    widget = _AdditionalInputWidget()
    first_directory = tmp_path / "first"
    second_directory = tmp_path / "second"
    first_file = first_directory / "first.csv"
    second_file = second_directory / "second.csv"
    initial_directories = []
    selections = iter(([str(first_file)], [str(second_file)]))

    def choose_files(_parent, _title, initial_directory, _filter):
        initial_directories.append(initial_directory)
        return next(selections), ""

    monkeypatch.setattr(additional_input.QFileDialog, "getOpenFileNames", choose_files)
    monkeypatch.setattr(data, "load_tabular_file", lambda _path: pd.DataFrame())

    widget.click_add_additional_files()
    widget.click_add_additional_files()

    assert initial_directories[1] == str(first_directory.resolve())
    assert widget._additional_input_directory == str(second_directory.resolve())
