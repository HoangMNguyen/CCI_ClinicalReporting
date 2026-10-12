import types

import pandas as pd
from PySide6.QtCore import QItemSelectionModel, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QListWidget,
    QPushButton,
    QTableWidget,
)
from tests.unit.fakes import FakeBanner

from clinical_reporting import data, steps
from clinical_reporting.additional_names import Match, SavedFileNames
from clinical_reporting.report import CLReport
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.pages import additional_input as additional_input_module
from clinical_reporting.ui.pages._common import CellComboBox
from clinical_reporting.ui.pages.additional_input import (
    SAVED_NAMES_COLUMN,
    AdditionalInputMixin,
)


class DummyWidget(AdditionalInputMixin, WidgetBaseMixin):
    """Lightweight stand-in to exercise the mixin logic without Qt."""

    def __init__(self):
        # Initialize mixin state expected by the helpers.
        self.additional_inputs = {}
        self.additional_form_names = {}
        self.additional_column_names = {}
        self._additional_form_keys = set()
        self.report = CLReport()
        self.ui = types.SimpleNamespace(banner_additional=FakeBanner())
        self.update_all_ui_calls = 0

    def update_all_ui(self):
        self.update_all_ui_calls += 1


# The Qt stand-ins below live for the whole session. One left to the garbage
# collector between tests gets destroyed at an unpredictable point, often in a
# later window test's event processing, which crashes in QObject::~QObject.
_ALIVE = []


class DummyAdditionalInputUiWidget(AdditionalInputMixin, WidgetBaseMixin):
    """Qt-backed stand-in for additional-input table interactions."""

    def __init__(self):
        _ALIVE.append(self)
        self.report = CLReport()
        column_table = QTableWidget()
        column_table.setColumnCount(2)
        form_table = QTableWidget()
        form_table.setColumnCount(2)
        self.ui = types.SimpleNamespace(
            pushButton_additional_file_add=QPushButton(),
            pushButton_additional_file_remove=QPushButton(),
            pushButton_apply_additional_files=QPushButton(),
            listWidget_additional_file=QListWidget(),
            tableWidget_update_form_name=form_table,
            tableWidget_update_column_name=column_table,
            banner_additional=FakeBanner(),
        )
        self._init_additional_input()


def test_context_action_copies_selected_new_columns_to_updated_names(qapp):
    widget = DummyAdditionalInputUiWidget()
    file_path = "C:/tmp/lab.csv"
    widget.additional_inputs[file_path] = pd.DataFrame(
        {"Subject": ["001"], "Result": [1.0], "Unit": ["mg"]}
    )
    widget._refresh_additional_files_ui()
    widget._refresh_additional_tables()
    table = widget.ui.tableWidget_update_column_name

    selection_model = table.selectionModel()
    for row in (0, 2):
        selection_model.select(
            table.model().index(row, 0),
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )

    widget.copy_new_column_name_action.trigger()

    assert table.item(0, 1).text() == "Subject"
    assert table.item(1, 1).text() == ""
    assert table.item(2, 1).text() == "Unit"
    assert widget.additional_column_names == {
        (file_path, "Subject"): "Subject",
        (file_path, "Unit"): "Unit",
    }


def test_apply_additional_inputs_preserves_available_selections_only():
    widget = DummyWidget()

    # Base report with one form and selections.
    base_df = pd.DataFrame({"Subject": ["S1", "S2"], "A1": [1, 2]})
    widget.report.set_data({"FormA": base_df})
    widget.report.add_selected_form("FormA")
    widget.report.selected_forms["FormA"].set_form_item_state("A1", selected=True)
    widget.report.set_common_item_state("A1", selected=True)
    widget.report.set_common_item_state("Subject", selected=True)

    # Additional form without A1 so common items will shrink to Subject only.
    add_path = "/tmp/formB.csv"
    widget.additional_inputs[add_path] = pd.DataFrame(
        {"Subject": ["S1", "S2"], "B1": [10, 20]}
    )
    widget.additional_form_names[add_path] = "FormB"

    widget.click_apply_additional_forms()

    # Form selection preserved when still available.
    assert "FormA" in widget.report.selected_forms
    # Form item selection preserved for existing items.
    assert "A1" in widget.report.selected_forms["FormA"].get_selected_form_items()
    # Common items re-identified; A1 no longer common, Subject remains selected.
    assert "Subject" in widget.report.get_selected_common_items()
    assert "A1" not in widget.report.get_selected_common_items()
    # New form should now be available after add.
    assert "FormB" in widget.report.available_forms
    # UI refresh was invoked.
    assert widget.update_all_ui_calls == 1


def _build_two_form_widget():
    """Widget with two selected forms (DM, AE) sharing a Subject common item."""
    widget = DummyWidget()
    widget.report.set_data(
        {
            "DM": pd.DataFrame({"Subject": ["001", "002"], "Age": [30, 40]}),
            "AE": pd.DataFrame({"Subject": ["001", "002"], "Event": ["x", "y"]}),
        }
    )
    widget.report.add_selected_form("DM")
    widget.report.add_selected_form("AE")
    widget.report.set_common_item_state("Subject", selected=True)
    return widget


def test_apply_additional_inputs_preserves_join_configuration():
    widget = _build_two_form_widget()
    # Configure a non-default join order/items/strategy on the existing forms.
    widget.report.update_join_items("DM", [], 1, "Left join")
    widget.report.update_join_items("AE", ["Subject"], 2, "Inner join")

    # Add an additional form that still shares Subject (so it stays common).
    add_path = "/tmp/lab.csv"
    widget.additional_inputs[add_path] = pd.DataFrame(
        {"Subject": ["001", "002"], "Result": [1.0, 2.0]}
    )
    widget.additional_form_names[add_path] = "LAB"

    widget.click_apply_additional_forms()

    # The previously configured join order/items/strategy survive the merge.
    ae = widget.report.selected_forms["AE"]
    assert ae.get_join_order() == 2
    assert ae.get_join_items() == ["Subject"]
    assert ae.get_join_how() == "Inner join"
    assert widget.report.selected_forms["DM"].get_join_order() == 1
    # The new form is merged into the data and available for selection.
    assert "LAB" in widget.report.data
    assert "LAB" in widget.report.available_forms


def test_apply_additional_inputs_drops_stale_join_item():
    widget = _build_two_form_widget()
    widget.report.update_join_items("AE", ["Subject"], 2, "Inner join")

    # This additional form shares no column, so Subject is no longer common.
    add_path = "/tmp/other.csv"
    widget.additional_inputs[add_path] = pd.DataFrame(
        {"Key": ["a", "b"], "Result": [1.0, 2.0]}
    )
    widget.additional_form_names[add_path] = "OTHER"

    widget.click_apply_additional_forms()

    ae = widget.report.selected_forms["AE"]
    # Order/strategy are retained, but the now-invalid join item is dropped.
    assert ae.get_join_order() == 2
    assert ae.get_join_items() == []


def test_renaming_additional_form_replaces_old_entry():
    widget = DummyWidget()
    file_path = "/tmp/RSC.csv"
    widget.additional_inputs[file_path] = pd.DataFrame({"Subject": ["S1"], "A": [1]})

    # Initial apply with explicit form name to avoid dotted default
    widget.additional_form_names[file_path] = "RSC"
    widget.click_apply_additional_forms()
    assert "RSC" in widget.report.get_available_forms_list()

    # Rename to RSC_clean and re-apply; the old name should be removed
    widget.additional_form_names[file_path] = "RSC_clean"
    widget.click_apply_additional_forms()

    forms = widget.report.get_available_forms_list()
    assert "RSC_clean" in forms
    assert "RSC" not in forms
    assert set(widget.report.data.keys()) == {"RSC_clean"}


def test_warn_on_additional_form_conflicts_detects_duplicates():
    widget = DummyWidget()
    widget.additional_inputs["/tmp/a.csv"] = pd.DataFrame({"Subject": ["S1"]})
    widget.additional_inputs["/tmp/b.csv"] = pd.DataFrame({"Subject": ["S2"]})
    widget.additional_form_names["/tmp/a.csv"] = "DupForm"
    widget.additional_form_names["/tmp/b.csv"] = "DupForm"

    assert widget._warn_on_additional_form_conflicts(set()) is True
    shown = widget.ui.banner_additional.value
    assert "DupForm" in shown and shown.kind == "warning"


def test_warn_on_additional_form_conflicts_detects_dots():
    widget = DummyWidget()
    widget.additional_inputs["/tmp/a.csv"] = pd.DataFrame({"Subject": ["S1"]})
    widget.additional_form_names["/tmp/a.csv"] = "Form.With.Dot"

    assert widget._warn_on_additional_form_conflicts(set()) is True
    assert "Form.With.Dot" in widget.ui.banner_additional.value


def test_applying_names_that_repeat_or_hold_a_dot_says_why_in_full():
    widget = DummyWidget()
    for path, name in {"/x/a.csv": "LAB", "/x/b.csv": "LAB", "/x/c.csv": "A.B"}.items():
        widget.additional_inputs[path] = pd.DataFrame({"Subject": ["S1"]})
        widget.additional_form_names[path] = name

    widget.click_apply_additional_forms()

    shown = widget.ui.banner_additional.value
    assert shown == (
        "These form names can't be used: A.B, LAB. Rename them in the table and "
        "try again."
    )
    assert shown.details == (
        "Cannot add forms because some form names are invalid or conflict with "
        "existing data.\n"
        "Form names cannot include '.':\n"
        "  - A.B\n"
        "Duplicate names in additional forms:\n"
        "  - LAB: a.csv, b.csv"
    )
    assert widget.report.loaded_data == {}


def test_apply_additional_inputs_aborts_on_form_name_conflict():
    widget = DummyWidget()
    base_df = pd.DataFrame({"Subject": ["S1"], "A1": [1]})
    widget.report.set_data({"FormA": base_df})

    add_path = "/tmp/formA.csv"
    widget.additional_inputs[add_path] = pd.DataFrame({"Subject": ["S1"], "B1": [2]})
    widget.additional_form_names[add_path] = "FormA"

    widget.click_apply_additional_forms()

    assert set(widget.report.data.keys()) == {"FormA"}
    assert widget.report.data["FormA"].equals(base_df)
    assert widget.update_all_ui_calls == 0
    shown = widget.ui.banner_additional.value
    assert shown.startswith("These form names can't be used: FormA.")
    assert "Conflicts with existing report forms" in shown.details


def test_applying_says_what_it_added_and_nothing_without_files():
    widget = DummyWidget()
    widget.click_apply_additional_forms()
    nothing = widget.ui.banner_additional.value
    widget.additional_inputs["/tmp/lab.csv"] = pd.DataFrame({"Subject": ["S1"]})
    widget.additional_form_names["/tmp/lab.csv"] = "LB"

    widget.click_apply_additional_forms()
    applied = widget.ui.banner_additional.value
    widget.additional_inputs.clear()
    widget.click_apply_additional_forms()

    assert nothing == "Add at least one file first." and nothing.kind == "warning"
    assert applied == "1 file applied. New forms: LB." and applied.kind == "success"
    assert widget.ui.banner_additional.value.startswith("The additional forms were")
    assert widget.update_all_ui_calls == 2


def test_a_new_zip_asks_for_the_applied_files_again():
    widget = DummyWidget()
    widget._forget_applied_additional_forms()  # Nothing applied: nothing to say.
    quiet = widget.ui.banner_additional.value
    widget._additional_form_keys = {"LB"}

    widget._forget_applied_additional_forms()

    assert quiet == "" and widget._additional_form_keys == set()
    shown = widget.ui.banner_additional.value
    assert shown.kind == "info" and "Apply the files again" in shown


def test_files_that_cannot_be_read_are_reported_and_the_rest_added(
    qapp, monkeypatch, tmp_path
):
    widget = DummyAdditionalInputUiWidget()
    good, bad = tmp_path / "labs.csv", tmp_path / "broken.csv"

    def load(path):
        if path.endswith("broken.csv"):
            raise ValueError("Error tokenizing data")
        return pd.DataFrame({"Subject": ["001"]})

    monkeypatch.setattr(
        additional_input_module.QFileDialog,
        "getOpenFileNames",
        lambda *_args: ([str(good), str(bad)], ""),
    )
    monkeypatch.setattr(data, "load_tabular_file", load)

    widget.click_add_additional_files()

    assert list(widget.additional_inputs) == [str(good.resolve())]
    assert widget.ui.listWidget_additional_file.count() == 1
    shown = widget.ui.banner_additional.value
    assert shown == "These files could not be read and were not added: broken.csv."
    assert shown.kind == "warning"
    assert "broken.csv: Error tokenizing data" in shown.details


def test_a_later_add_that_reads_everything_clears_the_warning(qapp):
    widget = DummyAdditionalInputUiWidget()
    widget._add_loaded_additional_files(({}, {"bad.csv": "Error tokenizing data"}))
    warned = widget.ui.banner_additional.value
    widget._add_loaded_additional_files(({"good.csv": pd.DataFrame()}, {}))

    assert warned.startswith("These files could not be read")
    assert widget.ui.banner_additional.value == ""


def test_a_later_add_keeps_other_messages(qapp):
    widget = DummyAdditionalInputUiWidget()
    widget.ui.banner_additional.setText(steps.APPLY_ADDITIONAL_AGAIN)

    widget._add_loaded_additional_files(({"good.csv": pd.DataFrame()}, {}))

    assert widget.ui.banner_additional.value == steps.APPLY_ADDITIONAL_AGAIN


def test_a_later_add_clears_the_nothing_to_apply_warning(qapp):
    widget = DummyAdditionalInputUiWidget()
    widget.click_apply_additional_forms()
    warned = widget.ui.banner_additional.value

    widget._add_loaded_additional_files(({"good.csv": pd.DataFrame()}, {}))

    assert warned == steps.ADD_FILES_FIRST
    assert widget.ui.banner_additional.value == ""


# --------------------------------------------------------------------------
# Saved names from a loaded setting

LAB_PATH = "C:/exports/lab_results.csv"
PK_PATH = "C:/exports/pk_2026-10.xlsx"
NOTES_PATH = "C:/exports/notes.csv"
SAVED_NAMES = [
    SavedFileNames(
        "lab_results.csv",
        ("Subject ID", "Visit Dt", "ALT"),
        "LAB",
        {"Subject ID": "Subject", "Visit Dt": "Visit Date"},
    ),
    SavedFileNames(
        "pk_conc.xlsx",
        ("Subject ID", "Nominal Time", "Conc"),
        "PK",
        {"Subject ID": "Subject", "Conc": "CONC"},
    ),
]


def _frame(*columns):
    return pd.DataFrame({column: [1] for column in columns})


FRAMES = {
    LAB_PATH: _frame("Subject ID", "Visit Dt", "ALT"),
    PK_PATH: _frame("Conc", "Subject ID", "Nominal Time"),
    NOTES_PATH: _frame("Subject ID", "Note Date"),
}


class SavedNamesUiWidget(DummyAdditionalInputUiWidget):
    """The Qt stand-in with the page's three-column Form names table."""

    def __init__(self):
        super().__init__()
        self.ui.tableWidget_update_form_name.setColumnCount(3)
        self.ui.banner_saved_names = FakeBanner()
        self.ui.banner_ignored_names = FakeBanner()

    def update_all_ui(self):
        pass  # Applying refreshes the other pages, which aren't here.

    def add(self, *paths, frames=None):
        frames = frames or FRAMES
        self._add_loaded_additional_files(({path: frames[path] for path in paths}, {}))

    def combo(self, file_path):
        table = self.ui.tableWidget_update_form_name
        return table.cellWidget(self._form_table_row(file_path), SAVED_NAMES_COLUMN)

    def pick(self, file_path, combo_index):
        combo = self.combo(file_path)
        combo.setCurrentIndex(combo_index)
        combo.activated.emit(combo_index)

    def column_rows(self):
        table = self.ui.tableWidget_update_column_name
        return [
            (table.item(row, 0).text(), table.item(row, 1).text())
            for row in range(table.rowCount())
        ]


def test_loading_saved_names_picks_them_for_matching_files(qapp):
    widget = SavedNamesUiWidget()
    widget.add(LAB_PATH, NOTES_PATH, PK_PATH)

    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")

    table = widget.ui.tableWidget_update_form_name
    assert widget.combo(LAB_PATH).isEnabled()
    assert widget.additional_form_names == {LAB_PATH: "LAB", PK_PATH: "PK"}
    assert widget.additional_column_names == {
        (LAB_PATH, "Subject ID"): "Subject",
        (LAB_PATH, "Visit Dt"): "Visit Date",
        (PK_PATH, "Subject ID"): "Subject",
        (PK_PATH, "Conc"): "CONC",
    }
    assert widget.combo(LAB_PATH).currentText() == "LAB"
    assert widget.combo(PK_PATH).currentText() == "PK"
    assert widget.combo(NOTES_PATH).currentText() == steps.SAVED_NAMES_NONE
    assert "file name matches" in widget.combo(LAB_PATH).toolTip()
    assert "columns match" in widget.combo(PK_PATH).toolTip()
    assert table.item(widget._form_table_row(LAB_PATH), 1).text() == "LAB"
    shown = widget.ui.banner_additional.value
    assert shown.kind == "info"
    assert shown.startswith("Saved names from “Monthly AE review” picked for 2")
    assert "lab_results.csv by its file name" in shown
    assert "pk_2026-10.xlsx by its columns" in shown


def test_names_the_user_typed_are_not_replaced(qapp):
    widget = SavedNamesUiWidget()
    widget.add(LAB_PATH)
    widget.additional_form_names[LAB_PATH] = "MYLAB"

    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")

    assert widget.additional_form_names == {LAB_PATH: "MYLAB"}
    assert widget.additional_column_names == {}
    assert widget.combo(LAB_PATH).currentIndex() == 0
    assert widget.ui.banner_additional.value == ""  # Nothing was picked.


def test_picking_none_keeps_names_the_user_typed(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH, LAB_PATH)
    widget.additional_form_names[NOTES_PATH] = "MYNOTES"
    widget.additional_column_names[(NOTES_PATH, "Note Date")] = "NDATE"
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    widget.ui.banner_additional.setText("")

    widget.pick(NOTES_PATH, 0)  # None again, on a file nothing was picked for.
    never_picked = (
        dict(widget.additional_form_names),
        widget.ui.banner_additional.value,
    )
    widget.additional_form_names[LAB_PATH] = "LAB_EDITED"  # Changed after its pick.
    widget.pick(LAB_PATH, 0)

    assert never_picked == ({NOTES_PATH: "MYNOTES", LAB_PATH: "LAB"}, "")
    assert widget.additional_column_names[(NOTES_PATH, "Note Date")] == "NDATE"
    assert widget.additional_form_names[LAB_PATH] == "LAB_EDITED"
    assert (LAB_PATH, "Visit Dt") in widget.additional_column_names
    assert LAB_PATH not in widget._saved_names_choice
    assert widget.ui.banner_additional.value == (
        "lab_results.csv no longer uses saved names. The names you changed stay."
    )


def test_picking_an_entry_fills_the_names_and_none_clears_them(qapp):
    widget = SavedNamesUiWidget()
    widget.add(LAB_PATH, NOTES_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES[1:], "Monthly AE review")

    widget.pick(NOTES_PATH, 1)
    picked = widget.ui.banner_additional.value
    filled = (dict(widget.additional_form_names), widget.column_rows())
    widget.pick(NOTES_PATH, 0)

    assert filled == (
        {NOTES_PATH: "PK"},
        [("Subject ID", "Subject"), ("Note Date", "")],
    )
    assert picked.kind == "warning"
    assert picked == (
        "Names from PK filled in for notes.csv. 1 saved column name can't be used "
        "and will be ignored: notes.csv has no Conc. Check them, then Apply to "
        "report."
    )
    assert picked.details == "notes.csv: Conc → CONC"
    assert widget.additional_form_names == {}
    assert widget.column_rows() == [("Subject ID", ""), ("Note Date", "")]
    assert widget.ui.banner_additional.value == "Saved names cleared for notes.csv."
    table = widget.ui.tableWidget_update_form_name
    assert table.item(widget._form_table_row(NOTES_PATH), 1).text() == ""


def test_a_file_added_later_gets_its_saved_names(qapp):
    widget = SavedNamesUiWidget()
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    quiet = widget.ui.banner_additional.value

    widget.add(LAB_PATH)

    assert quiet == ""
    assert widget.additional_form_names == {LAB_PATH: "LAB"}
    assert widget.combo(LAB_PATH).currentIndex() == 1
    assert widget.ui.banner_additional.value.startswith(
        "Saved names from “Monthly AE review” picked for 1 file: "
        "lab_results.csv by its file name."
    )


def test_an_entry_in_use_is_not_picked_again_for_an_added_file(qapp):
    widget = SavedNamesUiWidget()
    widget.add(PK_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    copy = "C:/elsewhere/pk_copy.xlsx"

    widget.add(copy, frames={copy: FRAMES[PK_PATH]})

    assert widget.additional_form_names == {PK_PATH: "PK"}
    assert widget.combo(copy).currentIndex() == 0


def test_dropdowns_stay_with_their_files_when_rows_move(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    widget.pick(NOTES_PATH, 2)
    first = "C:/exports/aaa.csv"

    widget.add(first, frames={first: _frame("Other")})  # The notes row moves down.

    assert widget._form_table_row(first) == 0
    assert widget.combo(first).currentIndex() == 0
    assert widget.combo(NOTES_PATH).currentIndex() == 2
    widget.pick(first, 1)
    assert widget.additional_form_names == {NOTES_PATH: "PK", first: "LAB"}


def test_picks_survive_a_refresh_and_go_with_their_file(qapp):
    widget = SavedNamesUiWidget()
    widget.add(LAB_PATH, NOTES_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")

    widget._refresh_additional_tables()
    kept = widget.combo(LAB_PATH).currentIndex()
    files = widget.ui.listWidget_additional_file
    files.item(0).setSelected(True)  # lab_results.csv
    widget.click_remove_additional_files()

    assert kept == 1
    assert LAB_PATH not in widget._saved_names_choice
    assert list(widget.additional_inputs) == [NOTES_PATH]


def test_another_setting_replaces_only_untouched_picks(qapp):
    widget = SavedNamesUiWidget()
    widget.add(LAB_PATH, PK_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    widget.additional_form_names[PK_PATH] = "PK_EDITED"  # Typed after the pick.
    weekly = [
        SavedFileNames("lab_results.csv", (), "LABS", {}),
        SavedFileNames("pk_2026-10.xlsx", (), "PKS", {}),
    ]

    widget._offer_saved_additional_names(weekly, "Weekly")

    assert widget.additional_form_names == {LAB_PATH: "LABS", PK_PATH: "PK_EDITED"}
    assert (LAB_PATH, "Subject ID") not in widget.additional_column_names
    assert widget.combo(LAB_PATH).currentText() == "LABS"
    assert widget.combo(PK_PATH).currentIndex() == 0


def test_without_saved_names_the_dropdowns_grey_out_and_the_names_stay(qapp):
    widget = SavedNamesUiWidget()
    widget.add(LAB_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")

    widget._offer_saved_additional_names([], "Old setting")
    greyed_by_load = not widget.combo(LAB_PATH).isEnabled()
    message_after_load = widget.ui.banner_additional.value
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    widget._forget_saved_additional_names()

    combo = widget.combo(LAB_PATH)
    assert greyed_by_load and not combo.isEnabled()
    assert combo.count() == 1 and combo.currentText() == steps.SAVED_NAMES_NONE
    assert combo.toolTip() == steps.SAVED_NAMES_UNAVAILABLE_TIP
    assert widget.additional_form_names == {LAB_PATH: "LAB"}
    assert widget._saved_names_choice == {}
    # The saved-names message goes with the dropdowns.
    assert message_after_load == ""
    assert widget.ui.banner_additional.value == ""


def test_the_saved_files_not_added_yet_are_listed(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    both_missing = widget.ui.banner_saved_names.value

    widget.add(LAB_PATH)
    pk_missing = widget.ui.banner_saved_names.value
    widget.pick(NOTES_PATH, 2)  # notes.csv stands in for pk_conc.xlsx
    none_missing = widget.ui.banner_saved_names.value
    widget.pick(NOTES_PATH, 0)
    missing_again = widget.ui.banner_saved_names.value
    widget._forget_saved_additional_names()

    assert both_missing == (
        "Still to add for “Monthly AE review”: lab_results.csv (LAB), "
        "pk_conc.xlsx (PK). Add them, and their saved names will be picked for "
        "you, or pick them in Saved names for files already added."
    )
    assert both_missing.kind == "warning"
    assert pk_missing.startswith(
        "Still to add for “Monthly AE review”: pk_conc.xlsx (PK)."
    )
    assert none_missing == ""
    assert missing_again == pk_missing
    assert widget.ui.banner_saved_names.value == ""


def test_only_files_for_forms_the_setting_uses_are_still_to_add(qapp):
    widget = SavedNamesUiWidget()
    column_only = SavedFileNames("extra.csv", ("A",), "", {"A": "B"})

    widget._offer_saved_additional_names(
        [*SAVED_NAMES, column_only], "Monthly AE review", used_forms={"DM", "PK"}
    )

    assert widget.ui.banner_saved_names.value.startswith(
        "Still to add for “Monthly AE review”: pk_conc.xlsx (PK). Add them"
    )


def test_a_pick_is_said_even_when_some_files_could_not_be_read(qapp):
    widget = SavedNamesUiWidget()
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")

    widget._add_loaded_additional_files(
        ({LAB_PATH: FRAMES[LAB_PATH]}, {"C:/exports/broken.csv": "Bad file"})
    )

    assert widget.ui.banner_additional.value.startswith(
        "These files could not be read and were not added: broken.csv."
    )
    assert widget.additional_form_names == {LAB_PATH: "LAB"}
    assert widget.combo(LAB_PATH).currentIndex() == 1


def test_dropdown_entries_show_form_names_and_say_their_file(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH)
    lab_copy = SavedFileNames("lab_old.csv", ("A",), "LAB", {})
    column_only = SavedFileNames("extra.csv", ("A",), "", {"A": "B"})

    widget._offer_saved_additional_names(
        [*SAVED_NAMES, lab_copy, column_only], "Monthly AE review"
    )

    combo = widget.combo(NOTES_PATH)
    assert [combo.itemText(i) for i in range(combo.count())] == [
        steps.SAVED_NAMES_NONE,
        "LAB (lab_results.csv)",
        "PK",
        "LAB (lab_old.csv)",
        "extra.csv",
    ]
    tips = [combo.itemData(i, Qt.ItemDataRole.ToolTipRole) for i in range(5)]
    assert tips == [
        None,
        "Saved for lab_results.csv",
        "Saved for pk_conc.xlsx",
        "Saved for lab_old.csv",
        "Saved for extra.csv",
    ]


def test_files_get_a_greyed_out_dropdown_without_saved_names(qapp):
    widget = SavedNamesUiWidget()

    widget.add(LAB_PATH, NOTES_PATH)

    table = widget.ui.tableWidget_update_form_name
    for path in (LAB_PATH, NOTES_PATH):
        combo = widget.combo(path)
        assert not combo.isEnabled()
        assert combo.count() == 1 and combo.currentText() == steps.SAVED_NAMES_NONE
        assert combo.toolTip() == steps.SAVED_NAMES_UNAVAILABLE_TIP
        # The cell under the dropdown can't open a text editor.
        cell = table.item(widget._form_table_row(path), SAVED_NAMES_COLUMN)
        assert not cell.flags() & Qt.ItemIsEditable


def test_names_a_file_cant_use_are_listed_until_it_can(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH, LAB_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    banner = widget.ui.banner_ignored_names
    nothing_yet = banner.value  # lab_results.csv has all its saved columns.

    widget.pick(NOTES_PATH, 2)  # PK's names, but notes.csv has no Conc.
    listed = banner.value
    columns = widget.ui.tableWidget_update_column_name
    rows = [columns.item(row, 0).text() for row in range(columns.rowCount())]
    note_date = columns.item(rows.index("Note Date"), 1)
    note_date.setText("CONC")  # Renamed by hand: nothing is lost.
    fixed = banner.value
    note_date.setText("")
    unfixed = banner.value
    widget.pick(NOTES_PATH, 0)

    assert nothing_yet == ""
    assert listed == (
        "A saved column name can't be used: notes.csv has no Conc. It's "
        "ignored; the form still applies without it."
    )
    assert listed.kind == "warning"
    assert listed.details == "notes.csv: Conc → CONC"
    assert fixed == "" and unfixed == listed
    assert banner.value == ""


def test_the_names_a_file_cant_use_go_with_the_file_or_the_setting(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    widget.pick(NOTES_PATH, 1)  # LAB's names, but notes.csv has no Visit Dt.
    listed = widget.ui.banner_ignored_names.value

    widget._forget_saved_additional_names()
    forgotten = widget.ui.banner_ignored_names.value
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    widget.pick(NOTES_PATH, 1)
    widget.ui.listWidget_additional_file.item(0).setSelected(True)
    widget.click_remove_additional_files()

    assert listed.startswith(
        "A saved column name can't be used: notes.csv has no Visit Dt."
    )
    assert forgotten == ""
    assert widget.ui.banner_ignored_names.value == ""


def test_picks_for_files_or_entries_that_are_gone_are_left_out(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")

    widget._saved_names_choice["C:/exports/gone.csv"] = Match(1)
    widget._saved_names_choice[NOTES_PATH] = Match(7)

    assert widget._ignored_saved_names() == []


def test_applying_adds_the_forms_and_says_which_names_were_ignored(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH, LAB_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    widget.pick(NOTES_PATH, 2)  # PK's names, but notes.csv has no Conc.

    widget.click_apply_additional_forms()
    applied = widget.ui.banner_additional.value
    widget.add(PK_PATH)  # A later add leaves the result.

    assert set(widget.report.data) == {"LAB", "PK"}
    assert applied.kind == "warning"
    assert applied == (
        "2 files applied. New forms: LAB, PK. Saved column names ignored: "
        "notes.csv has no Conc."
    )
    assert applied.details == "notes.csv: Conc → CONC"
    assert widget.ui.banner_additional.value == applied
    assert widget.ui.banner_ignored_names.value.startswith(
        "A saved column name can't be used: notes.csv has no Conc."
    )


def test_a_later_add_still_clears_other_warnings_after_an_apply(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    widget.pick(NOTES_PATH, 2)
    widget.click_apply_additional_forms()
    widget.ui.banner_additional.setText(steps.ADD_FILES_FIRST)
    other = "C:/exports/other.csv"

    widget.add(other, frames={other: _frame("Other")})  # Nothing to pick.

    assert widget.ui.banner_additional.value == ""


def test_copying_original_names_back_can_lose_a_saved_name_again(qapp):
    widget = SavedNamesUiWidget()
    widget.add(NOTES_PATH)
    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")
    widget.pick(NOTES_PATH, 2)  # PK's names, but notes.csv has no Conc.
    columns = widget.ui.tableWidget_update_column_name
    rows = [columns.item(row, 0).text() for row in range(columns.rowCount())]
    note_date = rows.index("Note Date")
    columns.item(note_date, 1).setText("CONC")  # Renamed by hand.
    fixed = widget.ui.banner_ignored_names.value

    columns.selectionModel().select(
        columns.model().index(note_date, 0),
        QItemSelectionModel.SelectionFlag.ClearAndSelect
        | QItemSelectionModel.SelectionFlag.Rows,
    )
    widget.copy_selected_new_column_names_to_updated()  # Back to "Note Date".

    assert fixed == ""
    assert widget.ui.banner_ignored_names.value.startswith(
        "A saved column name can't be used: notes.csv has no Conc."
    )


def test_a_two_column_form_table_still_gets_the_names(qapp):
    widget = DummyAdditionalInputUiWidget()
    widget.additional_inputs[LAB_PATH] = FRAMES[LAB_PATH]

    widget._offer_saved_additional_names(SAVED_NAMES, "Monthly AE review")

    assert widget.additional_form_names == {LAB_PATH: "LAB"}


def test_a_window_without_this_page_ignores_saved_names():
    AdditionalInputMixin._offer_saved_additional_names(
        types.SimpleNamespace(), SAVED_NAMES, "Monthly AE review"
    )

    assert DummyWidget()._pick_saved_names([LAB_PATH]) is None


def test_the_wheel_only_changes_a_focused_dropdown(qapp):
    combo = CellComboBox()
    combo.addItems(["None", "LAB", "PK"])
    wheel = QWheelEvent(
        QPointF(5, 5),
        QPointF(5, 5),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    combo.wheelEvent(wheel)

    assert combo.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert combo.currentIndex() == 0
    assert not wheel.isAccepted()
