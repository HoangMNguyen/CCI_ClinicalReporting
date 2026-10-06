"""Messages shown when a saved setting is loaded or its folder is chosen."""

import types

import pandas as pd
from PySide6.QtWidgets import QComboBox
from tests.unit.fakes import FakeBanner

from clinical_reporting import feedback
from clinical_reporting.additional_names import SETTINGS_KEY, from_settings
from clinical_reporting.report import CLReport
from clinical_reporting.settings_store import SavedSetting
from clinical_reporting.ui import dialogs
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.settings_tab import SettingsTabMixin


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
        self.label_setting = FakeBanner()
        self.label_save_confirmation = FakeBanner()
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

    # No saved names for AE, so no hint about additional files.
    assert widget.label_setting.value == "Missing forms: AE"
    assert feedback.kind_of(widget.label_setting.value) == "warning"


class _Combo:
    """The saved-setting dropdown: a placeholder, then one setting."""

    def __init__(self):
        self.entries = [("Choose a setting…", None), ("monthly", "monthly.json")]
        self.index = 0

    def itemData(self, index):  # noqa: N802 (Qt naming)
        return self.entries[index][1]

    def currentText(self):  # noqa: N802 (Qt naming)
        return self.entries[self.index][0]


class _OfferingWidget(_SettingsWidget):
    """A window whose Additional input page takes a setting's saved names."""

    def __init__(self, store=None):
        super().__init__(store)
        self.offers = []
        self.forgotten = 0
        self.added = []
        self._saved_additional_names = []
        self._last_loaded_setting_path = None
        self.ui.comboBox_saved_setting = _Combo()
        self.ui.lineEdit_setting_name = FakeBanner()

    def _offer_saved_additional_names(self, entries, setting_name, used_forms=None):
        self.offers.append((entries, setting_name, used_forms))
        self._saved_additional_names = list(entries)

    def _saved_names_added(self):
        return self.added

    def _forget_saved_additional_names(self):
        self.forgotten += 1
        self._saved_additional_names = []

    def pick(self, index):
        self.ui.comboBox_saved_setting.index = index
        self.on_saved_setting_changed(index)


def _setting_with_saved_names(*forms):
    settings = _setting_with_forms("DM", *forms)
    settings[SETTINGS_KEY] = [
        {"file_name": f"{form.lower()}_results.csv", "form_name": form}
        for form in forms
    ]
    return settings


def test_picking_a_setting_offers_its_saved_names_and_names_the_files():
    stored = _setting_with_saved_names("LAB", "PK")
    widget = _OfferingWidget(_Store(stored))

    widget.pick(1)

    assert widget.offers == [(from_settings(stored), "monthly", {"DM", "LAB", "PK"})]
    assert widget._last_loaded_setting_path == "monthly.json"
    assert widget.label_setting.value == (
        "Missing forms: LAB, PK\n"
        "LAB and PK come from additional files. Add lab_results.csv and "
        "pk_results.csv on Additional input, and their saved names will be "
        "picked for you."
    )
    assert feedback.kind_of(widget.label_setting.value) == "warning"


def test_re_applying_the_setting_leaves_the_saved_names_alone():
    widget = _OfferingWidget(_Store(_setting_with_saved_names("LAB")))

    # As after "Apply to report" on the Additional input page.
    assert widget._apply_saved_setting_from_path(
        "monthly.json", update_confirmation=False
    )

    assert widget.offers == []


def test_a_setting_without_saved_names_offers_none():
    widget = _OfferingWidget(_Store(_setting_with_forms("DM")))

    widget.pick(1)

    assert widget.offers == [([], "monthly", {"DM"})]


def test_forgetting_the_setting_takes_its_saved_names_away():
    widget = _OfferingWidget(_Store(_setting_with_saved_names("LAB")))
    widget.pick(1)

    widget.pick(0)  # Back to "Choose a setting…".

    assert widget.forgotten == 1
    assert widget._last_loaded_setting_path is None
    assert widget._pending_saved_setting_reapply is False
    assert widget.label_setting.value == ""


def test_a_setting_that_fails_to_load_forgets_the_one_before():
    widget = _OfferingWidget(_Store(_setting_with_saved_names("LAB")))
    widget.pick(1)
    widget._store = _Store(error=ValueError("bad json"))

    widget.pick(1)

    assert widget.forgotten == 1
    assert widget._last_loaded_setting_path is None


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


def test_files_already_added_are_to_be_checked_and_applied():
    stored = _setting_with_saved_names("LAB", "PK")
    widget = _OfferingWidget(_Store(stored))
    widget.added = [
        entry for entry in from_settings(stored) if entry.form_name == "LAB"
    ]

    widget.pick(1)

    assert widget.label_setting.value == (
        "Missing forms: LAB, PK\n"
        "PK comes from an additional file. Add pk_results.csv on Additional "
        "input, and its saved names will be picked for you. The file for LAB is "
        "added: check its form name on Additional input, then Apply to report."
    )


class _ListingStore:
    def list(self, _study_name):
        return [
            SavedSetting("monthly", "monthly.json"),
            SavedSetting("weekly", "w.json"),
        ]


def test_the_loaded_setting_stays_shown_when_the_list_is_refreshed(qapp):
    widget = _SettingsWidget(_ListingStore())
    widget.ui.comboBox_saved_setting = QComboBox()
    widget.ui.comboBox_saved_setting.setPlaceholderText("Choose a setting…")
    combo = widget.ui.comboBox_saved_setting

    widget._last_loaded_setting_path = "w.json"
    widget._refresh_saved_settings()  # As after a save.
    loaded = combo.currentText()
    widget._last_loaded_setting_path = "gone.json"  # Not in this folder.
    widget._refresh_saved_settings()
    elsewhere = combo.currentIndex()
    widget._last_loaded_setting_path = None
    widget._refresh_saved_settings()

    assert loaded == "weekly"
    assert elsewhere == 0
    assert combo.currentIndex() == 0 and combo.itemData(0) is None
