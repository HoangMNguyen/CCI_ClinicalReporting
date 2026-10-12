"""Names given to additional input files, kept with a saved setting."""

import json
import logging

import pandas as pd
import pytest

from clinical_reporting import additional_names as names
from clinical_reporting import session
from clinical_reporting.additional_names import (
    BY_COLUMNS,
    BY_FILE_NAME,
    SETTINGS_KEY,
    Match,
    SavedFileNames,
)
from clinical_reporting.data import build_additional_data_map
from clinical_reporting.report import CLReport
from clinical_reporting.settings_store import LocalFolderStore

LAB = pd.DataFrame(
    {"Subject ID": ["001"], "Visit Dt": ["2026-01-02"], "ALT": [30], "Unnamed: 3": [0]}
)
PK = pd.DataFrame({"Subject ID": ["001"], "Nominal Time": [1], "Conc": [2.5]})


def _entry(file_name, columns=(), form_name="", column_names=None):
    return SavedFileNames(file_name, tuple(columns), form_name, column_names or {})


# --------------------------------------------------------------------------
# Saving


def test_saved_entries_name_files_without_their_folders(tmp_path):
    lab = str(tmp_path / "exports" / "lab_results.csv")
    inputs = {lab: LAB, str(tmp_path / "notes.csv"): PK}
    form_names = {lab: "LAB"}
    column_names = {(lab, "Visit Dt"): "Visit Date", (lab, "Subject ID"): "Subject"}

    entries = names.to_settings(inputs, form_names, column_names)

    assert entries == [
        {
            "file_name": "lab_results.csv",
            "columns": ["Subject ID", "Visit Dt", "ALT"],
            "form_name": "LAB",
            # In the file's column order.
            "column_names": {"Subject ID": "Subject", "Visit Dt": "Visit Date"},
        }
    ]
    assert str(tmp_path) not in json.dumps(entries)


def test_only_files_with_names_are_saved_sorted_by_file_name():
    inputs = {"C:/b/zeta.csv": PK, "C:/a/Alpha.csv": LAB, "C:/c/plain.csv": PK}
    column_names = {("C:/b/zeta.csv", "Conc"): "CONC", ("C:/c/plain.csv", "Conc"): ""}

    entries = names.to_settings(inputs, {"C:/a/Alpha.csv": " LAB "}, column_names)

    assert [entry["file_name"] for entry in entries] == ["Alpha.csv", "zeta.csv"]
    assert entries[0]["form_name"] == "LAB"
    assert entries[1] == {
        "file_name": "zeta.csv",
        "columns": ["Subject ID", "Nominal Time", "Conc"],
        "form_name": "",
        "column_names": {"Conc": "CONC"},
    }


def test_a_setting_without_names_is_saved_as_before():
    report = CLReport()
    before = report.settings_to_dict("monthly")

    settings = names.add_to_settings(dict(before), {"C:/x.csv": PK}, {}, {})

    assert settings == before
    assert SETTINGS_KEY not in settings


def test_names_are_added_to_the_settings():
    settings = names.add_to_settings(
        {"setting_name": "monthly"}, {"C:/a/lab.csv": LAB}, {"C:/a/lab.csv": "LAB"}, {}
    )

    assert settings["setting_name"] == "monthly"
    assert settings[SETTINGS_KEY][0]["form_name"] == "LAB"


# --------------------------------------------------------------------------
# Loading


def test_entries_round_trip():
    lab = "C:/a/lab_results.csv"
    settings = names.add_to_settings(
        {}, {lab: LAB}, {lab: "LAB"}, {(lab, "ALT"): "ALT_UL"}
    )

    assert names.from_settings(settings) == [
        _entry(
            "lab_results.csv",
            ["Subject ID", "Visit Dt", "ALT"],
            "LAB",
            {"ALT": "ALT_UL"},
        )
    ]


def test_settings_from_before_the_key_have_no_entries():
    assert names.from_settings(CLReport().settings_to_dict("old")) == []
    assert names.from_settings(None) == []


@pytest.mark.parametrize(
    "value",
    [
        "lab.csv",
        42,
        {"file_name": "lab.csv"},
    ],
)
def test_a_key_that_is_not_a_list_is_ignored(value, caplog):
    with caplog.at_level(logging.WARNING):
        assert names.from_settings({SETTINGS_KEY: value}) == []
    assert "not a list" in caplog.text


def test_unusable_entries_are_skipped_and_the_rest_kept(caplog):
    good = {"file_name": "lab.csv", "form_name": "LAB"}
    junk = [
        "lab.csv",
        None,
        {"form_name": "NOFILE"},
        {"file_name": "", "form_name": "BLANK"},
        {"file_name": 7, "form_name": "NUMBER"},
        {"file_name": "nothing.csv"},
        {"file_name": "blank.csv", "form_name": "  ", "column_names": {"A": " "}},
    ]

    with caplog.at_level(logging.WARNING):
        entries = names.from_settings({SETTINGS_KEY: [*junk, good]})

    assert entries == [_entry("lab.csv", form_name="LAB")]
    assert caplog.text.count("Skipping saved") == len(junk)


def test_damaged_fields_inside_an_entry_are_tolerated():
    entries = names.from_settings(
        {
            SETTINGS_KEY: [
                {
                    "file_name": "C:\\Users\\analyst\\pk.xlsx",
                    "columns": ["Conc", 3, None],
                    "form_name": 5,
                    "column_names": {"Conc": " CONC ", "Time": 1, 2: "X"},
                },
                {"file_name": "lab.csv", "columns": "ALT", "column_names": ["ALT"]},
                {"file_name": "ae.csv", "form_name": "AEX", "columns": None},
            ]
        }
    )

    assert entries == [
        _entry("pk.xlsx", ["Conc"], "", {"Conc": "CONC"}),
        _entry("ae.csv", (), "AEX"),
    ]


def test_a_setting_with_names_still_loads_in_the_report():
    """A version without this feature reads only the keys it knows."""
    data = {"DM": pd.DataFrame({"Subject": ["001"], "Age": [54]})}
    source = CLReport()
    source.set_data(data)
    source.add_selected_form("DM")
    plain = source.settings_to_dict("monthly")
    with_names = {**plain, SETTINGS_KEY: [{"file_name": "a.csv", "form_name": "A"}]}

    states = []
    for settings in (plain, with_names):
        report = CLReport()
        report.set_data(data)
        missing = session.apply_saved_setting(report, settings)
        states.append((missing, report.settings_to_dict("monthly")))

    assert states[0] == states[1]


def test_the_settings_folder_lists_and_keeps_a_setting_with_names(tmp_path):
    store = LocalFolderStore(tmp_path)
    settings = {"study_name": "DEMO01", "setting_name": "monthly"}
    names.add_to_settings(settings, {"C:/a/lab.csv": LAB}, {"C:/a/lab.csv": "LAB"}, {})

    key = store.save("monthly", settings)

    assert [saved.name for saved in store.list("DEMO01")] == ["monthly"]
    assert names.from_settings(store.load(key))[0].form_name == "LAB"


# --------------------------------------------------------------------------
# Matching


def test_files_match_by_file_name_from_any_folder_ignoring_case():
    saved = [_entry("lab_results.csv", ["X"], "LAB")]

    found = names.match(saved, {"D:/other/LAB_RESULTS.CSV": ["Subject ID"]})

    assert found == {"D:/other/LAB_RESULTS.CSV": Match(0, BY_FILE_NAME)}


def test_a_renamed_file_matches_by_its_columns_in_any_order():
    saved = [_entry("pk_conc.xlsx", ["Subject ID", "Conc", "Nominal Time"], "PK")]

    found = names.match(
        saved, {"C:/pk_2026-10.xlsx": ["Conc", "Nominal Time", "Subject ID"]}
    )

    assert found == {"C:/pk_2026-10.xlsx": Match(0, BY_COLUMNS)}


def test_a_file_name_match_comes_before_a_column_match():
    columns = ["Subject ID", "Conc"]
    saved = [_entry("old.csv", columns, "OLD"), _entry("new.csv", columns, "NEW")]

    found = names.match(saved, {"C:/new.csv": columns})

    assert found == {"C:/new.csv": Match(1, BY_FILE_NAME)}


def test_each_entry_pairs_with_one_file_at_most():
    columns = ["Subject ID", "Conc"]
    saved = [_entry("pk.csv", columns, "PK")]

    found = names.match(saved, {"C:/pk.csv": columns, "C:/pk_copy.csv": columns})

    assert found == {"C:/pk.csv": Match(0, BY_FILE_NAME)}


def test_ambiguous_names_or_columns_match_nothing():
    columns = ["Subject ID", "Conc"]
    two_files = names.match(
        [_entry("pk.csv", columns, "PK")],
        {"C:/a/pk.csv": columns, "C:/b/pk.csv": columns},
    )
    two_entries = names.match(
        [_entry("a.csv", columns, "A"), _entry("b.csv", columns, "B")],
        {"C:/c.csv": columns},
    )

    assert two_files == {}
    assert two_entries == {}


def test_files_with_the_same_name_can_still_match_by_columns():
    saved = [_entry("pk.csv", ["Conc"], "PK"), _entry("other.csv", ["Dose"], "DOSE")]

    found = names.match(saved, {"C:/a/pk.csv": ["Conc"], "C:/b/pk.csv": ["Dose"]})

    assert found == {
        "C:/a/pk.csv": Match(0, BY_COLUMNS),
        "C:/b/pk.csv": Match(1, BY_COLUMNS),
    }


def test_files_without_headers_never_match_by_columns():
    saved = [_entry("saved.csv", (), "S")]

    assert names.match(saved, {"C:/empty.csv": []}) == {}


def test_taken_files_and_entries_are_left_out():
    columns = ["Subject ID", "Conc"]
    saved = [_entry("pk.csv", columns, "PK"), _entry("lab.csv", ["ALT"], "LAB")]
    files = {"C:/pk.csv": columns, "C:/pk_copy.csv": columns, "C:/lab.csv": ["ALT"]}

    found = names.match(saved, files, taken={"C:/pk_copy.csv": 0})

    assert found == {"C:/lab.csv": Match(1, BY_FILE_NAME)}


# --------------------------------------------------------------------------
# Applying an entry


def test_an_entry_gives_only_the_columns_the_file_has():
    entry = _entry(
        "lab.csv",
        form_name="LAB",
        column_names={"Subject ID": "Subject", "Visit Dt": "Visit Date", "AST": "AST"},
    )

    given = names.names_from(entry, ["Subject ID", "ALT"])

    assert given.form_name == "LAB"
    assert given.column_names == {"Subject ID": "Subject"}


def test_names_a_file_cant_use_are_ignored_unless_it_has_their_column():
    entry = _entry(
        "lab.csv",
        form_name="LAB",
        column_names={"Subject ID": "Subject", "Visit Dt": "Visit Date", "AST": "AST"},
    )
    path = "C:/exports/2026-10/lab.csv"
    columns = ["Subject ID", "Visit Date (dd)", "AST"]

    as_picked = names.ignored_names(entry, path, columns, {"Subject ID": "Subject"})
    fixed = names.ignored_names(entry, path, columns, {"Visit Date (dd)": "Visit Date"})
    already = names.ignored_names(entry, path, ["Subject ID", "Visit Date"], {})

    assert as_picked == [names.IgnoredName("lab.csv", "Visit Dt", "Visit Date")]
    assert fixed == []
    assert already == [names.IgnoredName("lab.csv", "AST", "AST")]


def test_current_names_are_one_files_form_and_column_names():
    current = names.current_names(
        "C:/a.csv",
        {"C:/a.csv": " A ", "C:/b.csv": "B"},
        {("C:/a.csv", "X"): "Y", ("C:/a.csv", "Z"): "", ("C:/b.csv", "X"): "W"},
    )

    assert current == ("A", {"X": "Y"})


def test_saved_names_rebuild_the_forms_a_setting_needs(tmp_path):
    """Save in one run, then reuse the names for a file from another folder."""
    lab = str(tmp_path / "first" / "lab_results.csv")
    data = {"DM": pd.DataFrame({"Subject": ["001"], "Age": [54]})}
    form_names = {lab: "LAB"}
    column_names = {(lab, "Subject ID"): "Subject", (lab, "Visit Dt"): "Visit Date"}
    first = CLReport()
    first.set_data(
        {**data, **build_additional_data_map({lab: LAB}, form_names, column_names)}
    )
    first.add_selected_form("LAB")
    first.selected_forms["LAB"].set_form_item_state("Visit Date", selected=True)
    store = LocalFolderStore(tmp_path / "settings")
    key = store.save(
        "monthly",
        names.add_to_settings(
            first.settings_to_dict("monthly"), {lab: LAB}, form_names, column_names
        ),
    )

    stored = store.load(key)
    again = str(tmp_path / "second" / "LAB_RESULTS.csv")
    saved = names.from_settings(stored)
    found = names.match(saved, {again: list(LAB.columns)})
    given = names.names_from(saved[found[again].index], list(LAB.columns))
    rebuilt = build_additional_data_map(
        {again: LAB},
        {again: given.form_name},
        {(again, column): new for column, new in given.column_names.items()},
    )
    report = CLReport()
    report.set_data({**data, **rebuilt})
    missing = session.apply_saved_setting(report, stored)

    assert missing == {"forms": [], "items": []}
    assert report.selected_forms["LAB"].get_selected_form_items() == ["Visit Date"]
