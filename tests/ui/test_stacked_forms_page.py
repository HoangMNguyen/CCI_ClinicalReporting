"""The Stacked forms page, on the DEMO01 sample report.

The sample's EOT (Reason) and DS (Status) forms share Subject, Site and
Visit, so stacking them leaves Reason and Status out until they are matched,
here as "Disposition". The page keeps its own stacked forms until "Apply to
report"; badges refresh once control returns to the event loop.
"""

import json

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QListWidget

from cci_ui.widgets.sidebar import StepState
from clinical_reporting.stacking import Match, StackedForm
from clinical_reporting.ui.pages.stacked_forms import FIRST_COLUMN_W, TICK_ROLE
from clinical_reporting.ui.sample_data import STUDY, sample_forms

NOT_APPLIED = "Not applied yet. Apply to report to use your changes."
DISP = StackedForm(
    "DISP", ("EOT", "DS"), (Match("Disposition", {"EOT": "Reason", "DS": "Status"}),)
)


def _open(window):
    window.ui.shell.set_current("stacked")
    QApplication.processEvents()


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
    """Apply one additional file per form: Subject, Site, Visit and its *columns*.

    Each form gets one column name or a tuple of them.
    """
    rows = {"Subject": ["01-100"], "Site": ["01"], "Visit": ["Screening"]}
    paths = {form: str(tmp_path / f"{form.lower()}.csv") for form in columns}
    files = {}
    for form, names in columns.items():
        names = (names,) if isinstance(names, str) else names
        files[paths[form]] = pd.DataFrame({**rows, **{name: ["x"] for name in names}})
    window.additional_inputs = files
    window.additional_form_names = {paths[form]: form for form in columns}
    window.click_apply_additional_forms()


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
    assert matched == ["In every member", "Matched", "Reason", "Left out", "Nothing left out."]
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

    assert refused == (False, "Pick at most one item from each member: DM has both Age and Sex.")
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
    state = window.ui.banner_stacked_state.text()
    _pick(_cell(window, "Reason", 1), "—")
    cleared = (_cell(window, "Reason", 1).currentText(), _grid_rows(window)[-2:])
    _pick(_cell(window, "Reason", 2), "—")

    assert listed == (["—", "Reason"], "Reason", ["—", "Other items", "Status"], "—")
    assert not heading.isEnabled()
    assert picked == ("Status", "Nothing left out.")
    assert state == NOT_APPLIED
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
    window.click_apply_stacked_forms()
    _add_files(window, tmp_path, OUT="Result")  # The next file renamed Outcome.
    box = _cell(window, "Reason", 2)
    warned = (box.currentText(), box.toolTip(), box.itemIcon(0).isNull())

    _pick(box, "Result")
    fixed = _cell(window, "Reason", 2)

    assert warned == ("—", "OUT has no Outcome", False)
    assert (fixed.currentText(), fixed.toolTip()) == ("Result", "")
    assert window.ui.banner_stacked_state.text() == NOT_APPLIED


def test_a_member_with_two_items_of_a_match_is_fixed_by_clearing_its_cell(
    sample_window, tmp_path
):
    window = sample_window
    _add_files(window, tmp_path, OUT="Outcome")
    _new_stacked_form(window, "ENDS", "EOT", "OUT")
    _click_item(window, "Reason")
    _click_item(window, "Outcome", Qt.KeyboardModifier.ControlModifier)
    window.click_match_stacked_items()
    window.click_apply_stacked_forms()
    _add_files(window, tmp_path, OUT=("Outcome", "Reason"))  # OUT now has both.
    box = _cell(window, "Reason", 2)
    warned = (box.currentText(), box.toolTip())

    _pick(box, "Outcome")  # Picking the item it shows again confirms nothing.
    again = window.ui.banner_stacked_state.text()
    _pick(_cell(window, "Reason", 2), "—")
    cleared = _cell(window, "Reason", 2).currentText()
    window.click_apply_stacked_forms()

    assert warned == ("Outcome", "OUT now has Reason and Outcome: which one is unclear")
    assert again == (
        "ENDS: OUT now has both Reason and Outcome, which the match Reason lines up. "
        "Unmatch it and match again on Stacked forms. The report can't be exported "
        "until this is fixed."
    )
    assert again.kind == "error"
    # "—" takes Outcome out of the match, so OUT gives its Reason.
    assert cleared == "Reason"
    assert window.report.validate() == []


def test_apply_refuses_problems_and_lists_them(sample_window):
    window = sample_window
    _open(window)
    window.click_new_stacked_form()
    _tick(window, 0, "EOT")

    window.click_apply_stacked_forms()
    banner = window.ui.banner_stacked

    assert banner.text() == "Not applied. Fix these 2 problems first, then apply again."
    assert banner.kind() == "error"
    assert banner.details() == (
        "New stacked form: Give it a name.\nNew stacked form: Pick at least two members."
    )
    assert window.report.stacked_forms == []
    assert window.ui.banner_stacked_state.text() == NOT_APPLIED


def test_apply_adds_the_stacked_form_and_keeps_the_selections(sample_window):
    window = sample_window
    _match_disposition(window)
    state = window.ui.banner_stacked_state.text()
    badge = _badge(window)

    window.click_apply_stacked_forms()
    QApplication.processEvents()
    forms = window.ui.listWidget_form_available
    (disp,) = forms.findItems("DISP", Qt.MatchFlag.MatchExactly)

    assert state == NOT_APPLIED and badge == (StepState.OPTIONAL, None)
    assert window.report.stacked_forms == [DISP]
    assert list(window.report.data["DISP"].columns) == [
        "Subject",
        "Site",
        "Visit",
        "Disposition",
    ]
    assert len(window.report.data["DISP"]) == 48
    assert sorted(window.report.get_selected_forms_list()) == ["AE", "DM", "VS"]
    assert window.ui.banner_stacked.text() == (
        "Applied. Stacked forms: DISP (48 rows from EOT, DS)."
    )
    assert window.ui.banner_stacked_state.text() == ""
    assert _badge(window) == (StepState.DONE, None)
    assert disp.toolTip() == "Stacked from EOT, DS"


def test_unapplied_changes_say_so_and_leave_the_badge(sample_window):
    window = sample_window
    _match_disposition(window)
    window.click_apply_stacked_forms()

    _type_name(window, 0, "DISPOSITIONS")

    assert window.ui.banner_stacked_state.text() == NOT_APPLIED
    assert window.report.stacked_forms == [DISP]
    assert _badge(window) == (StepState.DONE, None)


def test_a_new_zip_keeps_the_stacked_forms_and_asks_for_apply_again(sample_window):
    window = sample_window
    _match_disposition(window)
    window.click_apply_stacked_forms()

    window.open_input_data("Core_Listings_DEMO02_sample.zip", None, sample_forms())
    asked = window.ui.banner_stacked_state.text()
    listed = window.ui.tableWidget_stacked_forms.cellWidget(0, 0).text()
    dropped = list(window.report.stacked_forms)
    window.click_apply_stacked_forms()

    assert asked == (
        "The new Corelisting ZIP started a new report. Apply the stacked forms "
        "again to add them to it."
    )
    assert listed == "DISP" and dropped == []
    assert window.report.stacked_forms == [DISP]
    assert "DISP" in window.report.data
    assert window.ui.banner_stacked_state.text() == ""


def test_loading_a_setting_brings_its_stacked_forms_to_the_page(
    sample_window, tmp_path
):
    window = sample_window
    _match_disposition(window)
    window.click_apply_stacked_forms()
    window.settings_directory = str(tmp_path)
    window.ui.checkBox_save_current_setting.setChecked(True)
    window.ui.lineEdit_setting_name.setText("DSMB monthly")
    window.click_save_setting()
    window.ui.tableWidget_stacked_forms.selectRow(0)
    window.click_remove_stacked_form()
    window.click_apply_stacked_forms()
    _new_stacked_form(window, "OTHER", "CM", "EX")
    before = window.ui.tableWidget_stacked_forms.rowCount()

    window.ui.checkBox_saved_setting.setChecked(True)
    combo = window.ui.comboBox_saved_setting
    combo.setCurrentIndex(combo.findText("DSMB monthly"))
    table = window.ui.tableWidget_stacked_forms

    assert before == 1
    assert window.report.stacked_forms == [DISP]
    assert table.rowCount() == 1
    assert table.cellWidget(0, 0).text() == "DISP"
    assert table.cellWidget(0, 1).currentText() == "EOT, DS"
    assert window.ui.banner_stacked_state.text() == ""


def test_additional_input_refuses_a_file_named_like_a_stacked_form(sample_window):
    window = sample_window
    _match_disposition(window)
    window.click_apply_stacked_forms()
    window.additional_inputs = {"lab.csv": pd.DataFrame({"Subject": ["01-100"]})}
    window.additional_form_names = {"lab.csv": "DISP"}

    window.click_apply_additional_forms()
    banner = window.ui.banner_additional

    assert banner.text() == (
        "These form names can't be used: DISP. Rename them in the table and try again."
    )
    assert "Conflicts with existing report forms:\n  - DISP: lab.csv" in banner.details()
    assert list(window.report.data["DISP"].columns)[-1] == "Disposition"


def test_saving_with_unapplied_stacked_forms_says_they_werent_saved(
    sample_window, tmp_path
):
    window = sample_window
    _new_stacked_form(window, "DISP", "EOT", "DS")
    window.settings_directory = str(tmp_path)
    window.ui.checkBox_save_current_setting.setChecked(True)
    window.ui.lineEdit_setting_name.setText("DSMB monthly")

    window.click_save_setting()
    (saved,) = tmp_path.glob("*.json")
    message = window.ui.label_save_confirmation.text()

    assert message.kind == "warning"
    assert message == (
        f"Settings saved to {saved}. Stacked forms has changes that aren't applied, "
        "so they weren't saved."
    )
    assert "stacked_forms" not in json.loads(saved.read_text(encoding="utf-8"))


def test_a_setting_whose_stacked_member_is_missing_says_what_to_add(
    sample_window, tmp_path
):
    window = sample_window
    lab = str(tmp_path / "lab_results.csv")
    window.additional_inputs = {lab: pd.DataFrame({"Subject": ["01-100"], "ALT": [3]})}
    window.additional_form_names = {lab: "LAB"}
    window.click_apply_additional_forms()
    _new_stacked_form(window, "LABS", "LAB", "EOT")
    window.click_apply_stacked_forms()
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


def test_the_first_column_stays_when_the_members_scroll_sideways(sample_window):
    window = sample_window
    _new_stacked_form(
        window, "ALL", "DM", "VS", "AE", "LB", "CM", "EX", "EOT", "DS"
    )
    window.resize(960, 600)
    QApplication.processEvents()
    grid = window.ui.tableView_stacked_items
    bar = grid.horizontalScrollBar()
    first = grid.frozen
    before = (first.geometry(), first.columnViewportPosition(0))
    member_before = grid.columnViewportPosition(1)

    bar.setValue(bar.maximum())
    QApplication.processEvents()
    headers = _headers(window)
    tip = grid.model().headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole)

    assert bar.maximum() > 0 and bar.value() == bar.maximum()
    assert headers == ["Stacked item", "DM", "VS", "AE", "LB", "CM", "EX", "EOT", "DS"]
    assert tip == "DM · 24 rows"
    assert first.isVisible() and first.width() == FIRST_COLUMN_W
    assert (first.geometry(), first.columnViewportPosition(0)) == before
    # The first member column went under the first column, which stayed.
    assert member_before == FIRST_COLUMN_W
    assert grid.columnViewportPosition(1) == FIRST_COLUMN_W - bar.maximum()


def test_an_additional_file_that_now_gives_two_items_of_a_match_stops_the_export(
    sample_window, tmp_path
):
    window = sample_window
    outcomes = str(tmp_path / "outcomes.csv")
    rows = {"Subject": ["01-100"], "Site": ["01"], "Visit": ["Screening"]}
    window.additional_inputs = {outcomes: pd.DataFrame({**rows, "Outcome": ["Done"]})}
    window.additional_form_names = {outcomes: "OUT"}
    window.click_apply_additional_forms()
    _new_stacked_form(window, "ENDS", "EOT", "OUT")
    _click_item(window, "Reason")
    _click_item(window, "Outcome", Qt.KeyboardModifier.ControlModifier)
    window.click_match_stacked_items()
    window.click_apply_stacked_forms()
    before = _badge(window)

    # The next file also has a Reason column: OUT now gives the match two items.
    window.additional_inputs = {
        outcomes: pd.DataFrame({**rows, "Outcome": ["Done"], "Reason": ["Done"]})
    }
    window.click_apply_additional_forms()
    state = window.ui.banner_stacked_state.text()

    message = (
        "ENDS: OUT now has both Reason and Outcome, which the match Reason lines up. "
        "Unmatch it and match again on Stacked forms."
    )
    assert before == (StepState.DONE, None)
    assert state == f"{message} The report can't be exported until this is fixed."
    assert state.kind == "error"
    assert _badge(window) == (StepState.ERROR, None)
    assert [issue.message for issue in window.report.validate()] == [message]
