"""What the Clinical Reporting pages show around their content.

The "No data loaded" state, the Joins and Additional input banners, the
Source data footnote, the Preview caption and file name, the shortcuts, and
the tooltips. Most tests use the DEMO01 sample window (``sample_window`` in
``tests/ui/conftest.py``).
"""

import re

import pandas as pd
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from clinical_reporting import steps
from clinical_reporting.sample_data import sample_forms
from clinical_reporting.ui.pages import source_data
from clinical_reporting.ui.pages.preview_export import SUBTITLE
from clinical_reporting.ui.preview_model import ReportPreviewModel


def _page(window, key):
    return window.ui.shell.page(key)


def test_pages_that_need_data_say_how_to_load_some(empty_window, monkeypatch):
    asked = []
    monkeypatch.setattr(
        source_data.QFileDialog,
        "getOpenFileName",
        lambda *_args: asked.append(True) or ("", ""),
    )
    empty = {
        key: _page(empty_window, key).is_showing_empty_state()
        for key in steps.NEEDS_DATA
    }
    state = _page(empty_window, steps.FORMS).empty_state

    state.action_button.click()

    assert all(empty.values()), empty
    assert _page(empty_window, steps.SOURCE).empty_state is None
    assert asked == [True]  # The Source data page's "Choose ZIP…".


def test_loading_data_brings_the_pages_back(sample_window):
    def showing_empty_states():
        return {
            key
            for key in steps.NEEDS_DATA
            if _page(sample_window, key).is_showing_empty_state()
        }

    loaded = showing_empty_states()
    sample_window.click_remove_input()
    QApplication.processEvents()
    removed = showing_empty_states()
    sample_window.open_input_data("Core_Listings_DEMO02_x.zip", None, sample_forms())
    QApplication.processEvents()

    assert loaded == set() and removed == steps.NEEDS_DATA
    assert showing_empty_states() == set()


def test_the_preview_page_builds_nothing_without_data(empty_window, monkeypatch):
    built = []
    monkeypatch.setattr(type(empty_window), "preview_report", lambda w: built.append(w))

    empty_window.ui.shell.set_current(steps.PREVIEW)

    assert built == []


def test_a_common_item_the_forms_dont_join_on_gets_their_own_columns(sample_window):
    """AE and VS join on Subject and Site. Selecting Visit as well gives them
    AE.Visit and VS.Visit, which Order & rename and the filters offer, until a
    form joins on Visit too."""
    window = sample_window
    window.report.set_common_item_state("Visit", selected=True)
    window.update_all_ui()
    QApplication.processEvents()

    def order_rows():
        table = window.ui.tableWidget_rename
        return [table.item(row, 0).text() for row in range(table.rowCount())]

    assert {"AE.Visit", "VS.Visit"} <= set(order_rows())
    assert {"AE.Visit", "VS.Visit"} <= set(window._selected_filter_items())
    assert window.ui.banner_joins.kind() == "info"
    assert "AE.Visit" in window.ui.banner_joins.text()

    table = window.ui.tableWidget_join
    rows = {table.item(row, 1).text(): row for row in range(table.rowCount())}
    table.cellWidget(rows["VS"], 4).setCurrentText("Visit")
    QApplication.processEvents()

    assert "AE.Visit" in order_rows() and "VS.Visit" not in order_rows()
    assert "VS.Visit" not in window._selected_filter_items()
    out = window.report.create_report()
    assert "AE.Visit" in out.columns
    assert not [name for name in out.columns if name.endswith(("_x", "_y"))]


def test_a_join_edit_keeps_a_comparison_row_still_being_filled_in(sample_window):
    window = sample_window
    filters = window.ui.tableWidget_dynamic_filter
    window.dynamic_filter_add()  # A new, empty comparison row.
    rows = filters.rowCount()

    table = window.ui.tableWidget_join
    form_rows = {table.item(row, 1).text(): row for row in range(table.rowCount())}
    table.cellWidget(form_rows["AE"], 5).setCurrentText("Inner join")
    QApplication.processEvents()

    # The join type changes no column, so the filter tables stay as they are.
    assert filters.rowCount() == rows


def _join_forms(window):
    table = window.ui.tableWidget_join
    return [table.item(row, 1).text() for row in range(table.rowCount())]


def _selected_join_rows(window):
    table = window.ui.tableWidget_join
    return [index.row() for index in table.selectionModel().selectedRows()]


def _join_combos_enabled(window, row):
    table = window.ui.tableWidget_join
    return [table.cellWidget(row, column).isEnabled() for column in range(2, 6)]


def test_the_join_rows_follow_the_join_order(sample_window):
    window = sample_window
    table = window.ui.tableWidget_join
    numbers = [table.item(row, 0).text() for row in range(table.rowCount())]
    window.report.update_join_list(
        [("VS", ["Subject"], 2, "Left join"), ("AE", ["Subject"], 3, "Left join")]
    )

    window.update_join_table_ui()

    assert numbers == ["1", "2", "3"]
    assert _join_forms(window) == ["DM", "VS", "AE"]
    assert _join_combos_enabled(window, 0) == [False, False, False, False]
    assert _join_combos_enabled(window, 1) == [True, True, True, True]


def test_move_up_moves_the_selected_form_and_keeps_it_selected(sample_window):
    window = sample_window
    window.ui.tableWidget_join.selectRow(2)  # VS

    window.ui.pushButton_join_up.click()

    assert _join_forms(window) == ["DM", "VS", "AE"]
    assert _selected_join_rows(window) == [1]
    orders = {
        form: join["order"] for form, join in window.report.get_join_list_dict().items()
    }
    assert orders == {"DM": 1, "AE": 3, "VS": 2}


def test_the_move_buttons_follow_the_selected_row(sample_window):
    window = sample_window
    table = window.ui.tableWidget_join
    up, down = window.ui.pushButton_join_up, window.ui.pushButton_join_down

    def states():
        return up.isEnabled(), down.isEnabled()

    table.clearSelection()
    none = states()
    table.selectRow(0)
    first = states()
    table.selectRow(1)
    middle = states()
    table.selectRow(2)
    last = states()

    assert none == (False, False)
    assert first == (False, True)
    assert middle == (True, True)
    assert last == (True, False)


def test_moving_the_first_form_down_joins_it_on_subject(sample_window):
    window = sample_window
    table = window.ui.tableWidget_join
    table.selectRow(0)  # DM

    window.ui.pushButton_join_down.click()

    assert _join_forms(window) == ["AE", "DM", "VS"]
    assert table.cellWidget(1, 2).currentText() == "Subject"
    assert _join_combos_enabled(window, 0) == [False, False, False, False]
    assert window.report.get_join_list_dict()["DM"] == {
        "items": ["Subject"],
        "order": 2,
        "how": "Left join",
    }


def test_a_join_combo_taking_the_focus_selects_its_row(sample_window):
    table = sample_window.ui.tableWidget_join
    table.clearSelection()

    QApplication.sendEvent(
        table.cellWidget(2, 3),
        QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.MouseFocusReason),
    )

    assert _selected_join_rows(sample_window) == [2]


def test_a_newly_selected_form_joins_last_on_subject(sample_window):
    window = sample_window
    available = window.ui.listWidget_form_available
    available.setCurrentItem(available.findItems("LB", Qt.MatchFlag.MatchExactly)[0])

    window.click_select_form()

    assert _join_forms(window) == ["DM", "AE", "VS", "LB"]
    assert window.ui.tableWidget_join.cellWidget(3, 2).currentText() == "Subject"


def test_the_source_footnote_says_what_was_read(sample_window):
    footnote = sample_window.ui.section_input_file.footnote_label

    shown = footnote.text()
    sample_window.click_remove_input()

    assert re.fullmatch(
        r"\d+ forms · [\d,]+ rows · read at \d\d:\d\d on \d+ \w+", shown
    )
    assert footnote.text() == "" and not footnote.isVisible()


def test_the_preview_shows_its_size_and_the_file_name_it_would_write(
    sample_window, settle
):
    sample_window.ui.shell.set_current(steps.PREVIEW)
    settle(sample_window.task_runner)
    page = _page(sample_window, steps.PREVIEW)
    model = sample_window.ui.tableView_preview.model()

    caption = page.subtitle_label.text()
    unnamed = page.file_name_caption.isHidden()
    sample_window.ui.lineEdit_file_name.setText("DEMO01 DSMB")
    shown = not page.file_name_caption.isHidden()
    file_name = page.file_name_caption.text()
    sample_window.ui.checkBox_add_date_time.setChecked(False)
    unstamped = page.file_name_caption.text()
    sample_window.ui.lineEdit_file_name.setText(" .xlsx")
    blanked = page.file_name_caption.isHidden()
    sample_window.ui.tableView_preview.setModel(None)

    assert caption == steps.preview_caption(model.rowCount(), model.columnCount())
    assert unnamed and shown
    assert re.fullmatch(
        r"Saved as DEMO01 DSMB \d{6}_\d{6}\.xlsx \(date and time of export\)",
        file_name,
    )
    assert unstamped == "Saved as DEMO01 DSMB.xlsx"
    assert blanked
    assert page.subtitle_label.text() == SUBTITLE


def test_preview_shortcuts_refresh_and_export(
    sample_window, settle, monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setattr(
        source_data.QFileDialog, "getExistingDirectory", lambda *_args: str(tmp_path)
    )
    sample_window.click_output_file()  # Export to Excel needs a folder,
    sample_window.ui.lineEdit_file_name.setText("DEMO01 DSMB")  # and a name.
    sample_window.ui.shell.set_current(steps.PREVIEW)
    settle(sample_window.task_runner)  # Keys are blocked while it builds.
    sample_window.ui.pushButton_refresh_preview.clicked.disconnect()
    sample_window.ui.pushButton_refresh_preview.clicked.connect(
        lambda: calls.append("refresh")
    )
    sample_window.ui.pushButton_run.clicked.disconnect()
    sample_window.ui.pushButton_run.clicked.connect(lambda: calls.append("run"))
    sample_window.activateWindow()
    focus = sample_window.ui.lineEdit_file_name
    focus.setFocus()
    QApplication.processEvents()

    QTest.keyClick(focus, Qt.Key.Key_F5)
    QTest.keyClick(focus, Qt.Key.Key_E, Qt.KeyboardModifier.ControlModifier)
    sample_window.ui.pushButton_run.setEnabled(False)
    QTest.keyClick(focus, Qt.Key.Key_E, Qt.KeyboardModifier.ControlModifier)

    assert calls == ["refresh", "run"]
    assert "(F5)" in sample_window.ui.pushButton_refresh_preview.toolTip()


def test_tab_goes_from_the_file_name_to_its_checkbox_then_export(
    sample_window, settle, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        source_data.QFileDialog, "getExistingDirectory", lambda *_args: str(tmp_path)
    )
    sample_window.click_output_file()
    ui = sample_window.ui
    ui.lineEdit_file_name.setText("DEMO01 DSMB")  # Export takes the focus once enabled.
    ui.shell.set_current(steps.PREVIEW)
    settle(sample_window.task_runner)
    sample_window.activateWindow()
    ui.lineEdit_file_name.setFocus()
    QApplication.processEvents()

    focused = []
    for _ in range(2):
        QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab)
        focused.append(QApplication.focusWidget())

    assert focused == [ui.checkBox_add_date_time, ui.pushButton_run]


def test_ctrl_f_goes_to_the_search_field(sample_window):
    sample_window.ui.shell.set_current(steps.FORMS)
    sample_window.activateWindow()
    sample_window.ui.listWidget_form_available.setFocus()
    QApplication.processEvents()

    QTest.keyClick(
        sample_window.ui.listWidget_form_available,
        Qt.Key.Key_F,
        Qt.KeyboardModifier.ControlModifier,
    )

    assert QApplication.focusWidget() is sample_window.ui.lineEdit_form_search


def test_long_preview_values_show_whole_in_a_tooltip():
    long_text = "Subject withdrew consent after the second cycle of treatment"
    model = ReportPreviewModel(pd.DataFrame({"Reason": [long_text, "Completed"]}))

    assert model.data(model.index(0, 0), Qt.ToolTipRole) == long_text
    assert model.data(model.index(1, 0), Qt.ToolTipRole) is None


def test_small_wording_on_the_controls_and_pages(empty_window):
    ui = empty_window.ui

    assert ui.pushButton_remove_input.toolTip() == "Remove file"
    assert ui.comboBox_saved_setting.placeholderText() == "Choose a setting…"
    assert ui.lineEdit_file_name.placeholderText() == "e.g. DEMO01 DSMB"
    assert ui.checkBox_add_date_time.text() == "Add the date and time"
    assert ui.checkBox_add_date_time.isChecked()
    assert [page.title() for page in ui.pages] == list(steps.TITLES.values())


def test_a_new_zip_clears_the_old_preview(sample_window, settle):
    sample_window.ui.shell.set_current(steps.PREVIEW)
    settle(sample_window.task_runner)
    built = sample_window.ui.tableView_preview.model().rowCount()

    sample_window.open_input_data("Core_Listings_DEMO02_x.zip", None, sample_forms())
    QApplication.processEvents()

    assert built > 0
    assert sample_window.ui.tableView_preview.model() is None
    assert _page(sample_window, steps.PREVIEW).subtitle_label.text() == SUBTITLE


def test_preview_keys_do_nothing_while_there_is_no_data(empty_window):
    pressed = []
    empty_window.ui.pushButton_refresh_preview.clicked.connect(
        lambda: pressed.append(True)
    )
    empty_window.show()
    empty_window.activateWindow()
    empty_window.ui.shell.set_current(steps.PREVIEW)
    QApplication.processEvents()

    QTest.keyClick(empty_window.ui.shell.sidebar, Qt.Key.Key_F5)
    empty_window.close()

    assert pressed == []


def _leave_additional_input(window):
    """Go to Additional input and on: its changes reach the report."""
    window.ui.shell.set_current(steps.ADDITIONAL)
    window.ui.shell.set_current(steps.SOURCE)


def test_the_preview_goes_when_additional_only_data_goes(empty_window, settle):
    window = empty_window
    window.additional_inputs = {"lab.csv": pd.DataFrame({"Subject": ["1", "2"]})}
    window.additional_form_names = {"lab.csv": "PK"}
    _leave_additional_input(window)
    window.report.add_selected_form("PK")
    window.report.set_common_item_state("Subject", selected=True)
    window.update_all_ui()
    window.preview_report()
    settle(window.task_runner)
    built = window.ui.tableView_preview.model()

    window.additional_inputs.clear()
    _leave_additional_input(window)  # Removes the only forms.
    QApplication.processEvents()

    assert built is not None and built.rowCount() == 2
    assert window.ui.tableView_preview.model() is None
    assert _page(window, steps.PREVIEW).subtitle_label.text() == SUBTITLE


def test_ctrl_s_saves_the_setting_and_ctrl_f_searches_the_columns(
    sample_window, settle
):
    saved = []
    sample_window.ui.pushButton_save_setting.clicked.disconnect()
    sample_window.ui.pushButton_save_setting.clicked.connect(lambda: saved.append(1))
    sample_window.ui.checkBox_save_current_setting.setChecked(True)
    sample_window.ui.lineEdit_setting_name.setText("DEMO01 sample")
    sample_window.ui.shell.set_current(steps.PREVIEW)
    settle(sample_window.task_runner)
    sample_window.activateWindow()
    QApplication.processEvents()

    QTest.keyClick(
        sample_window.ui.lineEdit_setting_name,
        Qt.Key.Key_S,
        Qt.KeyboardModifier.ControlModifier,
    )
    sample_window.ui.shell.set_current(steps.ORDER)
    sample_window.ui.tableWidget_rename.setFocus()
    QApplication.processEvents()
    QTest.keyClick(
        sample_window.ui.tableWidget_rename,
        Qt.Key.Key_F,
        Qt.KeyboardModifier.ControlModifier,
    )

    assert saved == [1]
    assert QApplication.focusWidget() is sample_window.ui.lineEdit_order_search


def test_an_empty_zip_says_it_had_no_forms(sample_window):
    sample_window.open_input_data("Core_Listings_DEMO03_x.zip", None, {})

    footnote = sample_window.ui.section_input_file.footnote_label.text()

    assert footnote.startswith("0 forms · 0 rows · read at ")


def test_infinite_values_and_long_column_names_show_safely():
    long_name = "AE.Action taken with study treatment (other)"
    model = ReportPreviewModel(pd.DataFrame({long_name: [float("inf"), 2.0]}))

    assert model.data(model.index(0, 0)) == "inf"
    assert model.data(model.index(1, 0)) == "2"
    assert model.headerData(0, Qt.Horizontal, Qt.ToolTipRole) == long_name
