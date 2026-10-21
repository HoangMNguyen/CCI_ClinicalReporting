"""The export's file name, kept with a saved setting."""

import logging

import pandas as pd
import pytest

from clinical_reporting import export_name, session
from clinical_reporting.export_name import SETTINGS_KEY, ExportName
from clinical_reporting.report import CLReport
from clinical_reporting.settings_store import (
    LocalFolderStore,
    settings_from_json,
    settings_to_json,
)

# --------------------------------------------------------------------------
# Saving


@pytest.mark.parametrize("name", ["", "   ", ".xlsx", " .XLSX "])
def test_a_setting_without_a_file_name_is_saved_as_before(name):
    before = CLReport().settings_to_dict("monthly")

    settings = export_name.add_to_settings(dict(before), name, add_date_time=False)

    assert settings == before
    assert SETTINGS_KEY not in settings


def test_the_file_name_is_saved_as_the_export_uses_it():
    settings = export_name.add_to_settings(
        {"setting_name": "monthly"}, " DEMO01/DSMB.xlsx ", add_date_time=False
    )

    assert settings == {
        "setting_name": "monthly",
        SETTINGS_KEY: {"name": "DEMO01_DSMB", "add_date_time": False},
    }


def test_saving_without_a_file_name_drops_the_one_saved_before():
    settings = {SETTINGS_KEY: {"name": "AE review", "add_date_time": True}}

    assert export_name.add_to_settings(settings, "", add_date_time=True) == {}


def test_the_option_is_saved_as_true_or_false():
    settings = export_name.add_to_settings({}, "AE review", add_date_time=0)

    assert settings[SETTINGS_KEY]["add_date_time"] is False


# --------------------------------------------------------------------------
# Loading


def test_the_file_name_round_trips_through_the_saved_json():
    settings = export_name.add_to_settings({}, "DEMO01 DSMB", add_date_time=False)

    loaded = export_name.from_settings(settings_from_json(settings_to_json(settings)))

    assert loaded == ExportName("DEMO01 DSMB", False)


def test_settings_from_before_the_key_have_no_file_name(caplog):
    with caplog.at_level(logging.WARNING):
        assert export_name.from_settings(CLReport().settings_to_dict("old")) is None
        assert export_name.from_settings({SETTINGS_KEY: None}) is None
        assert export_name.from_settings(None) is None

    # Settings saved before the key are normal: nothing to log.
    assert caplog.text == ""


def test_the_date_and_time_are_added_unless_the_setting_says_not_to():
    saved = export_name.from_settings({SETTINGS_KEY: {"name": "AE review"}})

    assert saved == ExportName("AE review", True)


@pytest.mark.parametrize(
    "value",
    [
        "DEMO01 DSMB",
        42,
        True,
        [],
        {},
        {"name": ""},
        {"name": " .xlsx "},
        {"name": 7},
        {"name": None},
        {"add_date_time": False},
    ],
)
def test_a_key_without_a_usable_name_is_ignored(value, caplog):
    with caplog.at_level(logging.WARNING):
        assert export_name.from_settings({SETTINGS_KEY: value}) is None
    assert f"Ignoring saved {SETTINGS_KEY}" in caplog.text


@pytest.mark.parametrize("value", ["false", 0, None, [False]])
def test_an_unreadable_option_adds_the_date_and_time(value, caplog):
    with caplog.at_level(logging.WARNING):
        saved = export_name.from_settings(
            {SETTINGS_KEY: {"name": "AE review", "add_date_time": value}}
        )

    assert saved == ExportName("AE review", True)
    assert "not true or false" in caplog.text


def test_a_hand_edited_name_never_names_a_folder():
    saved = export_name.from_settings(
        {SETTINGS_KEY: {"name": "..\\reports/AE:v2.xlsx", "add_date_time": False}}
    )

    assert saved == ExportName(".._reports_AE_v2", False)


def test_a_setting_with_a_file_name_still_loads_in_the_report():
    """A version without this feature reads only the keys it knows."""
    data = {"DM": pd.DataFrame({"Subject": ["001"], "Age": [54]})}
    source = CLReport()
    source.set_data(data)
    source.add_selected_form("DM")
    plain = source.settings_to_dict("monthly")
    with_name = export_name.add_to_settings(
        dict(plain), "DEMO01 DSMB", add_date_time=False
    )

    states = []
    for settings in (plain, with_name):
        report = CLReport()
        report.set_data(data)
        missing = session.apply_saved_setting(report, settings)
        states.append((missing, report.settings_to_dict("monthly")))

    assert SETTINGS_KEY in with_name
    assert states[0] == states[1]


def test_the_settings_folder_lists_and_keeps_a_setting_with_a_file_name(tmp_path):
    store = LocalFolderStore(tmp_path)
    settings = export_name.add_to_settings(
        {"study_name": "DEMO01", "setting_name": "monthly"},
        "DEMO01 DSMB",
        add_date_time=False,
    )

    key = store.save("monthly", settings)

    assert [saved.name for saved in store.list("DEMO01")] == ["monthly"]
    assert export_name.from_settings(store.load(key)) == ExportName(
        "DEMO01 DSMB", False
    )
