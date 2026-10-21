"""The Stacked forms page, on the DEMO01 sample report.

The sample's EOT (Reason) and DS (Status) forms share Subject, Site and
Visit, so stacking them leaves Reason and Status out until they are matched,
here as "Disposition". The page keeps its own stacked forms until the user
goes to another step; badges refresh once control returns to the event loop.
"""

import pandas as pd
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QHelpEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QListWidget, QToolTip

from cci_ui.widgets.checklist import ChecklistComboBox
from cci_ui.widgets.sidebar import StepState
from clinical_reporting.sample_data import STUDY, sample_forms
from clinical_reporting.stacking import Match, StackedForm
from clinical_reporting.ui.pages.stacked_forms import TICK_ROLE

UPDATED = "Stacked forms updated: DISP (48 rows from EOT, DS)."
DISP = StackedForm(
    "DISP", ("EOT", "DS"), (Match("Disposition", {"EOT": "Reason", "DS": "Status"}),)
)


def _open(window):
    window.ui.shell.set_current("stacked")
    QApplication.processEvents()


def _leave(window):
    """Go to another step: the Data steps' changes reach the report."""
    window.ui.shell.set_current("forms")
    QApplication.processEvents()


def _set_additional_files(window, files, names):
    """List *files* named *names* on Additional input, then come to this page."""
    window.ui.shell.set_current("additional")
    window.additional_inputs = files
    window.additional_form_names = names
    _open(window)


def _type_name(window, row, text):
    edit = window.ui.tableWidget_stacked_forms.cellWidget(row, 0)
    edit.selectAll()
    QTest.keyClicks(edit, text)


def _tick(window, row, *forms):
    """Tick (or untick) *forms* in *row*'s Members checklist, in this order."""
    box = window.ui.tableWidget_stacked_forms.cellWidget(row, 1)
    box.showPopup()
    rows = box.findChild(QListWidget)
    for form in forms:
        (item,) = rows.findItems(form, Qt.MatchFlag.MatchExactly)
        center = rows.visualItemRect(item).center()
        QTest.mouseClick(rows.viewport(), Qt.MouseButton.LeftButton, pos=center)
    box.hidePopup()


def _new_stacked_form(window, name, *members):
    _open(window)
    window.click_new_stacked_form()
    row = window.ui.tableWidget_stacked_forms.rowCount() - 1
    _type_name(window, row, name)
    _tick(window, row, *members)
    return row


def _grid_rows(window):
    model = window.ui.tableView_stacked_items.model()
    return [model.index(row, 0).data() for row in range(model.rowCount())]


def _ticks(window, name):
    model = window.ui.tableView_stacked_items.model()
    row = _grid_rows(window).index(name)
    return [
        bool(model.index(row, column).data(TICK_ROLE))
        for column in range(1, model.columnCount())
    ]


def _headers(window):
    model = window.ui.tableView_stacked_items.model()
    return [
        model.headerData(column, Qt.Orientation.Horizontal)
        for column in range(model.columnCount())
    ]


def _click_item(window, name, modifier=Qt.KeyboardModifier.NoModifier, double=False):
    grid = window.ui.tableView_stacked_items
    row = _grid_rows(window).index(name)
    center = grid.visualRect(grid.model().index(row, 1)).center()
    QTest.mouseClick(grid.viewport(), Qt.MouseButton.LeftButton, modifier, center)
    if double:  # A double-click's second press, after the first click.
        QTest.mouseDClick(grid.viewport(), Qt.MouseButton.LeftButton, modifier, center)


def _cell(window, name, column):
    """The dropdown in *name*'s matched row under member *column* (1 is the first)."""
    grid = window.ui.tableView_stacked_items
    return grid.cell_widget(_grid_rows(window).index(name), column)


def _entries(box):
    return [box.itemText(i) for i in range(box.count())]


def _pick(box, text):
    """Pick *text* in a matched cell's dropdown, with a click in its list."""
    box.showPopup()
    view = box.view()
    center = view.visualRect(view.model().index(box.findText(text), 0)).center()
    QTest.mouseMove(view.viewport(), center)
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=center)


def _type_into(box, text):
    """Type *text* over a matched cell's text, then Enter."""
    box.lineEdit().selectAll()
    QTest.keyClicks(box.lineEdit(), text)
    QTest.keyClick(box.lineEdit(), Qt.Key.Key_Return)


def _add_files(window, tmp_path, **columns):
    """Add one additional file per form: Subject, Site, Visit and its *columns*.

    Each form gets one column name or a tuple of them.
    """
    rows = {"Subject": ["01-100"], "Site": ["01"], "Visit": ["Screening"]}
    paths = {form: str(tmp_path / f"{form.lower()}.csv") for form in columns}
    files = {}
    for form, names in columns.items():
        names = (names,) if isinstance(names, str) else names
        files[paths[form]] = pd.DataFrame({**rows, **{name: ["x"] for name in names}})
    _set_additional_files(window, files, {paths[form]: form for form in columns})


def _match_disposition(window):
    """DISP: EOT and DS, Reason and Status matched as Disposition."""
    _new_stacked_form(window, "DISP", "EOT", "DS")
    _click_item(window, "Reason")
    _click_item(window, "Status", Qt.KeyboardModifier.ControlModifier)
    window.click_match_stacked_items()
    grid = window.ui.tableView_stacked_items
    grid.first_widget(_grid_rows(window).index("Reason")).setCurrentText("Disposition")


def _badge(window):
    QApplication.processEvents()
    item = window.ui.shell.sidebar.item("stacked")
    return item.state(), item.count()


def test_members_ticked_line_up_their_items_in_the_order_ticked(sample_window):
    window = sample_window
    row = _new_stacked_form(window, "DISP", "DS", "EOT")
    table = window.ui.tableWidget_stacked_forms
    panel = window.ui.panel_stacked_items
    shown = (
        table.cellWidget(row, 1).currentText(),
        table.item(row, 2).text(),
        table.item(row, 3).text(),
    )
    title = window.ui.label_stacked_items.text()
    headers = _headers(window)
    rows = _grid_rows(window)
    ticks = (_ticks(window, "Reason"), _ticks(window, "Status"))
    grid = window.ui.tableView_stacked_items
    every = grid.visualRect(grid.model().index(0, 0)).center()  # The whole row.
    QTest.mouseClick(grid.viewport(), Qt.MouseButton.LeftButton, pos=every)
    opened = _grid_rows(window)[:4]
    _tick(window, row, "DS")

    assert shown == ("DS, EOT", "3", "48")
    assert title == "Items of DISP"
    assert headers == ["Stacked item", "DS  24 rows", "EOT  24 rows"]
    assert rows == [
        "In every member",
        "Matched",
        "No matches yet. Select left-out items below, then Match.",
        "Left out",
        "Status",
        "Reason",
    ]
    assert ticks == ([False, True], [True, False])
    assert opened == ["In every member", "Subject", "Site", "Visit"]
    assert panel.message() == (
        "Pick two or more forms in Members to see how their items line up."
    )
    assert table.cellWidget(row, 1).currentText() == "EOT"


def test_a_page_without_a_selected_stacked_form_says_how_to_make_one(sample_window):
    _open(sample_window)

    assert sample_window.ui.panel_stacked_items.message() == (
        "Select a stacked form above, or make one with New stacked form."
    )
    assert not sample_window.ui.pushButton_stacked_remove.isEnabled()


def test_names_that_cant_be_used_turn_red_as_they_are_typed(sample_window):
    window = sample_window
    _new_stacked_form(window, "DM", "EOT", "DS")
    edit = window.ui.tableWidget_stacked_forms.cellWidget(0, 0)
    named_like_a_form = (edit.property("invalid"), edit.toolTip())
    _type_name(window, 0, "DISP")
    renamed = (edit.property("invalid"), edit.toolTip())
    _click_item(window, "Reason", double=True)
    grid = window.ui.tableView_stacked_items
    box = grid.first_widget(_grid_rows(window).index("Reason"))

    box.setCurrentText("Subject")  # An item every member has.
    taken = (box.property("invalid"), box.toolTip())
    box.setCurrentText("Disposition")

    assert named_like_a_form == (True, "DM is already a loaded form.")
    assert renamed == (False, "")
    assert taken == (True, "DISP already has an item called Subject.")
    assert (box.property("invalid"), box.toolTip()) == (
        False,
        "Pick one of the matched names, or type a new one",
    )


def test_other_steps_leave_the_page_as_it_was(sample_window):
    window = sample_window
    _new_stacked_form(window, "DISP", "EOT", "DS")
    window.ui.lineEdit_stacked_item_search.setText("Rea")
    _click_item(window, "Reason")

    window.report.add_selected_form("EOT")  # As the Forms page does.
    window.update_all_ui()

    assert window.ui.lineEdit_stacked_item_search.text() == "Rea"
    assert _grid_rows(window)[-2:] == ["Left out", "Reason"]
    assert window.ui.tableView_stacked_items.selected_keys() == [("left", "Reason")]


def test_match_lines_up_left_out_items_and_unmatch_takes_them_back(sample_window):
    window = sample_window
    _new_stacked_form(window, "DISP", "EOT", "DS")
    match_button = window.ui.pushButton_stacked_match
    _click_item(window, "Reason")
    _click_item(window, "Status", Qt.KeyboardModifier.ControlModifier)
    ready = (match_button.isEnabled(), match_button.toolTip())

    window.click_match_stacked_items()
    matched = _grid_rows(window)
    grid = window.ui.tableView_stacked_items
    selected = grid.selected_keys()
    box = grid.first_widget(_grid_rows(window).index("Reason"))
    choices = [box.itemText(i) for i in range(box.count())]
    box.setCurrentText("Disposition")
    unmatch = window.ui.pushButton_stacked_unmatch.isEnabled()
    items = window.ui.tableWidget_stacked_forms.item(0, 2).text()
    window.click_unmatch_stacked_items()

    assert ready == (True, "Match Reason with Status into one stacked item")
    assert matched == [
        "In every member",
        "Matched",
        "Reason",
        "Left out",
        "Nothing left out.",
    ]
    assert selected == [("matched", 0)]
    assert choices == ["Reason", "Status"]
    assert unmatch and items == "4"
    assert _grid_rows(window)[-3:] == ["Left out", "Reason", "Status"]


def test_match_refuses_two_items_of_one_member_and_double_click_keeps_one(
    sample_window,
):
    window = sample_window
    _new_stacked_form(window, "VITALS", "DM", "VS")
    match_button = window.ui.pushButton_stacked_match
    _click_item(window, "Age")
    _click_item(window, "Sex", Qt.KeyboardModifier.ControlModifier)
    refused = (match_button.isEnabled(), match_button.toolTip())

    _click_item(window, "Pulse", double=True)

    assert refused == (
        False,
        "Pick at most one item from each member: DM has both Age and Sex.",
    )
    rows = _grid_rows(window)
    assert rows[rows.index("Matched") + 1] == "Pulse"
    assert _ticks(window, "Age") == [True, False]


def test_a_matched_cell_changes_its_members_item_from_a_dropdown(sample_window):
    window = sample_window
    _new_stacked_form(window, "DISP", "EOT", "DS")
    _click_item(window, "Reason", double=True)  # Reason on its own.
    eot, ds = _cell(window, "Reason", 1), _cell(window, "Reason", 2)
    listed = (_entries(eot), eot.currentText(), _entries(ds), ds.currentText())
    heading = ds.model().item(_entries(ds).index("Other items"))

    _pick(ds, "Status")
    picked = (_cell(window, "Reason", 2).currentText(), _grid_rows(window)[-1])
    in_report = list(window.report.stacked_forms)
    _pick(_cell(window, "Reason", 1), "—")
    cleared = (_cell(window, "Reason", 1).currentText(), _grid_rows(window)[-2:])
    _pick(_cell(window, "Reason", 2), "—")

    assert listed == (["—", "Reason"], "Reason", ["—", "Other items", "Status"], "—")
    assert not heading.isEnabled()
    assert picked == ("Status", "Nothing left out.")
    assert in_report == []  # Not until the user goes to another step.
    # The match keeps its name; EOT's Reason is left out again.
    assert cleared == ("—", ["Left out", "Reason"])
    # With no item left, the match goes.
    assert _grid_rows(window)[1:] == [
        "Matched",
        "No matches yet. Select left-out items below, then Match.",
        "Left out",
        "Reason",
        "Status",
    ]


def test_picking_an_item_brings_in_every_member_with_its_name(sample_window, tmp_path):
    window = sample_window
    _add_files(window, tmp_path, NOTEA="Comment", NOTEB="Comment")
    _new_stacked_form(window, "ENDS", "EOT", "NOTEA", "NOTEB")
    _click_item(window, "Reason", double=True)

    _pick(_cell(window, "Reason", 2), "Comment")
    cells = [_cell(window, "Reason", column).currentText() for column in (1, 2, 3)]
    tip = _cell(window, "Reason", 3).itemData(0, Qt.ItemDataRole.ToolTipRole)

    assert cells == ["Reason", "Comment", "Comment"]
    assert tip == "Choosing — also clears NOTEA, which gives Comment too."
    assert _grid_rows(window)[-2:] == ["Left out", "Nothing left out."]


def test_typing_in_a_matched_cell_picks_only_a_whole_item_name(sample_window):
    window = sample_window
    _new_stacked_form(window, "DISP", "EOT", "DS")
    _click_item(window, "Reason", double=True)

    _type_into(_cell(window, "Reason", 2), "Stat")
    kept = (_cell(window, "Reason", 2).currentText(), _grid_rows(window)[-1])
    _type_into(_cell(window, "Reason", 2), "status")

    assert kept == ("—", "Status")
    assert _cell(window, "Reason", 2).currentText() == "Status"
    assert _grid_rows(window)[-1] == "Nothing left out."


def test_a_cell_whose_member_lost_its_item_warns_until_one_is_picked(
    sample_window, tmp_path
):
    window = sample_window
    _add_files(window, tmp_path, OUT="Outcome")
    _new_stacked_form(window, "ENDS", "EOT", "OUT")
    _click_item(window, "Reason")
    _click_item(window, "Outcome", Qt.KeyboardModifier.ControlModifier)
    window.click_match_stacked_items()
    _leave(window)
    _add_files(window, tmp_path, OUT="Result")  # The next file renamed Outcome.
    box = _cell(window, "Reason", 2)
    warned = (box.currentText(), box.toolTip(), box.itemIcon(0).isNull())

    _pick(box, "Result")
    fixed = _cell(window, "Reason", 2)

    assert warned == ("—", "OUT has no Outcome", False)
    # No warning left: the cell's tooltip says how to use it instead.
    assert (fixed.currentText(), fixed.toolTip()) == (
        "Result",
        "Pick an item, or type to find one",
    )
    # The pick reaches the report when the user goes to another step.
    assert window.report.stacked_forms[0].matches[0].items["OUT"] == "Outcome"


def test_a_member_with_two_items_of_a_match_stops_the_export_until_its_cell_is_cleared(
    sample_window, tmp_path
):
    window = sample_window
    _add_files(window, tmp_path, OUT="Outcome")
    _new_stacked_form(window, "ENDS", "EOT", "OUT")
    _click_item(window, "Reason")
    _click_item(window, "Outcome", Qt.KeyboardModifier.ControlModifier)
    window.click_match_stacked_items()
    _leave(window)
    before = _badge(window)
    # The next file also has a Reason column: OUT now gives the match two items.
    _add_files(window, tmp_path, OUT=("Outcome", "Reason"))
    stopped = (_badge(window), [issue.message for issue in window.report.validate()])
    box = _cell(window, "Reason", 2)
    marked = (box.currentText(), box.property("invalid"), box.toolTip())

    _pick(box, "Outcome")  # Picking the item it shows again confirms nothing.
    box = _cell(window, "Reason", 2)
    again = (box.property("invalid"), box.toolTip())
    _pick(box, "—")
    box = _cell(window, "Reason", 2)
    cleared = (box.currentText(), bool(box.property("invalid")))
    _leave(window)

    problem = "Pick at most one item from each member: OUT has both Reason and Outcome."
    assert before == (StepState.DONE, None)
    assert stopped == (
        (StepState.ERROR, None),
        [
            "ENDS: OUT now has both Reason and Outcome, which the match Reason lines "
            "up. Choose “—” in OUT's cell or Unmatch it on Stacked forms."
        ],
    )
    assert marked == ("Outcome", True, problem)
    assert again == (True, problem)
    # "—" takes Outcome out of the match, so OUT gives its Reason.
    assert cleared == ("Reason", False)
    assert window.report.validate() == []
    assert _badge(window) == (StepState.DONE, None)


def test_a_new_stacked_form_shows_its_missing_name_and_members_in_red(sample_window):
    window = sample_window
    _open(window)

    window.click_new_stacked_form()
    table = window.ui.tableWidget_stacked_forms
    name, members = table.cellWidget(0, 0), table.cellWidget(0, 1)

    assert (name.property("invalid"), name.toolTip()) == (True, "Give it a name.")
    assert (members.property("invalid"), members.toolTip()) == (
        True,
        "Pick at least two members.",
    )
    assert _badge(window) == (StepState.ERROR, None)
    assert window.report.stacked_forms == []


def test_leaving_the_page_adds_the_stacked_form_and_keeps_the_selections(
    sample_window,
):
    window = sample_window
    _match_disposition(window)
    in_report = list(window.report.stacked_forms)
    badge = _badge(window)

    _leave(window)
    forms = window.ui.listWidget_form_available
    (disp,) = forms.findItems("DISP", Qt.MatchFlag.MatchExactly)

    assert in_report == [] and badge == (StepState.OPTIONAL, None)
    assert window.report.stacked_forms == [DISP]
    assert list(window.report.data["DISP"].columns) == [
        "Subject",
        "Site",
        "Visit",
        "Disposition",
    ]
    assert len(window.report.data["DISP"]) == 48
    assert sorted(window.report.get_selected_forms_list()) == ["AE", "DM", "VS"]
    assert window.ui.banner_stacked.text() == UPDATED
    assert window.ui.banner_stacked.kind() == "success"
    assert window.ui.shell.status_bar.message() == UPDATED
    assert window.ui.banner_stacked_state.text() == ""
    assert _badge(window) == (StepState.DONE, None)
    assert disp.toolTip() == "Stacked from EOT, DS"


def _hold_with_a_loaded_forms_name(window, tmp_path):
    """Leave DM over EOT and DS (DM is a loaded form's name).

    Saving is on, and the export has a folder and a name.
    """
    _new_stacked_form(window, "DM", "EOT", "DS")
    window.output_folder_name = str(tmp_path)
    window.ui.pathPicker_output_folder.set_path(str(tmp_path))
    window.ui.lineEdit_file_name.setText("DSMB monthly")
    window.ui.checkBox_save_current_setting.setChecked(True)
    window.ui.lineEdit_setting_name.setText("DSMB monthly")
    _leave(window)


def test_leaving_with_problems_holds_the_page(sample_window, tmp_path):
    window = sample_window

    _hold_with_a_loaded_forms_name(window, tmp_path)
    name = window.ui.tableWidget_stacked_forms.cellWidget(0, 0)
    save = window.ui.pushButton_save_setting

    assert window.report.stacked_forms == []
    assert window.ui.banner_stacked.text() == ""
    assert (name.property("invalid"), name.toolTip()) == (
        True,
        "DM is already a loaded form.",
    )
    assert _badge(window) == (StepState.ERROR, None)
    assert not window.ui.pushButton_run.isEnabled()
    assert window.ui.banner_run_state.text() == "Cannot run: Fix Stacked forms first."
    assert not save.isEnabled()
    assert save.toolTip() == (
        "Fix Stacked forms first: its changes aren't in the report yet."
    )


def test_fixing_and_leaving_again_applies(sample_window, tmp_path):
    window = sample_window
    _hold_with_a_loaded_forms_name(window, tmp_path)

    _open(window)
    _type_name(window, 0, "DISP")
    _leave(window)

    assert window.report.stacked_forms == [StackedForm("DISP", ("EOT", "DS"))]
    assert window.ui.banner_stacked.text() == UPDATED
    assert _badge(window) == (StepState.DONE, None)
    assert window.ui.pushButton_run.isEnabled()
    assert window.ui.banner_run_state.text() == ""
    assert window.ui.pushButton_save_setting.isEnabled()


def test_a_new_zip_brings_the_stacked_forms_along(sample_window):
    window = sample_window
    _match_disposition(window)
    _leave(window)

    window.open_input_data("Core_Listings_DEMO02_sample.zip", None, sample_forms())
    QApplication.processEvents()

    assert window.ui.tableWidget_stacked_forms.cellWidget(0, 0).text() == "DISP"
    assert window.report.stacked_forms == [DISP]
    assert list(window.report.data["DISP"].columns)[-1] == "Disposition"
    assert window.ui.banner_stacked_state.text() == ""
    assert _badge(window) == (StepState.DONE, None)


def test_loading_a_setting_brings_its_stacked_forms_to_the_page(
    sample_window, tmp_path
):
    window = sample_window
    _match_disposition(window)
    _leave(window)
    window.settings_directory = str(tmp_path)
    window.ui.checkBox_save_current_setting.setChecked(True)
    window.ui.lineEdit_setting_name.setText("DSMB monthly")
    window.click_save_setting()
    _open(window)
    window.ui.tableWidget_stacked_forms.selectRow(0)
    window.click_remove_stacked_form()
    _leave(window)
    removed = list(window.report.stacked_forms)
    _new_stacked_form(window, "OTHER", "CM", "EX")
    before = window.ui.tableWidget_stacked_forms.rowCount()

    window.ui.checkBox_saved_setting.setChecked(True)
    combo = window.ui.comboBox_saved_setting
    combo.setCurrentIndex(combo.findText("DSMB monthly"))
    table = window.ui.tableWidget_stacked_forms

    assert removed == [] and before == 1
    assert window.report.stacked_forms == [DISP]
    assert table.rowCount() == 1
    assert table.cellWidget(0, 0).text() == "DISP"
    assert table.cellWidget(0, 1).currentText() == "EOT, DS"
    assert window.ui.banner_stacked_state.text() == ""


def test_additional_input_holds_a_file_named_like_a_stacked_form(sample_window):
    window = sample_window
    _match_disposition(window)
    _leave(window)

    _set_additional_files(
        window, {"lab.csv": pd.DataFrame({"Subject": ["01-100"]})}, {"lab.csv": "DISP"}
    )

    assert window.update_additional_input_ui() == [
        "lab.csv: DISP is already a stacked form."
    ]
    assert list(window.report.data["DISP"].columns)[-1] == "Disposition"


def test_a_setting_whose_stacked_member_is_missing_says_what_to_add(
    sample_window, tmp_path
):
    window = sample_window
    lab = str(tmp_path / "lab_results.csv")
    _set_additional_files(
        window,
        {lab: pd.DataFrame({"Subject": ["01-100"], "ALT": [3]})},
        {lab: "LAB"},
    )
    _new_stacked_form(window, "LABS", "LAB", "EOT")
    _leave(window)
    window.settings_directory = str(tmp_path / "settings")
    window.ui.checkBox_save_current_setting.setChecked(True)
    window.ui.lineEdit_setting_name.setText("Monthly labs")
    window.click_save_setting()
    window.additional_inputs = {}
    window.additional_form_names = {}
    window.open_input_data(f"Core_Listings_{STUDY}_sample.zip", None, sample_forms())

    window.ui.checkBox_saved_setting.setChecked(True)
    combo = window.ui.comboBox_saved_setting
    combo.setCurrentIndex(combo.findText("Monthly labs"))
    members = window.ui.tableWidget_stacked_forms.cellWidget(0, 1).currentText()

    # LAB isn't selected; it is only a member of LABS.
    assert window.ui.banner_saved_names.text().startswith(
        "Still to add for “Monthly labs”: lab_results.csv (LAB)."
    )
    assert window.ui.label_setting.text().startswith("Missing forms: LAB")
    assert members == "LAB (not loaded), EOT"
    state = window.ui.banner_stacked_state.text()
    assert state == "LABS is built without LAB, which isn't loaded."
    assert state.kind == "warning"
    assert _badge(window) == (StepState.WARNING, None)


def test_removing_a_members_file_keeps_it_and_says_what_to_do(sample_window, tmp_path):
    window = sample_window
    _add_files(window, tmp_path, LAB=("Lab Test", "Result", "Unit"))
    _new_stacked_form(window, "LABS", "LB", "LAB")
    _leave(window)
    applied = window.ui.banner_stacked.text()

    _set_additional_files(window, {}, {})  # LAB's file removed on Additional input.

    assert applied == "Stacked forms updated: LABS (97 rows from LB, LAB)."
    # LAB stays a member, so adding its file again brings it back.
    assert window.ui.tableWidget_stacked_forms.cellWidget(0, 1).currentText() == (
        "LB, LAB (not loaded)"
    )
    assert window.ui.banner_stacked_state.text() == (
        "LABS is built without LAB, which isn't loaded."
    )
    assert window.ui.panel_stacked_items.message() == (
        "LAB isn't loaded. Add its file on Additional input, or untick it in Members."
    )
    # What last reached the report is out of date.
    assert window.ui.banner_stacked.text() == ""


def test_the_first_column_stays_when_the_members_scroll_sideways(sample_window):
    window = sample_window
    _new_stacked_form(window, "ALL", "DM", "VS", "AE", "LB", "CM", "EX", "EOT", "DS")
    window.resize(960, 600)
    QApplication.processEvents()
    grid = window.ui.tableView_stacked_items
    bar = grid.horizontalScrollBar()
    first = grid.frozen
    width = grid.columnWidth(0)
    before = (first.geometry(), first.columnViewportPosition(0))
    member_before = grid.columnViewportPosition(1)

    bar.setValue(bar.maximum())
    QApplication.processEvents()
    headers = _headers(window)
    tip = grid.model().headerData(
        1, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole
    )

    assert bar.maximum() > 0 and bar.value() == bar.maximum()
    # However many members, each header keeps its row count.
    assert headers == [
        "Stacked item",
        "DM  24 rows",
        "VS  96 rows",
        "AE  35 rows",
        "LB  96 rows",
        "CM  24 rows",
        "EX  24 rows",
        "EOT  24 rows",
        "DS  24 rows",
    ]
    assert tip == "DM · 24 rows"
    assert first.isVisible() and first.width() == width
    assert (first.geometry(), first.columnViewportPosition(0)) == before
    # The first member column went under the first column, which stayed.
    assert member_before == width
    assert grid.columnViewportPosition(1) == width - bar.maximum()


LONG_NAME = "Date informed consent was signed by the subject (IG_DM1.DT_ICDAT)"


def _edge(header, column):
    """A point just inside *column*'s right edge in *header*."""
    x = header.sectionViewportPosition(column) + header.sectionSize(column) - 2
    return QPoint(x, header.height() // 2)


def _drag(header, column, by):
    """Drag *column*'s right edge *by* pixels, in steps, as a mouse would."""
    start = _edge(header, column)
    left, none = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    QTest.mousePress(header.viewport(), left, none, start)
    for step in range(1, 11):
        QTest.mouseMove(header.viewport(), start + QPoint(by * step // 10, 0))
    QTest.mouseRelease(header.viewport(), left, none, start + QPoint(by, 0))
    QApplication.processEvents()


def _glide(window, view, x, from_y, to_y):
    """Move the pointer, no button held, from *from_y* to *to_y* in *view*."""
    step = 2 if to_y > from_y else -2
    for y in range(from_y, to_y, step):
        position = view.viewport().mapTo(window, QPoint(x, y))
        QTest.mouseMove(window.windowHandle(), position)
        QApplication.processEvents()


def _activate(window):
    """Make *window* active again (the Members popup took that), so focus moves."""
    window.activateWindow()
    assert QTest.qWaitForWindowActive(window)


def test_moving_the_pointer_over_rows_selects_none_of_them(sample_window):
    window = sample_window
    _new_stacked_form(window, "DMVS", "DM", "VS")
    _click_item(window, "Consent Date", double=True)  # Now a matched row.
    _activate(window)
    _click_item(window, "Age")
    grid = window.ui.tableView_stacked_items
    clicked = grid.hasFocus()  # So a cell's dropdown could take the focus.
    rows = _grid_rows(window)
    age = grid.visualRect(grid.model().index(rows.index("Age"), 2))
    matched = grid.visualRect(grid.model().index(rows.index("Consent Date"), 2))
    # Up from Age, through the margin beside the matched row's VS dropdown.
    _glide(window, grid, matched.left() + 3, age.center().y(), matched.top())
    hovered = (grid.selected_keys(), _cell(window, "Consent Date", 2).hasFocus())
    _new_stacked_form(window, "DISP", "EOT", "DS")
    _activate(window)
    table = window.ui.tableWidget_stacked_forms
    table.selectRow(0)
    table.setFocus()
    name = table.visualRect(table.model().index(1, 0))
    first = table.visualRect(table.model().index(0, 0))
    # Down from DMVS into the margin beside DISP's name field.
    _glide(window, table, name.left() + 3, first.center().y(), name.bottom())

    assert clicked
    assert hovered == ([("left", "Age")], False)
    assert window.ui.label_stacked_items.text() == "Items of DMVS"


def test_adding_a_stacked_form_leaves_one_members_box_per_row(sample_window):
    window = sample_window
    _new_stacked_form(window, "DMVS", "DM", "VS")
    _new_stacked_form(window, "ALL", "DM", "AE")
    viewport = window.ui.tableWidget_stacked_forms.viewport()

    shown = [
        box.currentText()
        for box in viewport.findChildren(ChecklistComboBox)
        if box.isVisible()
    ]

    # The box the new one replaced (deleted later by Qt) no longer shows.
    assert sorted(shown) == ["DM, AE", "DM, VS"]


def test_columns_fit_their_names_the_first_taking_at_most_its_share(
    sample_window, tmp_path
):
    window = sample_window
    _add_files(window, tmp_path, ICF=LONG_NAME)
    _new_stacked_form(window, "DATES", "EOT", "ICF")
    window.resize(960, 600)  # Too narrow for the long name in its share.
    QApplication.processEvents()
    grid = window.ui.tableView_stacked_items
    room = grid.viewport().width()
    widths = [grid.columnWidth(column) for column in range(3)]
    view = grid.frozen
    cell = view.visualRect(grid.model().index(_grid_rows(window).index(LONG_NAME), 0))
    QApplication.sendEvent(
        view.viewport(),
        QHelpEvent(
            QEvent.Type.ToolTip,
            cell.center(),
            view.viewport().mapToGlobal(cell.center()),
        ),
    )
    tip = QToolTip.text()
    _drag(view.horizontalHeader(), 0, -40)
    narrowed = [grid.columnWidth(column) for column in range(3)]

    # The long name would take more than its share, so it is cut, and its
    # tooltip shows it whole; the members share the rest of the grid, also
    # what the first column gives up when it is dragged narrower.
    assert widths[0] == int(room * 0.45)
    assert sum(widths) == room
    assert tip == LONG_NAME
    assert narrowed[0] == widths[0] - 40
    assert sum(narrowed) == room


def test_a_dragged_column_keeps_its_width_until_its_edge_is_double_clicked(
    sample_window,
):
    window = sample_window
    _new_stacked_form(window, "DMVS", "DM", "VS")
    _new_stacked_form(window, "ALL", "DM", "VS", "AE", "LB", "CM", "EX", "EOT", "DS")
    grid = window.ui.tableView_stacked_items
    first_header = grid.frozen.horizontalHeader()
    header = grid.horizontalHeader()
    table = window.ui.tableWidget_stacked_forms

    def first_and_dm():
        return grid.columnWidth(0), grid.columnWidth(1)

    fitted = first_and_dm()
    _drag(first_header, 0, 60)
    _drag(header, 1, 40)
    dragged = first_and_dm()
    window.ui.lineEdit_stacked_item_search.setText("e")  # Fills the grid again.
    searched = first_and_dm()
    window.ui.lineEdit_stacked_item_search.clear()
    table.selectRow(0)  # DMVS: DM is one of its members too.
    QApplication.processEvents()
    elsewhere = first_and_dm()
    table.selectRow(1)
    QApplication.processEvents()
    left, none = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    QTest.mouseDClick(first_header.viewport(), left, none, _edge(first_header, 0))
    QTest.mouseDClick(header.viewport(), left, none, _edge(header, 1))
    QApplication.processEvents()

    assert dragged == (fitted[0] + 60, fitted[1] + 40)
    assert searched == dragged
    assert elsewhere == dragged
    assert first_and_dm() == fitted


def test_a_long_name_shows_its_start_and_whole_in_its_tooltip(sample_window, tmp_path):
    window = sample_window
    _add_files(window, tmp_path, ICF=LONG_NAME)
    _new_stacked_form(window, "DATES", "EOT", "ICF")
    _click_item(window, LONG_NAME, double=True)  # Kept on its own.
    grid = window.ui.tableView_stacked_items
    row = _grid_rows(window).index(LONG_NAME)
    name = grid.first_widget(row).lineEdit()
    named = (name.cursorPosition(), name.selectedText())
    QApplication.processEvents()  # The boxes take their widths.
    icf_cell, eot_cell = _cell(window, LONG_NAME, 2), _cell(window, LONG_NAME, 1)

    # The new match's name is all selected, to type over, yet shows its start.
    assert named == (0, LONG_NAME)
    assert icf_cell.lineEdit().cursorPosition() == 0
    assert grid.first_widget(row).toolTip() == (
        f"{LONG_NAME}\nPick one of the matched names, or type a new one"
    )
    assert icf_cell.toolTip() == f"{LONG_NAME}\nPick an item, or type to find one"
    assert eot_cell.toolTip() == "Pick an item, or type to find one"
