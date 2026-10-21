"""Successful-output integration tests for the silent run counter hook."""

from __future__ import annotations

import types

import pandas as pd
import pytest
from tests.unit.fakes import FakeBanner, FakeCheckBox
from xlsxwriter.exceptions import FileCreateError

from clinical_reporting import session
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.pages import preview_export


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


class _RunWidget(WidgetBaseMixin, preview_export.PreviewExportMixin):
    def __init__(self, output_folder):
        self.report = _Report()
        self.output_folder_name = str(output_folder)
        self.settings_directory = str(output_folder)
        self.label_run_confirmation = FakeBanner()
        self.label_save_confirmation = FakeBanner()
        self.ui = types.SimpleNamespace(
            lineEdit_file_name=_LineEdit(),
            checkBox_add_date_time=FakeCheckBox(True),
            lineEdit_setting_name=_LineEdit("baseline"),
            checkBox_save_current_setting=FakeCheckBox(True),
            checkBox_saved_setting=FakeCheckBox(False),
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
        preview_export,
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
    assert widget.label_run_confirmation.value.kind == "success"


def test_telemetry_failure_does_not_change_successful_save(monkeypatch, tmp_path):
    monkeypatch.setattr(session, "write_xlsx", lambda *_args: None)

    def fail_to_count(_report_name):
        raise RuntimeError("telemetry unavailable")

    monkeypatch.setattr(preview_export, "record_successful_export", fail_to_count)
    widget = _RunWidget(tmp_path)

    widget.click_run()

    assert widget.label_run_confirmation.value.startswith("Report saved successfully")


def test_failed_export_is_not_counted(monkeypatch, tmp_path):
    counted = []

    def fail_to_write(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(session, "write_xlsx", fail_to_write)
    monkeypatch.setattr(
        preview_export,
        "record_successful_export",
        lambda _report_name: counted.append(True),
    )
    widget = _RunWidget(tmp_path)

    widget.click_run()

    assert counted == []
    assert widget.label_run_confirmation.value.startswith("Error saving report")
    assert widget.label_run_confirmation.value.kind == "error"
    assert "disk full" in widget.label_run_confirmation.value.details


def test_export_without_an_output_folder_builds_nothing(monkeypatch, tmp_path):
    written = []
    monkeypatch.setattr(session, "write_xlsx", lambda *args: written.append(args))
    widget = _RunWidget(tmp_path)
    widget.output_folder_name = None

    widget.click_run()

    # Export to Excel is disabled then, and the folder marked: nothing to say.
    assert widget.report.builds == 0 and written == []
    assert widget.label_run_confirmation.value == ""


@pytest.mark.parametrize("name", ["", "   ", ".xlsx"])
def test_export_without_a_file_name_builds_nothing(monkeypatch, tmp_path, name):
    written = []
    monkeypatch.setattr(session, "write_xlsx", lambda *args: written.append(args))
    widget = _RunWidget(tmp_path)
    widget.ui.lineEdit_file_name = _LineEdit(name)

    widget.click_run()

    # Export to Excel is disabled then, and the name marked: nothing to say.
    assert widget.report.builds == 0 and written == []
    assert widget.label_run_confirmation.value == ""


def test_export_without_the_date_and_time_writes_just_the_name(monkeypatch, tmp_path):
    written = []
    monkeypatch.setattr(session, "write_xlsx", lambda _df, path: written.append(path))
    widget = _RunWidget(tmp_path)
    widget.ui.checkBox_add_date_time = FakeCheckBox(False)

    widget.click_run()

    assert written == [str(tmp_path / "report.xlsx")]


def _export_over_a_file(monkeypatch, tmp_path, replace):
    """Export "report.xlsx" into a folder that has one; *replace* answers."""
    written, asked = [], []
    monkeypatch.setattr(session, "write_xlsx", lambda _df, path: written.append(path))
    monkeypatch.setattr(
        preview_export,
        "ask_to_replace",
        lambda _parent, file_name: asked.append(file_name) or replace,
    )
    (tmp_path / "report.xlsx").write_bytes(b"old")
    widget = _RunWidget(tmp_path)
    widget.ui.checkBox_add_date_time = FakeCheckBox(False)
    widget.click_run()
    return widget, asked, written


def test_keeping_a_file_already_there_writes_nothing(monkeypatch, tmp_path):
    widget, asked, written = _export_over_a_file(monkeypatch, tmp_path, False)

    assert asked == ["report.xlsx"]
    assert widget.report.builds == 0 and written == []
    assert widget.label_run_confirmation.value == ""


def test_replacing_a_file_already_there_writes_it(monkeypatch, tmp_path):
    widget, asked, written = _export_over_a_file(monkeypatch, tmp_path, True)

    assert asked == ["report.xlsx"]
    assert written == [str(tmp_path / "report.xlsx")]
    assert widget.label_run_confirmation.value.kind == "success"


def test_a_new_file_is_written_without_asking(monkeypatch, tmp_path):
    written, asked = [], []
    monkeypatch.setattr(session, "write_xlsx", lambda _df, path: written.append(path))
    monkeypatch.setattr(
        preview_export, "ask_to_replace", lambda *args: asked.append(args) or False
    )
    widget = _RunWidget(tmp_path)
    widget.ui.checkBox_add_date_time = FakeCheckBox(False)

    widget.click_run()

    assert asked == []
    assert written == [str(tmp_path / "report.xlsx")]


def _refused(*_args):
    raise PermissionError(13, "Permission denied", "report.xlsx")


def _refused_to_xlsxwriter(*_args):
    try:
        _refused()
    except OSError as error:
        raise FileCreateError(error)  # As xlsxwriter would, opening the path itself.


@pytest.mark.parametrize("write", [_refused, _refused_to_xlsxwriter])
def test_a_file_open_in_excel_says_to_close_it(monkeypatch, tmp_path, write):
    counted = []
    monkeypatch.setattr(session, "write_xlsx", write)
    monkeypatch.setattr(
        preview_export,
        "record_successful_export",
        lambda _report_name: counted.append(True),
    )
    widget = _RunWidget(tmp_path)
    widget.ui.checkBox_add_date_time = FakeCheckBox(False)

    widget.click_run()

    message = widget.label_run_confirmation.value
    assert counted == []
    assert message == (
        "Couldn't save report.xlsx. If it's open in Excel, close it, then export again."
    )
    assert message.kind == "error"
    assert "PermissionError" in message.details


def test_export_with_no_matching_rows_writes_nothing(monkeypatch, tmp_path):
    written = []
    monkeypatch.setattr(session, "write_xlsx", lambda *args: written.append(args))
    widget = _RunWidget(tmp_path)
    widget.report.create_report = lambda: pd.DataFrame()

    widget.click_run()

    assert written == []
    assert widget.label_run_confirmation.value.startswith("No data to save")
    assert widget.label_run_confirmation.value.kind == "warning"


def test_successful_setting_save_is_counted_after_writing(monkeypatch, tmp_path):
    operations = []
    widget = _RunWidget(tmp_path)
    widget._settings_store = lambda: _Store(operations)
    monkeypatch.setattr(
        preview_export,
        "record_successful_setting_save",
        lambda setting_name: operations.append(("count_setting", setting_name)),
    )

    widget.click_save_setting()

    assert operations == ["write_setting", ("count_setting", "baseline")]
    assert widget.label_save_confirmation.value.startswith("Settings saved to")
    assert widget.label_save_confirmation.value.kind == "success"


def test_setting_telemetry_failure_does_not_change_successful_save(
    monkeypatch, tmp_path
):
    widget = _RunWidget(tmp_path)

    def fail_to_count(_setting_name):
        raise RuntimeError("telemetry unavailable")

    monkeypatch.setattr(preview_export, "record_successful_setting_save", fail_to_count)

    widget.click_save_setting()

    assert widget.label_save_confirmation.value.startswith("Settings saved to")


def test_failed_setting_save_is_not_counted(monkeypatch, tmp_path):
    widget = _RunWidget(tmp_path)
    widget._settings_store = lambda: _Store(error=OSError("disk full"))
    counted = []
    monkeypatch.setattr(
        preview_export,
        "record_successful_setting_save",
        lambda _setting_name: counted.append(True),
    )

    widget.click_save_setting()

    assert counted == []
    assert widget.label_save_confirmation.value.startswith("Failed to save settings")
    assert widget.label_save_confirmation.value.kind == "error"
    assert "OSError: disk full" in widget.label_save_confirmation.value.details
