"""Problems marked on the fields that fix them, on the DEMO01 sample window.

A field that lacks a value, or holds one the report can't use, turns red with
the reason as its tooltip; the step's badge turns red with it, and Export to
Excel waits until it is fixed. The marks follow once control returns to the
event loop, so the tests process events before looking.
"""

import json

from PySide6.QtWidgets import QApplication

from cci_ui.widgets.sidebar import StepState
from cci_ui.widgets.tables import PROBLEM_ROLE
from clinical_reporting.sample_data import STUDY
from clinical_reporting.ui.pages import source_data


def _invalid(widget):
    return widget.property("invalid") is True


def _badge(window, key):
    return window.ui.shell.sidebar.item(key).state()


def _choose_output_folder(window, monkeypatch, folder):
    monkeypatch.setattr(
        source_data.QFileDialog, "getExistingDirectory", lambda *_args: str(folder)
    )
    window.click_output_file()
    QApplication.processEvents()


def test_a_new_filter_row_shows_what_it_lacks(sample_window, monkeypatch, tmp_path):
    window = sample_window
    _choose_output_folder(window, monkeypatch, tmp_path)
    window.ui.lineEdit_file_name.setText("DEMO01 DSMB")
    export_before = window.ui.pushButton_run.isEnabled()
    table = window.ui.tableWidget_static_filter

    window.static_filter_add()
    QApplication.processEvents()

    item_box, value = table.cellWidget(1, 0), table.item(1, 2)
    assert export_before
    assert _invalid(item_box)
    assert item_box.toolTip() == "Static filter 2 needs an item."
    assert value.data(PROBLEM_ROLE) == "Static filter 2 needs a value."
    assert value.toolTip() == "Static filter 2 needs a value."
    assert _badge(window, "filters") == StepState.ERROR
    assert not window.ui.pushButton_run.isEnabled()
    assert window.ui.banner_run_state.text() == "Cannot run: Fix Filters first."


def test_finishing_the_filter_row_clears_its_marks(
    sample_window, monkeypatch, tmp_path
):
    window = sample_window
    _choose_output_folder(window, monkeypatch, tmp_path)
    window.ui.lineEdit_file_name.setText("DEMO01 DSMB")
    table = window.ui.tableWidget_static_filter
    window.static_filter_add()
    QApplication.processEvents()
    item_box, value = table.cellWidget(1, 0), table.item(1, 2)

    item_box.setCurrentIndex(item_box.findText("Subject"))
    value.setText("01-100")
    QApplication.processEvents()

    assert not _invalid(item_box)
    assert item_box.toolTip() == "Subject\nPick an item, or type to find one"
    assert value.data(PROBLEM_ROLE) is None and value.toolTip() == ""
    assert _badge(window, "filters") == StepState.NONE
    assert window.ui.pushButton_run.isEnabled()
    assert window.ui.banner_run_state.text() == ""


def test_a_new_comparison_row_shows_both_missing_items(sample_window):
    window = sample_window
    table = window.ui.tableWidget_dynamic_filter

    window.dynamic_filter_add()
    QApplication.processEvents()

    left, right = table.cellWidget(1, 0), table.cellWidget(1, 2)
    assert _invalid(left) and _invalid(right)
    assert left.toolTip() == "Dynamic filter 2 needs its left item."
    assert right.toolTip() == "Dynamic filter 2 needs its right item."
    assert _badge(window, "comparisons") == StepState.ERROR


def test_a_name_two_columns_would_share_is_marked_on_both(sample_window):
    window = sample_window
    table = window.ui.tableWidget_rename
    rows = {table.item(row, 0).text(): row for row in range(table.rowCount())}

    table.item(rows["AE.Grade"], 1).setText("Age (years)")  # As DM.Age is named.
    QApplication.processEvents()

    duplicated = "Output column name 'Age (years)' would be duplicated."
    assert table.item(rows["AE.Grade"], 1).data(PROBLEM_ROLE) == duplicated
    assert table.item(rows["DM.Age"], 1).data(PROBLEM_ROLE) == duplicated
    assert table.item(rows["Subject"], 1).data(PROBLEM_ROLE) is None
    assert _badge(window, "order") == StepState.ERROR


def test_a_form_without_join_items_has_its_item_1_marked(sample_window):
    window = sample_window
    table = window.ui.tableWidget_join

    for column in (2, 3, 4):  # VS, the last form.
        table.cellWidget(2, column).setCurrentText("")
    QApplication.processEvents()

    item_1 = table.cellWidget(2, 2)
    assert _invalid(item_1)
    assert item_1.toolTip() == (
        "Form 'VS' needs at least one join item because it is not first."
    )
    assert not _invalid(table.cellWidget(1, 2))
    assert _badge(window, "joins") == StepState.ERROR


def test_the_output_folder_is_marked_until_one_is_chosen(
    sample_window, monkeypatch, tmp_path
):
    window = sample_window
    window.ui.lineEdit_file_name.setText("DEMO01 DSMB")
    QApplication.processEvents()
    picker = window.ui.pathPicker_output_folder
    before = (
        _invalid(picker.path_label),
        picker.toolTip(),
        window.ui.pushButton_run.isEnabled(),
    )

    _choose_output_folder(window, monkeypatch, tmp_path)

    assert before == (True, "Choose the folder to export to.", False)
    assert picker.toolTip() == ""  # One folder: the field shows it.
    assert not _invalid(picker.path_label)
    assert window.ui.pushButton_run.isEnabled()


def test_the_file_name_is_marked_until_one_is_typed(
    sample_window, monkeypatch, tmp_path
):
    window = sample_window
    _choose_output_folder(window, monkeypatch, tmp_path)
    name, export = window.ui.lineEdit_file_name, window.ui.pushButton_run
    unnamed = (
        _invalid(name),
        name.toolTip(),
        export.isEnabled(),
        # Only the field says so: no step to fix, no red badge.
        window.ui.banner_run_state.text(),
        _badge(window, "preview") != StepState.ERROR,
    )
    nameless = []
    for text in ("   ", ".xlsx"):
        name.setText(text)
        nameless.append((_invalid(name), export.isEnabled()))

    name.setText("DEMO01 DSMB")

    assert unnamed == (True, "Give the file a name.", False, "", True)
    assert nameless == [(True, False), (True, False)]
    assert not _invalid(name) and name.toolTip() == ""
    assert export.isEnabled()


def test_saving_needs_a_setting_name(sample_window):
    window = sample_window
    name, save = window.ui.lineEdit_setting_name, window.ui.pushButton_save_setting

    window.ui.checkBox_save_current_setting.setChecked(True)
    unnamed = (_invalid(name), name.toolTip(), save.isEnabled())
    name.setText("DEMO01 monthly")

    assert unnamed == (True, "Give the setting a name.", False)
    assert not _invalid(name) and name.toolTip() == ""
    assert save.isEnabled()


def test_a_setting_that_cant_be_loaded_marks_the_setting_box(sample_window, tmp_path):
    window = sample_window
    setting = tmp_path / "monthly.json"
    setting.write_text(
        json.dumps({"study_name": STUDY, "setting_name": "monthly"}), encoding="utf-8"
    )
    window.settings_directory = str(tmp_path)
    window.ui.checkBox_saved_setting.setChecked(True)  # Lists it.
    setting.write_text("{broken", encoding="utf-8")
    box = window.ui.comboBox_saved_setting

    box.setCurrentIndex(box.findText("monthly"))

    assert _invalid(box)
    assert box.toolTip() == "This setting couldn't be loaded; see the message below."
    assert window.ui.label_setting.text().startswith("Failed to load settings: ")
    assert window.ui.label_setting.kind() == "error"
