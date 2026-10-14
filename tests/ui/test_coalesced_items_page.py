"""The Coalesced items page, on a made-up DM form with Race and Race Other Specify.

Six subjects have Race "Other" and say which in Race Other Specify; one has
no Race but a Race Other Specify. Coalescing the two with the condition
``= Other`` fills all seven without an overlap; without the condition, the
six "Other" rows overlap. The page keeps its own coalesced items until
"Apply to report"; badges refresh once control returns to the event loop.
"""

import json

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from cci_ui.widgets.sidebar import StepState
from clinical_reporting.coalescing import KEEP_EARLIER, CoalescedItem, Fill
from clinical_reporting.ui.pages._common import ItemBox

ZIP = "Core_Listings_DEMO01_sample.zip"
NOT_APPLIED = "Not applied yet. Apply to report to use your changes."
RACE = CoalescedItem("DM", "Race", "Race", (Fill("Race Other Specify", "=", "Other"),))


def _forms():
    dm = pd.DataFrame(
        {
            "Subject": [f"101-00{n}" for n in range(1, 10)],
            "Site": ["101"] * 9,
            "Race": ["White", *["Other"] * 6, None, "Asian"],
            "Race Other Specify": [
                None,
                "Maori",
                "Samoan",
                "Fijian",
                "Tongan",
                "Hmong",
                "Lao",
                "Ainu",
                None,
            ],
            "Age": [34, 51, 47, 29, 62, 38, 45, 57, 40],
        }
    )
    ae = pd.DataFrame(
        {
            "Subject": ["101-001", "101-002"],
            "Site": ["101", "101"],
            "AE Term": ["Headache", "Nausea"],
        }
    )
    return {"DM": dm, "AE": ae}


def _open(window):
    window.open_input_data(ZIP, None, _forms())
    window.ui.shell.set_current("coalesced")
    QApplication.processEvents()


def _pick(box, text):
    box.setCurrentIndex(box.findText(text))


def _set_condition(window, row, operator, value=""):
    fills = window.ui.tableWidget_coalesced_fills
    _pick(fills.cellWidget(row, 2), operator)
    if value:
        fills.item(row, 3).setText(value)


def _new_race(window, operator="=", value="Other"):
    """A new coalesced item of DM: Race, then Race Other Specify where *operator*."""
    window.click_new_coalesced_item()
    fills = window.ui.tableWidget_coalesced_fills
    _pick(window.ui.comboBox_coalesced_form, "DM")
    _pick(fills.cellWidget(0, 1), "Race")
    _pick(fills.cellWidget(1, 1), "Race Other Specify")
    if operator:
        _set_condition(window, 1, operator, value)


def _cells(table, row):
    return [table.item(row, column).text() for column in range(table.columnCount())]


def _column(table, column):
    return [table.item(row, column).text() for row in range(table.rowCount())]


def _badge(window):
    QApplication.processEvents()
    item = window.ui.shell.sidebar.item("coalesced")
    return item.state(), item.count()


def test_a_coalesced_item_takes_the_place_of_its_items_once_applied(sample_window):
    window = sample_window
    ui = window.ui
    _open(window)
    _new_race(window)
    before = (ui.banner_coalesced_state.text(), _badge(window))
    editor = (
        ui.label_coalesced_editor.text(),
        ui.comboBox_coalesced_name.currentText(),
        ui.label_coalesced_counts.text(),
        _column(ui.tableWidget_coalesced_fills, 4),
        _cells(ui.tableWidget_coalesced_items, 0),
        ui.banner_coalesced_item.text(),
    )

    window.click_apply_coalesced_items()

    assert before == (NOT_APPLIED, (StepState.OPTIONAL, None))
    assert editor == (
        "Race in DM",
        "Race",
        "DM has 9 rows: 2 keep Race · 7 filled from Race Other Specify · "
        "0 left empty · 0 rows overlap",
        ["2", "7"],
        ["Race", "DM", "Race, Race Other Specify", "7", "0", "Refuse"],
        "",
    )
    assert window.report.coalesced_items == [RACE]
    dm = window.report.data["DM"]
    assert list(dm.columns) == ["Subject", "Site", "Race", "Age"]
    assert list(dm["Race"]) == [
        "White",
        "Maori",
        "Samoan",
        "Fijian",
        "Tongan",
        "Hmong",
        "Lao",
        "Ainu",
        "Asian",
    ]
    assert ui.banner_coalesced.text() == (
        "Applied. Coalesced items: Race in DM (7 rows filled)."
    )
    assert ui.banner_coalesced.kind() == "success"
    assert ui.banner_coalesced_state.text() == ""
    assert _badge(window) == (StepState.DONE, None)


OVERLAPS = (
    "6 rows have a value in Race Other Specify where Race already has one: "
    "101-002 (Other / Maori), 101-003 (Other / Samoan), 101-004 (Other / Fijian), "
    "101-005 (Other / Tongan), 101-006 (Other / Hmong)"
)


def test_overlaps_refuse_apply_until_the_earlier_values_are_kept(sample_window):
    window = sample_window
    ui = window.ui
    _open(window)
    _new_race(window, operator="")
    editor = (
        ui.label_coalesced_counts.text(),
        ui.banner_coalesced_item.text(),
        _cells(ui.tableWidget_coalesced_items, 0),
    )

    window.click_apply_coalesced_items()
    banner = ui.banner_coalesced
    refused = (banner.text(), banner.kind(), banner.details())
    applied_then = list(window.report.coalesced_items)
    _pick(ui.comboBox_coalesced_overlap, "Keep the earlier value")
    kept = (ui.banner_coalesced_item.text(), _cells(ui.tableWidget_coalesced_items, 0))
    window.click_apply_coalesced_items()

    assert editor == (
        "DM has 9 rows: 8 keep Race · 1 filled from Race Other Specify · "
        "0 left empty · 6 rows overlap",
        f"Can't apply yet: {OVERLAPS} and 1 more.",
        ["Race", "DM", "Race, Race Other Specify", "1", "6", "Refuse"],
    )
    assert refused == (
        "Not applied. Fix this problem first, then apply again.\n"
        f"- Race in DM: {OVERLAPS} and 1 more.",
        "error",
        f"Race in DM: {OVERLAPS}, 101-007 (Other / Lao).",
    )
    assert applied_then == []
    assert kept == (
        "",
        ["Race", "DM", "Race, Race Other Specify", "1", "6", "Keep the earlier value"],
    )
    assert window.report.coalesced_items == [
        CoalescedItem("DM", "Race", "Race", (Fill("Race Other Specify"),), KEEP_EARLIER)
    ]
    assert list(window.report.data["DM"]["Race"]) == [
        "White",
        *["Other"] * 6,
        "Ainu",
        "Asian",
    ]
    assert banner.text() == "Applied. Coalesced items: Race in DM (1 row filled)."


def _type_name(window, text):
    edit = window.ui.comboBox_coalesced_name.lineEdit()
    edit.selectAll()
    QTest.keyClicks(edit, text)


def test_a_taken_name_turns_red_with_the_reason_as_its_tooltip(sample_window):
    window = sample_window
    ui = window.ui
    name = ui.comboBox_coalesced_name
    _open(window)
    _new_race(window)

    _type_name(window, "Age")
    taken = (name.property("invalid"), name.toolTip(), ui.label_coalesced_editor.text())
    _type_name(window, "Race (all)")
    free = (name.property("invalid"), name.toolTip(), ui.label_coalesced_editor.text())

    assert taken == (True, "DM already has an item called Age.", "Age in DM")
    assert ui.banner_coalesced_item.text() == ""
    assert free == (False, "", "Race (all) in DM")
    assert _cells(ui.tableWidget_coalesced_items, 0)[0] == "Race (all)"


def _rows(window):
    """The items table: each row's item, condition and value."""
    fills = window.ui.tableWidget_coalesced_fills
    shown = []
    for row in range(fills.rowCount()):
        item = fills.cellWidget(row, 1).currentText()
        box = fills.cellWidget(row, 2)
        condition = fills.item(row, 2).text() if box is None else box.currentText()
        shown.append((item, condition, fills.item(row, 3).text()))
    return shown


def _selected(window):
    fills = window.ui.tableWidget_coalesced_fills
    return [index.row() for index in fills.selectionModel().selectedRows()]


def test_items_move_add_and_remove_and_row_one_has_no_condition(sample_window):
    window = sample_window
    ui = window.ui
    fills = ui.tableWidget_coalesced_fills
    _open(window)
    _new_race(window)

    window.click_add_item_to_coalesced()
    added = (_rows(window)[2], _selected(window))
    offered = [fills.cellWidget(2, 1).itemText(i) for i in range(3)]
    _pick(fills.cellWidget(2, 1), "Age")
    fills.selectRow(1)
    window.click_move_item_up_in_coalesced()
    name = ui.comboBox_coalesced_name
    moved_up = (_rows(window), _selected(window), name.currentText())
    first_value_editable = bool(fills.item(0, 3).flags() & Qt.ItemFlag.ItemIsEditable)
    up_enabled = ui.pushButton_coalesced_up.isEnabled()
    window.click_move_item_down_in_coalesced()
    moved_down = (_rows(window), _selected(window))
    fills.selectRow(2)
    window.click_remove_item_from_coalesced()
    removed = (_rows(window), _selected(window))
    window.click_remove_item_from_coalesced()

    assert added == (("", "—", ""), [2])
    assert offered == ["Subject", "Site", "Age"]
    assert moved_up == (
        [
            ("Race Other Specify", "starts the value", ""),
            ("Race", "—", ""),
            ("Age", "—", ""),
        ],
        [0],
        "Race Other Specify",  # The name follows the first item.
    )
    assert not first_value_editable and not up_enabled
    assert moved_down == (
        [
            ("Race", "starts the value", ""),
            ("Race Other Specify", "—", ""),
            ("Age", "—", ""),
        ],
        [1],
    )
    assert removed == (
        [("Race", "starts the value", ""), ("Race Other Specify", "—", "")],
        [1],
    )
    # Two rows stay: removing one of them clears it.
    assert _rows(window) == [("Race", "starts the value", ""), ("", "—", "")]
    assert ui.label_coalesced_counts.text() == (
        "Pick its form and at least two of its items to see how it fills."
    )
    assert _column(fills, 4) == ["", ""]


def test_a_new_zip_keeps_the_coalesced_items_and_asks_for_apply_again(sample_window):
    window = sample_window
    ui = window.ui
    _open(window)
    _new_race(window)
    window.click_apply_coalesced_items()

    window.open_input_data("Core_Listings_DEMO02_sample.zip", None, _forms())
    asked = ui.banner_coalesced_state.text()
    listed = _cells(ui.tableWidget_coalesced_items, 0)
    dropped = (list(window.report.coalesced_items), ui.banner_coalesced.text())
    window.click_apply_coalesced_items()

    assert asked == (
        "The new Corelisting ZIP started a new report. Apply the coalesced items "
        "again to add them to it."
    )
    assert listed == ["Race", "DM", "Race, Race Other Specify", "7", "0", "Refuse"]
    assert dropped == ([], "")
    assert window.report.coalesced_items == [RACE]
    assert "Race Other Specify" not in window.report.data["DM"].columns
    assert ui.banner_coalesced_state.text() == ""


def _save_setting(window, folder, name="Race review"):
    window.settings_directory = str(folder)
    window.ui.checkBox_save_current_setting.setChecked(True)
    window.ui.lineEdit_setting_name.setText(name)
    window.click_save_setting()


def test_saving_with_unapplied_coalesced_items_says_they_werent_saved(
    sample_window, tmp_path
):
    window = sample_window
    _open(window)
    _new_race(window)

    _save_setting(window, tmp_path)
    (saved,) = tmp_path.glob("*.json")
    message = window.ui.label_save_confirmation.text()

    assert message.kind == "warning"
    assert message == (
        f"Settings saved to {saved}. Coalesced items has changes that aren't "
        "applied, so they weren't saved."
    )
    assert "coalesced_items" not in json.loads(saved.read_text(encoding="utf-8"))


def test_saving_with_both_pages_unapplied_names_both(sample_window, tmp_path):
    window = sample_window
    _open(window)
    _new_race(window)
    window.click_new_stacked_form()

    _save_setting(window, tmp_path)
    (saved,) = tmp_path.glob("*.json")

    assert window.ui.label_save_confirmation.text() == (
        f"Settings saved to {saved}. Stacked forms has changes that aren't "
        "applied, so they weren't saved. Coalesced items has changes that aren't "
        "applied, so they weren't saved."
    )


def test_loading_a_setting_brings_its_coalesced_items_to_the_page(
    sample_window, tmp_path
):
    window = sample_window
    ui = window.ui
    table = ui.tableWidget_coalesced_items
    _open(window)
    _new_race(window)
    window.click_apply_coalesced_items()
    _save_setting(window, tmp_path)
    table.selectRow(0)
    window.click_remove_coalesced_item()
    window.click_apply_coalesced_items()
    removed = (list(window.report.coalesced_items), ui.banner_coalesced.text())
    window.click_new_coalesced_item()
    before = (_cells(table, 0), ui.banner_coalesced_state.text())

    ui.checkBox_saved_setting.setChecked(True)
    combo = ui.comboBox_saved_setting
    combo.setCurrentIndex(combo.findText("Race review"))

    assert removed == ([], "The coalesced items were removed from the report.")
    assert before == (
        ["New coalesced item", "AE", "", "—", "—", "Refuse"],
        NOT_APPLIED,
    )
    assert window.report.coalesced_items == [RACE]
    assert table.rowCount() == 1
    assert _cells(table, 0) == [
        "Race",
        "DM",
        "Race, Race Other Specify",
        "7",
        "0",
        "Refuse",
    ]
    assert ui.label_coalesced_editor.text() == "Race in DM"
    assert _rows(window) == [
        ("Race", "starts the value", ""),
        ("Race Other Specify", "=", "Other"),
    ]
    assert ui.banner_coalesced_state.text() == ""


def test_a_new_coalesced_item_takes_the_form_being_edited(sample_window):
    window = sample_window
    ui = window.ui
    fills = ui.tableWidget_coalesced_fills
    _open(window)
    _new_race(window)

    window.click_new_coalesced_item()
    box = fills.cellWidget(0, 1)

    assert ui.comboBox_coalesced_form.currentText() == "DM"
    assert ui.label_coalesced_editor.text() == "New coalesced item in DM"
    # Race and Race Other Specify are in the other coalesced item of DM.
    assert [box.itemText(i) for i in range(box.count())] == ["Subject", "Site", "Age"]
    assert _rows(window) == [("", "starts the value", ""), ("", "—", "")]
    assert ui.banner_coalesced_item.text() == (
        "Can't apply yet:\n- Pick an item in each row.\n- Give it a name."
    )


def test_another_form_starts_its_items_over_but_keeps_a_typed_name(sample_window):
    window = sample_window
    ui = window.ui
    _open(window)
    _new_race(window)

    # The name only followed Race, so it goes with the items.
    _pick(ui.comboBox_coalesced_form, "AE")

    assert ui.comboBox_coalesced_name.currentText() == ""
    assert _rows(window) == [("", "starts the value", ""), ("", "—", "")]

    _type_name(window, "Origin")
    _pick(ui.comboBox_coalesced_form, "DM")

    assert ui.comboBox_coalesced_name.currentText() == "Origin"
    assert _rows(window) == [("", "starts the value", ""), ("", "—", "")]


def test_an_item_box_shows_its_problem_after_its_item(qapp):
    box = ItemBox(["DM.Age", "DM.Sex"], "DM.Age")

    box.set_problem("DM.Age is in it twice.")
    marked = (box.property("invalid"), box.toolTip())
    box.setCurrentIndex(box.findText("DM.Sex"))
    picked_again = box.toolTip()
    box.set_problem("")
    cleared = (box.property("invalid"), box.toolTip())

    assert marked == (True, "DM.Age\nDM.Age is in it twice.")
    assert picked_again == "DM.Sex\nDM.Age is in it twice."
    assert cleared == (False, "DM.Sex\nPick an item, or type to find one")
