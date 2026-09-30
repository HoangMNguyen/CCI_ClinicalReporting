"""Successful-output integration tests for the silent run counter hook."""

from __future__ import annotations

import types

import pandas as pd

from clinical_reporting import session
from clinical_reporting.ui import run_save_tab
from clinical_reporting.ui.base import WidgetBaseMixin


class _Report:
    def __init__(self):
        self.builds = 0

    def validate(self):
        return []

    def create_report(self):
        self.builds += 1
        return pd.DataFrame({"Subject": ["001"]})

    def settings_to_dict(self, setting_name):
        return {"setting_name": setting_name}


class _Store:
    """Settings store that records writes, or fails with *error*."""

    def __init__(self, operations=None, error=None):
        self.operations = operations if operations is not None else []
        self.error = error

    def save(self, name, settings):
        if self.error is not None:
            raise self.error
        self.operations.append("write_setting")
        return f"settings/{name}.json"


class _LineEdit:
    def __init__(self, value="report"):
        self.value = value

    def text(self):
        return self.value


class _CheckBox:
    def __init__(self, checked):
        self.checked = checked

    def isChecked(self):  # noqa: N802 (Qt naming convention)
        return self.checked


class _Label:
    def __init__(self):
        self.value = ""


class _RunWidget(WidgetBaseMixin, run_save_tab.RunAndSaveMixin):
    def __init__(self, output_folder):
        self.report = _Report()
        self.output_folder_name = str(output_folder)
        self.settings_directory = str(output_folder)
        self.label_run_confirmation = _Label()
        self.label_save_confirmation = _Label()
        self.ui = types.SimpleNamespace(
            lineEdit_file_name=_LineEdit(),
            lineEdit_setting_name=_LineEdit("baseline"),
            checkBox_save_current_setting=_CheckBox(True),
            checkBox_saved_setting=_CheckBox(False),
        )

    @staticmethod
    def _set_label_text(label, text):
        label.value = text


def test_successful_export_records_one_run_after_writing(monkeypatch, tmp_path):
    operations = []
    monkeypatch.setattr(
        session, "write_xlsx", lambda *_args: operations.append("write")
    )
    monkeypatch.setattr(
        run_save_tab,
        "record_successful_export",
        lambda report_name: operations.append(("count", report_name)),
    )
    widget = _RunWidget(tmp_path)

    widget.click_run()

    assert operations[0] == "write"
    assert operations[1][0] == "count"
    assert operations[1][1].startswith("report ")
    assert operations[1][1].endswith(".xlsx")
    assert widget.label_run_confirmation.value.startswith("Report saved successfully")


def test_telemetry_failure_does_not_change_successful_save(monkeypatch, tmp_path):
    monkeypatch.setattr(session, "write_xlsx", lambda *_args: None)

    def fail_to_count(_report_name):
        raise RuntimeError("telemetry unavailable")

    monkeypatch.setattr(run_save_tab, "record_successful_export", fail_to_count)
    widget = _RunWidget(tmp_path)

    widget.click_run()

    assert widget.label_run_confirmation.value.startswith("Report saved successfully")


def test_failed_export_is_not_counted(monkeypatch, tmp_path):
    counted = []

    def fail_to_write(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(session, "write_xlsx", fail_to_write)
    monkeypatch.setattr(
        run_save_tab,
        "record_successful_export",
        lambda _report_name: counted.append(True),
    )
    widget = _RunWidget(tmp_path)

    widget.click_run()

    assert counted == []
    assert widget.label_run_confirmation.value.startswith("Error saving report")


def test_export_without_an_output_folder_builds_nothing(monkeypatch, tmp_path):
    written = []
    monkeypatch.setattr(session, "write_xlsx", lambda *args: written.append(args))
    widget = _RunWidget(tmp_path)
    widget.output_folder_name = None

    widget.click_run()

    assert widget.report.builds == 0 and written == []
    assert (
        widget.label_run_confirmation.value == "Please select an output folder first."
    )


def test_export_with_no_matching_rows_writes_nothing(monkeypatch, tmp_path):
    written = []
    monkeypatch.setattr(session, "write_xlsx", lambda *args: written.append(args))
    widget = _RunWidget(tmp_path)
    widget.report.create_report = lambda: pd.DataFrame()

    widget.click_run()

    assert written == []
    assert widget.label_run_confirmation.value.startswith("No data to save")


def test_successful_setting_save_is_counted_after_writing(monkeypatch, tmp_path):
    operations = []
    widget = _RunWidget(tmp_path)
    widget._settings_store = lambda: _Store(operations)
    monkeypatch.setattr(
        run_save_tab,
        "record_successful_setting_save",
        lambda setting_name: operations.append(("count_setting", setting_name)),
    )

    widget.click_save_setting()

    assert operations == ["write_setting", ("count_setting", "baseline")]
    assert widget.label_save_confirmation.value.startswith("Settings saved to")


def test_setting_telemetry_failure_does_not_change_successful_save(
    monkeypatch, tmp_path
):
    widget = _RunWidget(tmp_path)

    def fail_to_count(_setting_name):
        raise RuntimeError("telemetry unavailable")

    monkeypatch.setattr(run_save_tab, "record_successful_setting_save", fail_to_count)

    widget.click_save_setting()

    assert widget.label_save_confirmation.value.startswith("Settings saved to")


def test_failed_setting_save_is_not_counted(monkeypatch, tmp_path):
    widget = _RunWidget(tmp_path)
    widget._settings_store = lambda: _Store(error=OSError("disk full"))
    counted = []
    monkeypatch.setattr(
        run_save_tab,
        "record_successful_setting_save",
        lambda _setting_name: counted.append(True),
    )

    widget.click_save_setting()

    assert counted == []
    assert widget.label_save_confirmation.value.startswith("Failed to save settings")
