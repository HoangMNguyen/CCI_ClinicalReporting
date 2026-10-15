"""Removing inputs takes the stacked forms and coalesced items left without input.

Removing the Corelisting ZIP drops those made only from its forms; once no
input is left at all (no ZIP and no additional files), every stacked form and
coalesced item goes, from the pages and from the report, at once. Made-up
data: a ZIP with DM and AE, and two lab files.
"""

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QListWidget

from cci_ui.widgets.sidebar import StepState
from clinical_reporting import steps
from clinical_reporting.coalescing import CoalescedItem, Fill

ZIP = "Core_Listings_DEMO01_sample.zip"
SUBJECTS = ["101-001", "101-002", "101-003"]


def _zip_forms():
    """DM, whose Race Other has a value only where Race has none, and AE."""
    return {
        "DM": pd.DataFrame(
            {
                "Subject": SUBJECTS,
                "Site": ["101"] * 3,
                "Race": ["White", None, "Asian"],
                "Race Other": [None, "Maori", None],
            }
        ),
        "AE": pd.DataFrame(
            {
                "Subject": SUBJECTS,
                "Site": ["101"] * 3,
                "AE Term": ["Headache", "Nausea", "Rash"],
            }
        ),
    }


def _lab_a():
    """A lab file whose Result Text has a value only where Result has none."""
    return pd.DataFrame(
        {
            "Subject": SUBJECTS,
            "Site": ["101"] * 3,
            "Result": ["12", None, "30"],
            "Result Text": [None, "<5", None],
        }
    )


def _lab_b():
    return pd.DataFrame(
        {"Subject": SUBJECTS, "Site": ["101"] * 3, "Result": ["8", "9", "10"]}
    )


def _go(window, step):
    window.ui.shell.set_current(step)
    QApplication.processEvents()


def _add_file(window, path, frame, form):
    """List *path* on Additional input (open) and name its form *form*."""
    window._add_loaded_additional_files(({path: frame}, {}))
    table = window.ui.tableWidget_update_form_name
    (row,) = [
        row
        for row in range(table.rowCount())
        if table.item(row, 1).data(Qt.ItemDataRole.UserRole) == path
    ]
    table.item(row, 1).setText(form)


def _new_stacked(window, name, *members):
    """A new stacked form *name* of *members*, typed and ticked on its page."""
    _go(window, steps.STACKED)
    window.click_new_stacked_form()
    table = window.ui.tableWidget_stacked_forms
    row = table.rowCount() - 1
    edit = table.cellWidget(row, 0)
    edit.selectAll()
    QTest.keyClicks(edit, name)
    box = table.cellWidget(row, 1)
    box.showPopup()
    rows = box.findChild(QListWidget)
    for member in members:
        (item,) = rows.findItems(member, Qt.MatchFlag.MatchExactly)
        center = rows.visualItemRect(item).center()
        QTest.mouseClick(rows.viewport(), Qt.MouseButton.LeftButton, pos=center)
    box.hidePopup()


def _pick(box, text):
    box.setCurrentIndex(box.findText(text))


def _new_coalesced(window, form, first, then):
    """A new coalesced item of *form*: *first*, then *then* where empty."""
    _go(window, steps.COALESCED)
    window.click_new_coalesced_item()
    fills = window.ui.tableWidget_coalesced_fills
    _pick(window.ui.comboBox_coalesced_form, form)
    _pick(fills.cellWidget(0, 1), first)
    _pick(fills.cellWidget(1, 1), then)


def _names(window):
    """The report's stacked forms and coalesced items, by name."""
    report = window.report
    return (
        [stacked.name for stacked in report.stacked_forms],
        [item.name for item in report.coalesced_items],
    )


def _page_rows(window):
    """How many stacked forms and coalesced items their pages list."""
    return (
        window.ui.tableWidget_stacked_forms.rowCount(),
        window.ui.tableWidget_coalesced_items.rowCount(),
    )


def _states(window):
    QApplication.processEvents()
    sidebar = window.ui.shell.sidebar
    return sidebar.item(steps.STACKED).state(), sidebar.item(steps.COALESCED).state()


def test_removing_the_only_input_resets_the_stacked_forms_and_coalesced_items(
    sample_window,
):
    window = sample_window
    window.open_input_data(ZIP, None, _zip_forms())
    _new_stacked(window, "BOTH", "DM", "AE")
    _new_coalesced(window, "DM", "Race", "Race Other")
    _go(window, steps.SOURCE)  # Both reach the report.
    before = _names(window)

    window.click_remove_input()

    assert before == (["BOTH"], ["Race"])
    assert _names(window) == ([], [])
    assert _page_rows(window) == (0, 0)
    assert _states(window) == (StepState.NONE, StepState.NONE)
    assert window.ui.banner_run_state.text() == (
        "Cannot run: Load report data before running. Select at least one form "
        "before running."
    )


def test_removing_the_zip_drops_what_was_made_only_from_its_forms(
    sample_window, tmp_path
):
    window = sample_window
    window.open_input_data(ZIP, None, _zip_forms())
    _go(window, steps.ADDITIONAL)
    _add_file(window, str(tmp_path / "lab_a.csv"), _lab_a(), "LAB")
    _new_stacked(window, "BOTH", "DM", "AE")  # Leaving Additional input adds LAB.
    _new_coalesced(window, "DM", "Race", "Race Other")
    _new_coalesced(window, "LAB", "Result", "Result Text")
    _go(window, steps.SOURCE)
    before = _names(window)

    window.click_remove_input()

    assert before == (["BOTH"], ["Race", "Result"])
    # LAB's coalesced item stays, and reaches the report without the ZIP.
    assert window.report.stacked_forms == []
    assert window.report.coalesced_items == [
        CoalescedItem("LAB", "Result", "Result", (Fill("Result Text"),))
    ]
    assert _page_rows(window) == (0, 1)
    assert _states(window) == (StepState.OPTIONAL, StepState.DONE)


def test_removing_the_last_file_without_a_zip_resets_them_at_once(
    sample_window, tmp_path
):
    window = sample_window
    window.click_remove_input()  # The files are the only input from here.
    _go(window, steps.ADDITIONAL)
    _add_file(window, str(tmp_path / "lab_a.csv"), _lab_a(), "LBA")
    _add_file(window, str(tmp_path / "lab_b.csv"), _lab_b(), "LBB")
    _new_stacked(window, "LABS", "LBA", "LBB")
    _new_coalesced(window, "LBA", "Result", "Result Text")
    _go(window, steps.ADDITIONAL)  # Both reach the report.
    before = _names(window)
    files = window.ui.listWidget_additional_file
    files.selectAll()

    window.click_remove_additional_files()

    assert before == (["LABS"], ["Result"])
    # While Additional input is still open.
    assert window.ui.shell.current() == steps.ADDITIONAL
    assert _names(window) == ([], [])
    assert _page_rows(window) == (0, 0)


def test_removing_the_files_while_a_zip_is_loaded_resets_nothing(
    sample_window, tmp_path
):
    window = sample_window
    window.open_input_data(ZIP, None, _zip_forms())
    _go(window, steps.ADDITIONAL)
    _add_file(window, str(tmp_path / "lab_a.csv"), _lab_a(), "LAB")
    _new_stacked(window, "BOTH", "DM", "AE")
    _new_coalesced(window, "LAB", "Result", "Result Text")
    _go(window, steps.ADDITIONAL)
    files = window.ui.listWidget_additional_file
    files.selectAll()

    window.click_remove_additional_files()

    assert _names(window) == (["BOTH"], ["Result"])
    assert _page_rows(window) == (1, 1)
