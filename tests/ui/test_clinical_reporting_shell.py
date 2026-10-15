"""The Clinical Reporting window's frame: sidebar, header, status bar, toasts.

The window holds the DEMO01 sample report the preview tool shows (forms DM,
AE and VS; common items Subject and Site; one filter, one comparison, one
rename). Badges and the summary refresh once control returns to the event
loop, so the tests process events before looking.
"""

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from cci_ui.widgets.sidebar import StepState
from cci_ui.widgets.status import ToastHost
from clinical_reporting import feedback, steps
from clinical_reporting.sample_data import STUDY, sample_forms
from clinical_reporting.ui.preview import PAGE_KEYS


def _badge(window, key):
    item = window.ui.shell.sidebar.item(key)
    return item.state(), item.count()


def _toasts(window):
    host = window.findChild(ToastHost)
    return [] if host is None else [t.accessibleName() for t in host.toasts()]


def test_badge_states_are_ones_the_sidebar_draws():
    assert {steps.NONE, steps.DONE, steps.WARNING, steps.ERROR, steps.OPTIONAL} <= {
        state.value for state in StepState
    }


def test_the_sidebar_lists_every_step_and_shows_where_you_are(sample_window):
    shell = sample_window.ui.shell

    QTest.mouseClick(shell.sidebar.item("joins"), Qt.MouseButton.LeftButton)

    assert shell.sidebar.keys() == list(PAGE_KEYS)
    assert shell.current() == "joins" and shell.page("joins").isVisible()
    assert shell.header.context_label.text() == STUDY
    assert shell.header.page_label.text() == "Joins"
    assert sample_window.windowTitle() == f"{STUDY} — Clinical Reporting"
    assert shell.display_button is not None


def test_the_help_starts_closed_and_follows_the_open_step(sample_window):
    shell = sample_window.ui.shell
    shell.set_current("source")
    closed = shell.is_help_visible()
    width = sample_window.width()

    shell.help_button.click()
    QApplication.processEvents()
    on_source = shell.help_panel.title.text()
    opening = shell.help_panel.body.toPlainText().splitlines()[0]
    shell.set_current("joins")

    assert closed is False
    assert on_source == "Help: Source data" and opening == "What this step is for"
    assert shell.help_panel.title.text() == "Help: Joins"
    assert shell.is_help_visible()
    assert sample_window.width() == width  # The pages make room for it.


def test_next_goes_to_the_following_step(sample_window):
    shell = sample_window.ui.shell
    shell.set_current("joins")
    (next_button,) = [
        button
        for button in shell.page("joins").findChildren(QPushButton)
        if button.text().startswith("Next:")
    ]

    QTest.mouseClick(next_button, Qt.MouseButton.LeftButton)

    assert next_button.text() == "Next: Comparisons"
    assert shell.current() == "comparisons"


def test_a_title_with_an_ampersand_gets_no_shortcut(sample_window):
    item = sample_window.ui.shell.sidebar.item("order")

    assert item.title() == "Order & rename" and item.text() == "Order && rename"


def test_badges_follow_the_sample_report(sample_window):
    assert _badge(sample_window, "source") == (StepState.DONE, None)
    assert _badge(sample_window, "additional") == (StepState.OPTIONAL, None)
    assert _badge(sample_window, "stacked") == (StepState.OPTIONAL, None)
    assert _badge(sample_window, "forms") == (StepState.NONE, 3)
    assert _badge(sample_window, "common") == (StepState.NONE, 2)
    assert _badge(sample_window, "filters") == (StepState.NONE, 1)
    assert _badge(sample_window, "joins") == (StepState.DONE, None)
    assert _badge(sample_window, "comparisons") == (StepState.NONE, 1)
    assert _badge(sample_window, "order") == (StepState.NONE, 1)
    assert _badge(sample_window, "preview") == (StepState.NONE, None)
    summary = sample_window.ui.shell.status_bar.summary()
    assert summary.startswith(f"{STUDY} · 3 forms · ")


def _after(window, change, key):
    """Make *change*, let the refresh run, and return *key*'s badge."""
    change()
    QApplication.processEvents()
    return _badge(window, key)


def test_badges_follow_filter_edits(sample_window):
    ui = sample_window.ui
    static, dynamic = ui.tableWidget_static_filter, ui.tableWidget_dynamic_filter

    def remove_static():
        static.selectRow(0)
        sample_window.static_filter_remove()

    def pick(box, item):
        box.setCurrentIndex(box.findText(item))

    def add_static():
        # An "=" filter needs a value now, as well as an item.
        sample_window.static_filter_add()
        pick(static.cellWidget(0, 0), "DM.Age")
        static.item(0, 2).setText("18")

    def add_dynamic():
        sample_window.dynamic_filter_add()
        pick(dynamic.cellWidget(1, 0), "DM.Age")
        pick(dynamic.cellWidget(1, 2), "Subject")

    def remove_dynamic():
        dynamic.selectRow(0)
        sample_window.dynamic_filter_remove()

    assert _after(sample_window, remove_static, "filters") == (StepState.NONE, None)
    assert _after(sample_window, add_static, "filters") == (StepState.NONE, 1)
    assert _after(sample_window, add_dynamic, "comparisons") == (StepState.NONE, 2)
    assert _after(sample_window, remove_dynamic, "comparisons") == (
        StepState.NONE,
        1,
    )


def test_badges_follow_item_join_and_rename_edits(sample_window):
    ui = sample_window.ui
    joins, renames = ui.tableWidget_join, ui.tableWidget_rename
    forms = {joins.item(row, 1).text(): row for row in range(joins.rowCount())}
    _, items_before = _badge(sample_window, "formitems")

    def pick_a_form_item():
        ui.listWidget_form_item_available.item(0).setSelected(True)
        sample_window.click_select_form_item()

    def clear_the_last_forms_join_items():
        for column in (2, 3, 4):
            joins.cellWidget(forms["VS"], column).setCurrentText("")

    def rename_the_first_column():
        renames.item(0, 1).setText("Renamed")

    def copy_the_original_names():
        renames.selectAll()
        sample_window.copy_selected_original_names_to_rename()

    picked = _after(sample_window, pick_a_form_item, "formitems")
    assert picked == (StepState.NONE, items_before + 1)
    cleared = _after(sample_window, clear_the_last_forms_join_items, "joins")
    assert cleared == (StepState.ERROR, None)
    tip = ui.shell.sidebar.item("joins").toolTip()
    assert "Form 'VS' needs at least one join item because it is not first." in tip
    # Copying the original names undoes the sample's one rename.
    assert _after(sample_window, copy_the_original_names, "order") == (
        StepState.NONE,
        None,
    )
    assert _after(sample_window, rename_the_first_column, "order") == (
        StepState.NONE,
        1,
    )


def test_an_export_marks_the_last_step_done(sample_window, settle, tmp_path):
    sample_window.output_folder_name = str(tmp_path)

    sample_window.click_run()
    settle(sample_window.task_runner)
    QApplication.processEvents()

    assert _badge(sample_window, "preview") == (StepState.DONE, None)
    exported = next(tmp_path.glob("*.xlsx")).name
    assert sample_window.ui.shell.sidebar.item("preview").toolTip().endswith(exported)


def test_a_window_without_data_says_so(empty_window):
    shell = empty_window.ui.shell

    assert shell.header.context_label.text() == "No data loaded"
    assert empty_window.windowTitle() == "Clinical Reporting"
    assert shell.status_bar.summary().startswith("No data loaded")
    assert _badge(empty_window, "additional") == (StepState.OPTIONAL, None)
    assert _badge(empty_window, "stacked") == (StepState.NONE, None)
    assert _badge(empty_window, "forms") == (StepState.NONE, None)
    assert shell.display_button is None  # No theme manager given.


def test_the_status_bar_repeats_the_latest_message_until_it_is_cleared(
    sample_window,
):
    status_bar = sample_window.ui.shell.status_bar
    banner = sample_window.ui.label_save_confirmation

    sample_window._set_label_text(
        banner, feedback.warning("Cannot run:\n- Join order 2 is used twice.")
    )
    shown = status_bar.message(), status_bar.message_kind()
    sample_window._set_label_text(sample_window.ui.label_setting, "")  # Another's.
    still = status_bar.message()
    sample_window._set_label_text(banner, "")

    assert shown == ("Cannot run: Join order 2 is used twice.", "warning")
    assert still == shown[0]
    assert status_bar.message() == "" and status_bar.message_kind() == ""


def test_results_raised_on_another_page_also_show_as_a_toast(sample_window):
    sample_window.ui.shell.set_current("forms")
    saved = feedback.success("Settings saved to C:\\settings\\DSMB.json")

    sample_window._set_label_text(sample_window.ui.label_save_confirmation, saved)
    sample_window._set_label_text(
        sample_window.ui.label_run_confirmation, feedback.warning("Cannot run: …")
    )

    assert _toasts(sample_window) == [saved]  # Warnings stay in the status bar.


def test_results_on_the_open_page_show_no_toast(sample_window):
    sample_window.ui.shell.set_current("source")

    sample_window._set_label_text(
        sample_window.ui.banner_input_file, feedback.error("Could not read x.zip")
    )

    assert _toasts(sample_window) == []
    assert sample_window.ui.shell.status_bar.message_kind() == "error"


def test_a_new_zip_brings_the_additional_forms_and_forgets_the_results(
    sample_window,
):
    sample_window.additional_inputs = {"lab.csv": pd.DataFrame({"Subject": ["1"]})}
    sample_window.additional_form_names = {"lab.csv": "PK"}  # Not a DEMO01 form.
    sample_window.ui.shell.set_current(steps.ADDITIONAL)
    sample_window.ui.shell.set_current(steps.SOURCE)  # Leaving adds PK.
    QApplication.processEvents()
    applied = _badge(sample_window, "additional")
    sample_window._set_label_text(
        sample_window.ui.label_run_confirmation,
        feedback.success("Report saved successfully to C:\\DEMO01.xlsx"),
    )

    sample_window.open_input_data(
        "Core_Listings_DEMO02_sample.zip", None, sample_forms()
    )
    QApplication.processEvents()

    assert applied == (StepState.DONE, None)
    # The files' forms come along to the new report.
    assert "PK" in sample_window.report.data
    assert _badge(sample_window, "additional") == (StepState.DONE, None)
    assert sample_window.ui.label_run_confirmation.text() == ""
    assert sample_window.ui.shell.status_bar.message() == (
        "Additional input updated: 1 file added to the report. New forms: PK."
    )
    assert sample_window.windowTitle() == "DEMO02 — Clinical Reporting"


def test_removing_the_zip_empties_the_frame(sample_window):
    sample_window.click_remove_input()
    QApplication.processEvents()
    shell = sample_window.ui.shell

    assert _badge(sample_window, "source") == (StepState.NONE, None)
    assert _badge(sample_window, "forms") == (StepState.NONE, None)
    assert shell.header.context_label.text() == "No data loaded"
    assert sample_window.windowTitle() == "Clinical Reporting"


def test_a_saved_setting_brings_its_badges_back(sample_window, tmp_path):
    sample_window.settings_directory = str(tmp_path)
    sample_window.ui.checkBox_save_current_setting.setChecked(True)
    sample_window.ui.lineEdit_setting_name.setText("DSMB monthly")
    sample_window.click_save_setting()
    (saved,) = tmp_path.glob("*.json")
    sample_window.ui.tableWidget_static_filter.selectRow(0)
    sample_window.static_filter_remove()
    QApplication.processEvents()
    removed = _badge(sample_window, "filters")

    sample_window._apply_saved_setting_from_path(str(saved))
    QApplication.processEvents()

    assert removed == (StepState.NONE, None)
    assert _badge(sample_window, "filters") == (StepState.NONE, 1)


def test_the_status_bar_falls_back_to_a_message_still_showing(sample_window):
    status_bar = sample_window.ui.shell.status_bar
    problem = feedback.error("Could not read x.zip")
    sample_window._set_label_text(sample_window.ui.banner_input_file, problem)
    hint = feedback.warning("Cannot run:\n- Join order 2 is used twice.")
    sample_window._set_label_text(sample_window.ui.label_run_confirmation, hint)
    newest = status_bar.message()

    sample_window._set_label_text(sample_window.ui.label_run_confirmation, "")

    assert newest.startswith("Cannot run:")
    assert (status_bar.message(), status_bar.message_kind()) == (problem, "error")
