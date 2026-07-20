"""Successful-output integration tests for the silent run counter hook."""

from __future__ import annotations

import types

import pandas as pd

from clinical_reporting.ui import output


class _Report:
    def validate(self):
        return []

    def create_report(self):
        return pd.DataFrame({"Subject": ["001"]})


class _LineEdit:
    def text(self):
        return "report"


class _Label:
    def __init__(self):
        self.value = ""


class _RunWidget(output.RunAndSaveMixin):
    def __init__(self, output_folder):
        self.report = _Report()
        self.output_folder_name = str(output_folder)
        self.label_run_confirmation = _Label()
        self.ui = types.SimpleNamespace(lineEdit_file_name=_LineEdit())

    @staticmethod
    def _set_label_text(label, text):
        label.value = text


def test_successful_export_records_one_run_after_writing(monkeypatch, tmp_path):
    operations = []
    monkeypatch.setattr(output, "write_xlsx", lambda *_args: operations.append("write"))
    monkeypatch.setattr(
        output,
        "record_successful_export",
        lambda: operations.append("count"),
    )
    widget = _RunWidget(tmp_path)

    widget.click_run()

    assert operations == ["write", "count"]
    assert widget.label_run_confirmation.value.startswith("Report saved successfully")


def test_telemetry_failure_does_not_change_successful_save(monkeypatch, tmp_path):
    monkeypatch.setattr(output, "write_xlsx", lambda *_args: None)

    def fail_to_count():
        raise RuntimeError("telemetry unavailable")

    monkeypatch.setattr(output, "record_successful_export", fail_to_count)
    widget = _RunWidget(tmp_path)

    widget.click_run()

    assert widget.label_run_confirmation.value.startswith("Report saved successfully")


def test_failed_export_is_not_counted(monkeypatch, tmp_path):
    counted = []

    def fail_to_write(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(output, "write_xlsx", fail_to_write)
    monkeypatch.setattr(output, "record_successful_export", lambda: counted.append(True))
    widget = _RunWidget(tmp_path)

    widget.click_run()

    assert counted == []
    assert widget.label_run_confirmation.value.startswith("Error saving report")
