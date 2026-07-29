"""Tests for re-applying the cut-off date after an input file is loaded.

The cut-off filters rows while the ZIP is read, so changing the checkbox or
the date after loading must re-read the data. These tests exercise
``SettingsTabMixin._reload_with_current_cut_off`` without Qt by faking the
few UI widgets it touches and monkeypatching the loader.
"""

import datetime

import pandas as pd

from clinical_reporting.report import CLReport
from clinical_reporting.ui import settings_tab as settings_module
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.settings_tab import SettingsTabMixin


class _FakeCheckBox:
    def __init__(self, checked=False):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _FakeQDate:
    def __init__(self, value):
        self._value = value

    def toPython(self):
        return self._value


class _FakeDateEdit:
    def __init__(self, value):
        self._date = _FakeQDate(value)

    def date(self):
        return self._date


class _FakeUi:
    def __init__(self, checked, date_value):
        self.cutoff_checkBox = _FakeCheckBox(checked)
        self.cutoff_dateEdit = _FakeDateEdit(date_value)


class DummySettingsWidget(SettingsTabMixin, WidgetBaseMixin):
    """Stand-in exercising the settings mixin logic without Qt."""

    def __init__(self, checked, date_value):
        self.report = CLReport()
        self.ui = _FakeUi(checked, date_value)
        self._input_file_path = None
        self._applied_cut_off_date = None
        self._additional_form_keys = set()
        self.update_all_ui_calls = 0
        self.update_items_dependent_ui_calls = 0

    def update_all_ui(self):
        self.update_all_ui_calls += 1

    def update_items_dependent_ui(self):
        self.update_items_dependent_ui_calls += 1


def _loader(path, cut_off_date=None):
    """Fake corelisting reader: two rows, filtered by Event Date <= cut-off."""
    df = pd.DataFrame(
        {
            "Subject": ["001", "002"],
            "Event Date": pd.to_datetime(["2024-01-01", "2024-12-01"]),
            "Val": [1, 2],
        }
    )
    if cut_off_date is not None:
        df = df[df["Event Date"] <= pd.to_datetime(cut_off_date)]
    return {"FormA": df.reset_index(drop=True)}


def test_reload_applies_cutoff_and_preserves_selection(monkeypatch):
    monkeypatch.setattr(settings_module, "read_data_dict_zip_corelisting", _loader)

    # Initial load with no cut-off (checkbox unchecked); user selects FormA.
    widget = DummySettingsWidget(checked=False, date_value=datetime.date(2024, 6, 1))
    widget._input_file_path = "study.zip"
    widget.report.set_data(_loader("study.zip", None))
    widget.report.add_selected_form("FormA")
    assert len(widget.report.data["FormA"]) == 2

    # User checks the box, opting into the 2024-06-01 cut-off.
    widget.ui.cutoff_checkBox._checked = True
    widget._reload_with_current_cut_off()

    # Data re-read and filtered (only the 2024-01-01 row survives).
    assert widget._applied_cut_off_date == datetime.date(2024, 6, 1)
    assert len(widget.report.data["FormA"]) == 1
    # Selection survives the reload.
    assert "FormA" in widget.report.selected_forms
    assert widget.update_all_ui_calls == 1
    # update_all_ui now refreshes the item-dependent tables itself, so the
    # reload path must not stack a second refresh on top of it.
    assert widget.update_items_dependent_ui_calls == 0


def test_reload_is_noop_without_input_file(monkeypatch):
    calls = []

    def tracking_loader(path, cut_off_date=None):
        calls.append(path)
        return {}

    monkeypatch.setattr(settings_module, "read_data_dict_zip_corelisting", tracking_loader)

    widget = DummySettingsWidget(checked=True, date_value=datetime.date(2024, 6, 1))
    widget._reload_with_current_cut_off()

    assert calls == []
    assert widget.update_all_ui_calls == 0


def test_reload_is_noop_when_cutoff_unchanged(monkeypatch):
    calls = []

    def tracking_loader(path, cut_off_date=None):
        calls.append(cut_off_date)
        return _loader(path, cut_off_date)

    monkeypatch.setattr(settings_module, "read_data_dict_zip_corelisting", tracking_loader)

    # Checkbox unchecked -> effective cut-off is None, matching the applied None.
    widget = DummySettingsWidget(checked=False, date_value=datetime.date(2024, 6, 1))
    widget._input_file_path = "study.zip"
    widget._applied_cut_off_date = None
    widget._reload_with_current_cut_off()

    assert calls == []
    assert widget.update_all_ui_calls == 0


def test_unchecking_removes_cutoff_filter(monkeypatch):
    monkeypatch.setattr(settings_module, "read_data_dict_zip_corelisting", _loader)

    # Loaded with a cut-off already applied (only one row present).
    widget = DummySettingsWidget(checked=True, date_value=datetime.date(2024, 6, 1))
    widget._input_file_path = "study.zip"
    widget.report.set_data(_loader("study.zip", datetime.date(2024, 6, 1)))
    widget._applied_cut_off_date = datetime.date(2024, 6, 1)
    assert len(widget.report.data["FormA"]) == 1

    # User unchecks the box -> cut-off removed, all rows return.
    widget.ui.cutoff_checkBox._checked = False
    widget._reload_with_current_cut_off()

    assert widget._applied_cut_off_date is None
    assert len(widget.report.data["FormA"]) == 2
