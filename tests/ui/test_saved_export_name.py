"""The export's file name, saved with a setting and filled in by picking it.

On the DEMO01 sample window (``sample_window`` in ``tests/ui/conftest.py``):
Save setting keeps File name and Add the date and time, and picking the
setting on Source data fills them back in; a setting saved without them
clears File name and ticks the box.
"""

import json
import logging

import pytest
from PySide6.QtWidgets import QApplication

from clinical_reporting.export_name import SETTINGS_KEY
from clinical_reporting.sample_data import STUDY, sample_forms


def _invalid(widget):
    return widget.property("invalid") is True


def _save(window, folder, setting_name, file_name, add_date_time):
    """Save the sample report as *setting_name* with that export name; its JSON."""
    window.settings_directory = str(folder)
    window.ui.lineEdit_file_name.setText(file_name)
    window.ui.checkBox_add_date_time.setChecked(add_date_time)
    window.ui.checkBox_save_current_setting.setChecked(True)
    window.ui.lineEdit_setting_name.setText(setting_name)
    window.click_save_setting()
    saved = folder / f"{setting_name}.json"
    return json.loads(saved.read_text(encoding="utf-8"))


def _write(window, folder, setting_name, **extra):
    """A setting file as the report saves it, plus *extra* keys."""
    settings = {**window.report.settings_to_dict(setting_name), **extra}
    saved = folder / f"{setting_name}.json"
    saved.write_text(json.dumps(settings), encoding="utf-8")
    window.settings_directory = str(folder)


def _pick(window, setting_name):
    """Pick the saved setting *setting_name* on Source data."""
    window.ui.checkBox_saved_setting.setChecked(True)
    combo = window.ui.comboBox_saved_setting
    combo.setCurrentIndex(combo.findText(setting_name))
    QApplication.processEvents()


def test_a_saved_setting_keeps_the_export_name(sample_window, tmp_path):
    saved = _save(sample_window, tmp_path, "Monthly", " DEMO01 DSMB.xlsx", False)

    assert saved[SETTINGS_KEY] == {"name": "DEMO01 DSMB", "add_date_time": False}


def test_a_setting_saved_without_a_file_name_is_saved_as_before(
    sample_window, tmp_path
):
    saved = _save(sample_window, tmp_path, "Monthly", "  ", True)

    assert SETTINGS_KEY not in saved


@pytest.mark.parametrize("add_date_time", [False, True])
def test_picking_the_setting_fills_the_export_name_back_in(
    sample_window, tmp_path, add_date_time
):
    window = sample_window
    window.output_folder_name = str(tmp_path)
    _save(window, tmp_path, "Monthly", "DEMO01 DSMB", add_date_time)
    window.ui.lineEdit_file_name.setText("Something else")
    window.ui.checkBox_add_date_time.setChecked(not add_date_time)

    _pick(window, "Monthly")

    name = window.ui.lineEdit_file_name
    assert name.text() == "DEMO01 DSMB"
    assert window.ui.checkBox_add_date_time.isChecked() is add_date_time
    assert not _invalid(name)
    assert window.ui.pushButton_run.isEnabled()


def test_a_new_zip_leaves_the_export_name_alone(sample_window, tmp_path):
    window = sample_window
    _save(window, tmp_path, "Monthly", "DEMO01 DSMB", False)
    window.ui.lineEdit_file_name.setText("Something else")
    _pick(window, "Monthly")
    picked = window.ui.lineEdit_file_name.text()

    # Forgets the setting it was picked from.
    window.open_input_data(f"Core_Listings_{STUDY}_sample.zip", None, sample_forms())
    QApplication.processEvents()

    assert picked == "DEMO01 DSMB"
    assert window.ui.lineEdit_file_name.text() == "DEMO01 DSMB"
    assert not window.ui.checkBox_add_date_time.isChecked()


def test_picking_an_older_setting_clears_the_file_name(sample_window, tmp_path):
    window = sample_window
    window.output_folder_name = str(tmp_path)  # Only the name holds Export back.
    _write(window, tmp_path, "Older")  # As saved before 2.21: no export name.
    window.ui.lineEdit_file_name.setText("DEMO01 DSMB")
    window.ui.checkBox_add_date_time.setChecked(False)

    _pick(window, "Older")

    name = window.ui.lineEdit_file_name
    assert window.ui.label_save_confirmation.kind() == "success"  # It loaded.
    assert name.text() == ""
    assert window.ui.checkBox_add_date_time.isChecked()
    assert _invalid(name) and name.toolTip() == "Give the file a name."
    assert not window.ui.pushButton_run.isEnabled()


def test_a_damaged_export_name_still_loads_the_setting(sample_window, tmp_path, caplog):
    window = sample_window
    _write(window, tmp_path, "Damaged", **{SETTINGS_KEY: "DEMO01 DSMB"})
    window.ui.lineEdit_file_name.setText("DEMO01 DSMB")

    with caplog.at_level(logging.WARNING):
        _pick(window, "Damaged")

    assert window.ui.label_save_confirmation.kind() == "success"
    assert window.ui.lineEdit_file_name.text() == ""
    assert f"Ignoring saved {SETTINGS_KEY}" in caplog.text
