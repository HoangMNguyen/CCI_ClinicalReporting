"""Messages shown when a saved setting is loaded or its folder is chosen."""

import types

import pandas as pd

from clinical_reporting import feedback
from clinical_reporting.report import CLReport
from clinical_reporting.ui import dialogs
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.settings_tab import SettingsTabMixin


class _Label:
    def __init__(self):
        self.value = ""

    def setText(self, text):  # noqa: N802 (Qt naming convention)
        self.value = text


class _Store:
    def __init__(self, stored=None, error=None):
        self.stored = stored
        self.error = error

    def load(self, _path):
        if self.error is not None:
            raise self.error
        return self.stored


class _SettingsWidget(SettingsTabMixin, WidgetBaseMixin):
    def __init__(self, store=None):
        self.report = CLReport()
        self.report.set_data({"DM": pd.DataFrame({"Subject": ["001"], "Age": [54]})})
        self.study_name = "DEMO01"
        self.settings_directory = None
        self.label_setting = _Label()
        self.label_save_confirmation = _Label()
        self._pending_saved_setting_reapply = False
        self._store = store
        self.ui = types.SimpleNamespace(
            checkBox_saved_setting=types.SimpleNamespace(isChecked=lambda: False)
        )

    def _settings_store(self):
        return self._store

    def update_all_ui(self):
        pass


def _setting_with_forms(*forms):
    source = CLReport()
    source.set_data(
        {form: pd.DataFrame({"Subject": ["001"], f"{form}X": [1]}) for form in forms}
    )
    for form in forms:
        source.add_selected_form(form)
    return source.settings_to_dict("monthly")


def test_loading_a_setting_is_a_success():
    widget = _SettingsWidget(_Store(_setting_with_forms("DM")))

    assert widget._apply_saved_setting_from_path("monthly.json")

    shown = widget.label_save_confirmation.value
    assert shown == "Loaded settings from monthly.json"
    assert feedback.kind_of(shown) == "success"
    assert widget.label_setting.value == ""


def test_a_setting_with_missing_forms_warns():
    widget = _SettingsWidget(_Store(_setting_with_forms("DM", "AE")))

    widget._apply_saved_setting_from_path("monthly.json")

    assert widget.label_setting.value.startswith("Missing forms: AE")
    assert feedback.kind_of(widget.label_setting.value) == "warning"


def test_a_setting_that_cannot_be_read_is_an_error_with_details():
    widget = _SettingsWidget(_Store(error=ValueError("bad json")))

    assert not widget._apply_saved_setting_from_path("monthly.json")

    shown = widget.label_save_confirmation.value
    assert shown == "Failed to load settings: bad json"
    assert feedback.kind_of(shown) == "error"
    assert "ValueError: bad json" in shown.details


def test_choosing_the_settings_folder_is_confirmed(monkeypatch):
    widget = _SettingsWidget()
    widget._get_default_settings_directory = lambda: "C:/Users/test/Documents"
    monkeypatch.setattr(
        dialogs.QFileDialog,
        "getExistingDirectory",
        lambda *_args: "D:/Study/Settings",
    )

    dialogs.choose_settings_directory(widget)

    shown = widget.label_save_confirmation.value
    assert shown == "Settings folder set to D:/Study/Settings"
    assert feedback.kind_of(shown) == "info"
