"""Tests for the Qt-free core pieces shared by every front end."""

import io
import json
import pickle
from datetime import datetime

import pandas as pd
import pytest

from clinical_reporting import feedback
from clinical_reporting.data import load_tabular_file
from clinical_reporting.filenames import output_file_name
from clinical_reporting.report import CLReport
from clinical_reporting.session import capture_selection, restore_selection
from clinical_reporting.settings_store import LocalFolderStore, SavedSetting

# ---------------------------------------------------------------------------
# feedback


def test_message_is_a_str_with_kind_and_details():
    message = feedback.error("Error saving report: disk full", details="Traceback ...")

    assert message == "Error saving report: disk full"
    assert message.startswith("Error saving report")
    assert message.kind == "error"
    assert message.details == "Traceback ..."
    assert feedback.kind_of(message) == "error"


def test_plain_strings_count_as_info_and_unknown_kinds_are_rejected():
    assert feedback.kind_of("Generating preview...") == "info"
    assert feedback.kind_of(None) == "info"
    with pytest.raises(ValueError):
        feedback.Message("text", kind="fatal")


def test_message_survives_pickling():
    restored = pickle.loads(pickle.dumps(feedback.warning("Missing forms: AE")))

    assert restored == "Missing forms: AE"
    assert restored.kind == "warning"


# ---------------------------------------------------------------------------
# settings store


def test_local_folder_store_round_trip_and_study_filter(tmp_path):
    store = LocalFolderStore(tmp_path / "settings")

    key = store.save(
        "DSMB monthly", {"study_name": "15420", "setting_name": "DSMB monthly"}
    )
    store.save("Other study", {"study_name": "03325", "setting_name": "Other study"})

    assert key == str(tmp_path / "settings" / "DSMB monthly.json")
    assert store.list("15420") == [SavedSetting("DSMB monthly", key)]
    assert len(store.list()) == 2
    assert store.load(key)["setting_name"] == "DSMB monthly"


def test_local_folder_store_skips_unreadable_files(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "list.json").write_text("[1, 2]", encoding="utf-8")
    (tmp_path / "unnamed.json").write_text(
        json.dumps({"study_name": "15420"}), encoding="utf-8"
    )

    listed = LocalFolderStore(tmp_path).list("15420")

    assert [saved.name for saved in listed] == ["unnamed"]


def test_saved_setting_names_cannot_leave_the_folder(tmp_path):
    store = LocalFolderStore(tmp_path / "settings")

    key = store.save("../escape: v2", {"setting_name": "../escape: v2"})

    assert key == str(tmp_path / "settings" / ".._escape_ v2.json")
    assert store.list()[0].name == "../escape: v2"


def test_missing_folder_lists_nothing(tmp_path):
    assert LocalFolderStore(tmp_path / "does-not-exist").list() == []


def test_settings_dict_matches_the_saved_json(tmp_path):
    report = CLReport()
    report.set_data({"DM": pd.DataFrame({"Subject": ["01"], "Age": [42]})})
    report.add_selected_form("DM")
    path = tmp_path / "baseline.json"

    report.save_setting_to_json(str(path), setting_name="baseline")

    assert json.loads(path.read_text(encoding="utf-8")) == report.settings_to_dict(
        "baseline"
    )


# ---------------------------------------------------------------------------
# output file names


def test_output_file_name_stamps_and_adds_extension():
    now = datetime(2026, 9, 30, 10, 15, 0)

    assert output_file_name("DEMO01_DSMB", now=now) == "DEMO01_DSMB 260930_101500.xlsx"
    assert output_file_name("report.xlsx", now=now) == "report 260930_101500.xlsx"
    assert output_file_name("  ", now=now) == "260930_101500.xlsx"


def test_output_file_name_cannot_leave_the_output_folder():
    name = output_file_name(
        "..\\..\\secret/report:v2", now=datetime(2026, 1, 2, 3, 4, 5)
    )

    assert "/" not in name and "\\" not in name and ":" not in name
    assert name == ".._.._secret_report_v2 260102_030405.xlsx"


# ---------------------------------------------------------------------------
# data loading from uploads


def test_load_tabular_file_accepts_an_open_file_with_a_name():
    upload = io.BytesIO(b"Subject,Result\n01,N/A\n")

    df = load_tabular_file(upload, name="labs.csv")

    assert df["Result"].tolist() == ["N/A"]


def test_load_tabular_file_rejects_unknown_upload_types():
    with pytest.raises(ValueError):
        load_tabular_file(io.BytesIO(b"x"), name="notes.txt")


# ---------------------------------------------------------------------------
# session: selection survives a data rebuild


def test_selection_is_restored_after_rebuilding_the_data():
    data = {
        "DM": pd.DataFrame({"Subject": ["01"], "Site": ["A"], "Age": [42]}),
        "AE": pd.DataFrame({"Subject": ["01"], "Site": ["A"], "Term": ["Rash"]}),
    }
    report = CLReport()
    report.set_data(data)
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.set_common_item_state("Subject", selected=True)
    state = capture_selection(report)

    # A rebuild (for example a cut-off reload) creates fresh form objects.
    report.set_data({name: df.copy() for name, df in data.items()})
    assert report.get_selected_forms_list() == []
    restore_selection(report, state)

    assert report.get_selected_forms_list() == ["DM"]
    assert report.selected_forms["DM"].get_selected_form_items() == ["Age"]
    assert "Subject" in report.get_selected_common_items()
