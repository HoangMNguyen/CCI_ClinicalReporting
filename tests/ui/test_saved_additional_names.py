"""A saved setting brings back the names given to its additional input files."""

import json

import pandas as pd
from PySide6.QtWidgets import QApplication, QHeaderView

from clinical_reporting import steps
from clinical_reporting.additional_names import SETTINGS_KEY, SavedFileNames
from clinical_reporting.ui.pages.additional_input import SAVED_NAMES_COLUMN
from clinical_reporting.ui.sample_data import STUDY, sample_forms


def _lab_results():
    subjects = sample_forms()["DM"]["Subject"].head(5)
    return pd.DataFrame(
        {
            "Subject ID": subjects,
            "Visit Dt": ["2026-02-01"] * len(subjects),
            "ALT (U/L)": range(len(subjects)),
        }
    )


def _start_again(window):
    """A new run: the sample ZIP again, and no additional files."""
    window.additional_inputs.clear()
    window.additional_form_names.clear()
    window.additional_column_names.clear()
    window.open_input_data(f"Core_Listings_{STUDY}_sample.zip", None, sample_forms())
    window._refresh_additional_files_ui()
    window._refresh_additional_tables()


def test_saved_names_come_back_for_a_saved_settings_files(sample_window, tmp_path):
    window = sample_window
    first = str(tmp_path / "first" / "lab_results.csv")
    window.additional_inputs[first] = _lab_results()
    window.additional_form_names[first] = "LAB"
    window.additional_column_names[(first, "Subject ID")] = "Subject"
    window.additional_column_names[(first, "Visit Dt")] = "Visit Date"
    window.click_apply_additional_forms()
    window.report.add_selected_form("LAB")
    window.report.selected_forms["LAB"].set_form_item_state("Visit Date", selected=True)
    window.update_all_ui()
    window.settings_directory = str(tmp_path / "settings")
    window.ui.checkBox_save_current_setting.setChecked(True)
    window.ui.lineEdit_setting_name.setText("Monthly AE review")
    window.click_save_setting()
    (saved,) = (tmp_path / "settings").glob("*.json")
    text = saved.read_text(encoding="utf-8")

    _start_again(window)
    window.ui.checkBox_saved_setting.setChecked(True)
    combo = window.ui.comboBox_saved_setting
    combo.setCurrentIndex(combo.findText("Monthly AE review"))
    QApplication.processEvents()
    missing = window.ui.label_setting.text()
    still_to_add = window.ui.banner_saved_names.text()
    table = window.ui.tableWidget_update_form_name

    again = str(tmp_path / "second" / "LAB_RESULTS.csv")
    window._add_loaded_additional_files(({again: _lab_results()}, {}))
    picker = table.cellWidget(0, SAVED_NAMES_COLUMN)
    dropdown = (picker.isEnabled(), picker.currentText())
    all_added = window.ui.banner_saved_names.text()
    names = (dict(window.additional_form_names), dict(window.additional_column_names))
    window.click_apply_additional_forms()
    QApplication.processEvents()

    assert json.loads(text)[SETTINGS_KEY] == [
        {
            "file_name": "lab_results.csv",
            "columns": ["Subject ID", "Visit Dt", "ALT (U/L)"],
            "form_name": "LAB",
            "column_names": {"Subject ID": "Subject", "Visit Dt": "Visit Date"},
        }
    ]
    assert str(tmp_path) not in text
    assert missing.startswith("Missing forms: LAB\n")
    assert "Add lab_results.csv on Additional input" in missing
    assert still_to_add.startswith(
        "Still to add for “Monthly AE review”: lab_results.csv (LAB)."
    )
    assert all_added == ""
    assert dropdown == (True, "LAB")
    assert names == (
        {again: "LAB"},
        {(again, "Subject ID"): "Subject", (again, "Visit Dt"): "Visit Date"},
    )
    # The setting is applied again with LAB there, so its selections are back.
    assert window.report.selected_forms["LAB"].get_selected_form_items() == [
        "Visit Date"
    ]
    assert window.ui.label_setting.text() == ""
    # Re-applying the setting kept the pick.
    assert table.cellWidget(0, SAVED_NAMES_COLUMN).currentIndex() == 1

    window.ui.checkBox_saved_setting.setChecked(False)

    assert not table.cellWidget(0, SAVED_NAMES_COLUMN).isEnabled()
    assert window.additional_form_names == {again: "LAB"}


def test_removing_the_zip_takes_the_saved_names_away(sample_window, tmp_path):
    window = sample_window
    lab = str(tmp_path / "lab_results.csv")
    window.additional_inputs[lab] = _lab_results()
    window._offer_saved_additional_names(
        [SavedFileNames("lab_results.csv", (), "LAB", {})], "Monthly AE review"
    )
    table = window.ui.tableWidget_update_form_name
    offered = table.cellWidget(0, SAVED_NAMES_COLUMN).isEnabled()

    window.click_remove_input()

    assert offered and not table.cellWidget(0, SAVED_NAMES_COLUMN).isEnabled()
    assert window.additional_form_names == {lab: "LAB"}
    assert window.ui.banner_saved_names.text() == ""


def test_the_saved_names_column_shows_without_a_setting(empty_window):
    window = empty_window
    table = window.ui.tableWidget_update_form_name
    header = table.horizontalHeader()
    lab = "C:/exports/lab_results.csv"

    window._add_loaded_additional_files(({lab: _lab_results()}, {}))
    picker = table.cellWidget(0, SAVED_NAMES_COLUMN)

    assert table.columnCount() == 3
    assert table.horizontalHeaderItem(SAVED_NAMES_COLUMN).text() == "Saved names"
    assert not table.isColumnHidden(SAVED_NAMES_COLUMN)
    assert [header.sectionResizeMode(column) for column in range(3)] == [
        QHeaderView.ResizeMode.Stretch,
        QHeaderView.ResizeMode.Interactive,
        QHeaderView.ResizeMode.Interactive,
    ]
    assert (header.sectionSize(1), header.sectionSize(2)) == (110, 130)
    assert not picker.isEnabled()
    assert picker.currentText() == steps.SAVED_NAMES_NONE
    assert picker.toolTip() == steps.SAVED_NAMES_UNAVAILABLE_TIP
