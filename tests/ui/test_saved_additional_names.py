"""A saved setting brings back the names given to its additional input files."""

import json

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHeaderView

from cci_ui.widgets.sidebar import StepState
from clinical_reporting import steps
from clinical_reporting.additional_names import SETTINGS_KEY, SavedFileNames
from clinical_reporting.sample_data import STUDY, sample_forms
from clinical_reporting.ui.pages import additional_input
from clinical_reporting.ui.pages.additional_input import SAVED_NAMES_COLUMN


def _lab_results():
    subjects = sample_forms()["DM"]["Subject"].head(5)
    return pd.DataFrame(
        {
            "Subject ID": subjects,
            "Visit Dt": ["2026-02-01"] * len(subjects),
            "ALT (U/L)": range(len(subjects)),
        }
    )


def _ecg_results():
    subjects = sample_forms()["DM"]["Subject"].head(5)
    return pd.DataFrame(
        {
            "Subject ID": subjects,
            "Visit Dt": ["2026-02-02"] * len(subjects),
            "QTc (ms)": range(400, 400 + len(subjects)),
        }
    )


def _notes():
    return pd.DataFrame({"Subject ID": ["01-701"], "Note": ["Retested"]})


def _leave_additional_input(window):
    """Go to Additional input and on to Forms: its changes reach the report."""
    window.ui.shell.set_current(steps.ADDITIONAL)
    window.ui.shell.set_current(steps.FORMS)
    QApplication.processEvents()


def _start_again(window):
    """A new run: the sample ZIP again, and no additional files."""
    window.additional_inputs.clear()
    window.additional_form_names.clear()
    window.additional_column_names.clear()
    window.open_input_data(f"Core_Listings_{STUDY}_sample.zip", None, sample_forms())
    window._refresh_additional_files_ui()
    window._refresh_additional_tables()


def _save_setting(window, tmp_path, name, files):
    """Save setting *name* with *files* ({file name: (form, rows)}) and their forms.

    Each form is selected with its Visit Dt column, renamed Visit Date.
    """
    for file_name, (form, rows) in files.items():
        path = str(tmp_path / "first" / file_name)
        window.additional_inputs[path] = rows
        window.additional_form_names[path] = form
        window.additional_column_names[(path, "Subject ID")] = "Subject"
        window.additional_column_names[(path, "Visit Dt")] = "Visit Date"
    _leave_additional_input(window)
    for form, _ in files.values():
        window.report.add_selected_form(form)
        window.report.selected_forms[form].set_form_item_state(
            "Visit Date", selected=True
        )
    window.update_all_ui()
    window.settings_directory = str(tmp_path / "settings")
    window.ui.checkBox_save_current_setting.setChecked(True)
    window.ui.lineEdit_setting_name.setText(name)
    window.click_save_setting()


def _save_monthly_setting(window, tmp_path):
    """Save "Monthly AE review", with LAB from lab_results.csv; its JSON."""
    _save_setting(
        window,
        tmp_path,
        "Monthly AE review",
        {"lab_results.csv": ("LAB", _lab_results())},
    )
    (saved,) = (tmp_path / "settings").glob("*.json")
    return saved.read_text(encoding="utf-8")


def _load_setting(window, name):
    """A new run, starting from the saved setting *name* (on Source data)."""
    window.ui.shell.set_current(steps.SOURCE)
    _start_again(window)
    window.ui.checkBox_saved_setting.setChecked(True)
    combo = window.ui.comboBox_saved_setting
    combo.setCurrentIndex(combo.findText(name))
    QApplication.processEvents()


def _load_monthly_setting(window):
    """A new run, starting from "Monthly AE review"."""
    _load_setting(window, "Monthly AE review")


def _add_on_additional_input(window, monkeypatch, settle, folder, files):
    """On Additional input, add *files* ({file name: rows}) saved in *folder*.

    As its Add files… button does, the file dialog answering with them. Rows
    given as bytes are written as they are.
    """
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for file_name, rows in files.items():
        if isinstance(rows, bytes):
            (folder / file_name).write_bytes(rows)
        else:
            rows.to_csv(folder / file_name, index=False)
        paths.append(str(folder / file_name))
    monkeypatch.setattr(
        additional_input.QFileDialog, "getOpenFileNames", lambda *_args: (paths, "")
    )
    window.ui.shell.set_current(steps.ADDITIONAL)
    window.click_add_additional_files()
    settle(window.task_runner)
    # Files the setting completes go in just after, and the badges follow.
    QApplication.processEvents()
    QApplication.processEvents()


def _new_name_cell(window, file_name):
    """The New name cell of *file_name* in the Form names table."""
    table = window.ui.tableWidget_update_form_name
    (row,) = [
        row for row in range(table.rowCount()) if table.item(row, 0).text() == file_name
    ]
    return table.item(row, 1)


def _additional_forms(window):
    """The report's forms from additional files, with their selected items.

    None for a form the report has but doesn't select.
    """
    selected = window.report.selected_forms
    return {
        form: selected[form].get_selected_form_items() if form in selected else None
        for form in sorted(set(window.report.data) - set(sample_forms()))
    }


def test_saved_names_come_back_for_a_saved_settings_files(sample_window, tmp_path):
    window = sample_window
    text = _save_monthly_setting(window, tmp_path)

    _load_monthly_setting(window)
    missing = window.ui.label_setting.text()
    still_to_add = window.ui.banner_saved_names.text()
    table = window.ui.tableWidget_update_form_name

    again = str(tmp_path / "second" / "LAB_RESULTS.csv")
    window._add_loaded_additional_files(({again: _lab_results()}, {}))
    picker = table.cellWidget(0, SAVED_NAMES_COLUMN)
    dropdown = (picker.isEnabled(), picker.currentText())
    all_added = window.ui.banner_saved_names.text()
    names = (dict(window.additional_form_names), dict(window.additional_column_names))
    _leave_additional_input(window)

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


def test_saved_names_a_new_export_cant_use_are_ignored_with_a_warning(
    sample_window, tmp_path
):
    window = sample_window
    _save_monthly_setting(window, tmp_path)
    _load_monthly_setting(window)
    dated = str(tmp_path / "second" / "lab_results.csv")
    export = _lab_results().rename(columns={"Visit Dt": "Visit Date (dd)"})

    window._add_loaded_additional_files(({dated: export}, {}))
    standing = window.ui.banner_ignored_names.text()
    _leave_additional_input(window)
    applied = window.ui.banner_additional.text()
    missing = window.ui.label_setting.text()
    columns = window.ui.tableWidget_update_column_name
    rows = [columns.item(row, 0).text() for row in range(columns.rowCount())]
    columns.item(rows.index("Visit Date (dd)"), 1).setText("Visit Date")
    fixed = window.ui.banner_ignored_names.text()
    _leave_additional_input(window)

    assert standing.kind == "warning"
    assert "lab_results.csv has no Visit Dt." in standing
    assert "the form is still added" in standing
    # The form is added all the same; the setting misses the item it lacks.
    assert "LAB" in window.report.data
    assert applied.kind == "warning"
    assert applied == (
        "Additional input updated: 1 file added to the report. New forms: LAB. "
        "Saved column names ignored: lab_results.csv has no Visit Dt."
    )
    assert missing == "Missing items in LAB: Visit Date"
    # Renamed by hand, the column is back, and so is the setting's item.
    assert fixed == ""
    assert window.ui.banner_additional.text().kind == "success"
    assert window.ui.label_setting.text() == ""
    assert window.report.selected_forms["LAB"].get_selected_form_items() == [
        "Visit Date"
    ]


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


def test_adding_the_settings_last_file_puts_its_files_in_the_report_at_once(
    sample_window, tmp_path, monkeypatch, settle
):
    window = sample_window
    _save_monthly_setting(window, tmp_path)
    _load_monthly_setting(window)

    _add_on_additional_input(
        window,
        monkeypatch,
        settle,
        tmp_path / "second",
        {"lab_results.csv": _lab_results()},
    )
    banner = window.ui.banner_additional.text()

    assert window.ui.shell.current() == steps.ADDITIONAL
    assert _additional_forms(window) == {"LAB": ["Visit Date"]}
    assert window.ui.shell.sidebar.item(steps.ADDITIONAL).state() == StepState.DONE
    assert window.ui.label_setting.text() == ""
    assert banner.kind == "success"
    assert banner == (
        "Saved names from “Monthly AE review” picked for 1 file: lab_results.csv by "
        "its file name. Every file the setting needs is in, so the files were added "
        "to the report. New forms: LAB."
    )


def test_adding_some_of_the_settings_files_waits_for_the_rest(
    sample_window, tmp_path, monkeypatch, settle
):
    window = sample_window
    files = {
        "lab_results.csv": ("LAB", _lab_results()),
        "ecg_results.csv": ("ECG", _ecg_results()),
    }
    _save_setting(window, tmp_path, "Lab and ECG", files)
    _load_setting(window, "Lab and ECG")
    second = tmp_path / "second"

    _add_on_additional_input(
        window, monkeypatch, settle, second, {"lab_results.csv": _lab_results()}
    )
    waiting = (_additional_forms(window), window.ui.banner_additional.text())
    still_to_add = window.ui.banner_saved_names.text()
    _add_on_additional_input(
        window, monkeypatch, settle, second, {"ecg_results.csv": _ecg_results()}
    )

    assert waiting == (
        {},
        "Saved names from “Lab and ECG” picked for 1 file: lab_results.csv by its "
        "file name. Check them on Additional input. The files go into the report "
        "once the setting's other files are in, or when you go to another step.",
    )
    assert still_to_add.startswith("Still to add for “Lab and ECG”: ecg_results.csv")
    assert _additional_forms(window) == {
        "ECG": ["Visit Date"],
        "LAB": ["Visit Date"],
    }
    assert window.ui.banner_additional.text() == (
        "Saved names from “Lab and ECG” picked for 1 file: ecg_results.csv by its "
        "file name. Every file the setting needs is in, so the files were added to "
        "the report. New forms: ECG, LAB."
    )


def test_picking_the_last_saved_names_puts_the_files_in_at_once(
    sample_window, tmp_path, monkeypatch, settle
):
    window = sample_window
    _save_monthly_setting(window, tmp_path)
    _load_monthly_setting(window)
    # Another file name, and one more column: nothing picks the saved names.
    march = _lab_results().assign(**{"AST (U/L)": 7})
    _add_on_additional_input(
        window, monkeypatch, settle, tmp_path / "second", {"lab_march.csv": march}
    )
    held = (
        _additional_forms(window),
        _new_name_cell(window, "lab_march.csv").toolTip(),
    )
    picker = window.ui.tableWidget_update_form_name.cellWidget(0, SAVED_NAMES_COLUMN)

    picker.activated.emit(1)
    QApplication.processEvents()

    assert held == ({}, "Give it a form name.")
    assert _additional_forms(window) == {"LAB": ["Visit Date"]}
    assert window.ui.banner_additional.text() == (
        "Names from LAB filled in for lab_march.csv. Every file “Monthly AE review” "
        "needs is in, so the files were added to the report. New forms: LAB."
    )


def test_naming_the_last_red_file_puts_the_files_in_at_once(
    sample_window, tmp_path, monkeypatch, settle
):
    window = sample_window
    _save_monthly_setting(window, tmp_path)
    _load_monthly_setting(window)
    _add_on_additional_input(
        window,
        monkeypatch,
        settle,
        tmp_path / "second",
        {"lab_results.csv": _lab_results(), "notes.csv": _notes()},
    )
    held = _additional_forms(window)

    _new_name_cell(window, "notes.csv").setText("NOTES")
    QApplication.processEvents()

    assert held == {}
    assert _additional_forms(window) == {"LAB": ["Visit Date"], "NOTES": None}
    assert window.ui.banner_additional.text() == (
        "Every file “Monthly AE review” needs is in, so the files were added to the "
        "report. New forms: LAB, NOTES."
    )


def test_removing_the_last_red_file_puts_the_files_in_at_once(
    sample_window, tmp_path, monkeypatch, settle
):
    window = sample_window
    _save_monthly_setting(window, tmp_path)
    _load_monthly_setting(window)
    _add_on_additional_input(
        window,
        monkeypatch,
        settle,
        tmp_path / "second",
        {"lab_results.csv": _lab_results(), "notes.csv": _notes()},
    )
    held = _additional_forms(window)
    listed = window.ui.listWidget_additional_file
    (notes,) = listed.findItems("notes.csv", Qt.MatchFlag.MatchExactly)

    notes.setSelected(True)
    window.click_remove_additional_files()
    QApplication.processEvents()

    assert held == {}
    assert _additional_forms(window) == {"LAB": ["Visit Date"]}
    assert window.ui.banner_additional.text() == (
        "Every file “Monthly AE review” needs is in, so the files were added to the "
        "report. New forms: LAB."
    )


def test_a_rename_once_the_files_are_in_waits_until_you_leave(
    sample_window, tmp_path, monkeypatch, settle
):
    window = sample_window
    _save_monthly_setting(window, tmp_path)
    _load_monthly_setting(window)
    _add_on_additional_input(
        window,
        monkeypatch,
        settle,
        tmp_path / "second",
        {"lab_results.csv": _lab_results()},
    )

    _new_name_cell(window, "lab_results.csv").setText("LABS")
    QApplication.processEvents()
    before_leaving = sorted(_additional_forms(window))
    window.ui.shell.set_current(steps.FORMS)
    QApplication.processEvents()

    assert before_leaving == ["LAB"]
    assert sorted(_additional_forms(window)) == ["LABS"]


def test_files_put_in_at_once_still_say_which_files_couldnt_be_read(
    sample_window, tmp_path, monkeypatch, settle
):
    window = sample_window
    _save_monthly_setting(window, tmp_path)
    _load_monthly_setting(window)

    _add_on_additional_input(
        window,
        monkeypatch,
        settle,
        tmp_path / "second",
        {"lab_results.csv": _lab_results(), "broken.xlsx": b"not a workbook"},
    )
    banner = window.ui.banner_additional.text()

    assert _additional_forms(window) == {"LAB": ["Visit Date"]}
    assert banner.kind == "warning"
    assert banner == (
        "Saved names from “Monthly AE review” picked for 1 file: lab_results.csv by "
        "its file name. Every file the setting needs is in, so the files were added "
        "to the report. New forms: LAB. These files could not be read and were not "
        "added: broken.xlsx."
    )
