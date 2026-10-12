"""Saved settings kept in a local folder (clinical_reporting.settings_store)."""

import json

import pytest

from clinical_reporting.settings_store import (
    LocalFolderStore,
    SavedSetting,
    find_saved_setting,
    read_settings_json,
    settings_from_json,
    settings_to_json,
    write_settings_json,
)
from clinical_reporting.workflow import WorkflowInputError


def test_a_setting_is_saved_as_json_with_a_four_space_indent():
    assert settings_to_json({"a": [1]}) == '{\n    "a": [\n        1\n    ]\n}'
    assert settings_from_json('{"a": [1]}') == {"a": [1]}


def test_a_setting_written_to_a_file_reads_back_the_same(tmp_path):
    path = tmp_path / "monthly.json"

    write_settings_json(path, {"setting_name": "monthly", "order_list": ["Subject"]})

    assert read_settings_json(path) == {
        "setting_name": "monthly",
        "order_list": ["Subject"],
    }


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


def _saved_settings(folder):
    write_settings_json(
        folder / "a.json",
        {"setting_name": "Monthly AE review", "study_name": "DEMO01"},
    )
    write_settings_json(folder / "b.json", {"study_name": "DEMO02"})
    write_settings_json(
        folder / "c.json",
        {"setting_name": "Monthly AE review", "study_name": "DEMO02"},
    )


def test_a_saved_setting_is_found_by_the_name_the_desktop_shows(tmp_path):
    _saved_settings(tmp_path)

    assert (
        find_saved_setting("Monthly AE review", folder=tmp_path, study_name="DEMO01")
        == tmp_path / "a.json"
    )
    assert find_saved_setting("b", folder=tmp_path) == tmp_path / "b.json"


def test_a_name_several_settings_share_or_none_has_is_refused(tmp_path):
    _saved_settings(tmp_path)

    with pytest.raises(WorkflowInputError) as several:
        find_saved_setting("Monthly AE review", folder=tmp_path)
    with pytest.raises(WorkflowInputError) as none:
        find_saved_setting("Weekly", folder=tmp_path)
    # A setting with a name isn't listed under its file's stem.
    with pytest.raises(WorkflowInputError) as by_stem:
        find_saved_setting("a", folder=tmp_path)

    assert str(several.value) == (
        f"Several saved settings are called “Monthly AE review” in {tmp_path}: "
        "a.json, c.json."
    )
    assert str(none.value) == f"No saved setting is called “Weekly” in {tmp_path}."
    assert str(by_stem.value) == f"No saved setting is called “a” in {tmp_path}."
