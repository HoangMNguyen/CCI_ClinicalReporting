"""Saved settings kept in a local folder (clinical_reporting.settings_store)."""

import json

from clinical_reporting.settings_store import LocalFolderStore, SavedSetting


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
