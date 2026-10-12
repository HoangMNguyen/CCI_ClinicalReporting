"""Tests for the headless / programmatic API surface.

These exercise the building blocks that let the reporting engine be driven
without the PySide6 UI (tool chaining):

* ``models.ReportConfig`` -- declarative config wrapper over the settings JSON
* ``report.CLReport.load_setting_from_dict`` / ``apply_config`` -- file-free
  configuration + reconciliation
* ``session.apply_saved_setting`` -- applying a saved setting as the desktop
  does: its study, tidied joins, and what the data lacks
* ``data`` -- data loading / input shaping
* ``export`` -- xlsx / csv / bytes export

The capstone tests cover the end-to-end chain (load -> configure -> run ->
export) and assert that a config saved from the UI flow produces an identical
report when replayed programmatically.
"""

import io
import json

import openpyxl
import pandas as pd
from pandas.testing import assert_frame_equal

import clinical_reporting as api
from clinical_reporting import data, session
from clinical_reporting.data import (
    build_additional_data_map,
    parse_study_name,
    strip_subject_prefix,
)
from clinical_reporting.export import (
    dataframe_to_xlsx_bytes,
    prepare_export_dataframe,
    write_csv,
    write_xlsx,
)
from clinical_reporting.models import ReportConfig
from clinical_reporting.report import CLReport

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _two_form_data():
    """Two forms sharing only ``Subject``; ``Age``/``Pulse`` are form-specific."""
    return {
        "DM": pd.DataFrame({"Subject": ["001", "002", "003"], "Age": [75, 41, 29]}),
        "VS": pd.DataFrame({"Subject": ["001", "002", "003"], "Pulse": [70, 90, 55]}),
    }


def _configure_reference_report():
    """Build a report the way the UI would: select forms, items, joins, common."""
    report = CLReport()
    report.set_study_name("STUDY01")
    report.set_data(_two_form_data())

    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.selected_forms["DM"].set_join_order(1)

    report.add_selected_form("VS")
    report.selected_forms["VS"].set_form_item_state("Pulse", selected=True)
    report.selected_forms["VS"].set_join_items(["Subject"])
    report.selected_forms["VS"].set_join_order(2)
    report.selected_forms["VS"].set_join_how("Left join")

    report.set_common_item_state("Subject", selected=True)
    return report


def _reference_settings_dict(tmp_path):
    """Round-trip the reference report through the on-disk settings schema."""
    report = _configure_reference_report()
    path = tmp_path / "reference.json"
    report.save_setting_to_json(str(path), setting_name="baseline")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------
# ReportConfig
# ---------------------------------------------------------------------------


def test_report_config_defaults_to_empty():
    config = ReportConfig()
    assert config.raw == {}
    assert config.study_name is None
    assert config.setting_name is None


def test_report_config_from_dict_is_deep_copied():
    source = {"study_name": "S1", "selected_common_items": ["Subject"]}
    config = ReportConfig.from_dict(source)

    # Mutating the source must not leak into the config.
    source["selected_common_items"].append("Visit")
    source["study_name"] = "MUTATED"

    assert config.study_name == "S1"
    assert config.raw["selected_common_items"] == ["Subject"]


def test_report_config_to_dict_returns_isolated_copy():
    config = ReportConfig.from_dict({"selected_common_items": ["Subject"]})
    snapshot = config.to_dict()
    snapshot["selected_common_items"].append("Visit")

    # The internal raw dict is untouched by edits to the returned copy.
    assert config.raw["selected_common_items"] == ["Subject"]


def test_report_config_exposes_study_and_setting_name():
    config = ReportConfig.from_dict(
        {"study_name": "STUDY01", "setting_name": "baseline"}
    )
    assert config.study_name == "STUDY01"
    assert config.setting_name == "baseline"


def test_report_config_json_roundtrip(tmp_path):
    raw = {
        "study_name": "STUDY01",
        "setting_name": "baseline",
        "selected_common_items": ["Subject"],
        "rename_dict": {"DM.Age": "Age"},
    }
    path = tmp_path / "setting.json"

    ReportConfig.from_dict(raw).to_settings_json(path)
    reloaded = ReportConfig.from_settings_json(path)

    assert reloaded.raw == raw


def test_report_config_reads_settings_saved_by_engine(tmp_path):
    """A config loaded from a UI-saved settings file mirrors the saved data."""
    settings = _reference_settings_dict(tmp_path)
    path = tmp_path / "engine_setting.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(settings, handle)

    config = ReportConfig.from_settings_json(path)

    assert config.study_name == "STUDY01"
    assert config.setting_name == "baseline"
    assert config.raw["selected_forms"]["DM"]["selected_form_items"] == ["Age"]


# ---------------------------------------------------------------------------
# CLReport.load_setting_from_dict
# ---------------------------------------------------------------------------


def test_load_setting_from_dict_applies_settings_without_io(tmp_path):
    settings = _reference_settings_dict(tmp_path)

    report = CLReport()
    returned = report.load_setting_from_dict(settings)

    # Returns the same settings mapping it was given.
    assert returned is settings
    assert report.study_name == "STUDY01"
    assert report.get_selected_common_items() == ["Subject"]
    assert report.selected_forms["DM"].get_selected_form_items() == ["Age"]
    assert report.selected_forms["VS"].get_join_items() == ["Subject"]
    assert report.selected_forms["VS"].get_join_how() == "Left join"


# ---------------------------------------------------------------------------
# CLReport.apply_config
# ---------------------------------------------------------------------------


def test_apply_config_with_matching_data_reports_nothing_missing(tmp_path):
    config = ReportConfig.from_dict(_reference_settings_dict(tmp_path))

    report = CLReport()
    report.set_data(_two_form_data())
    missing = report.apply_config(config)

    assert missing == {"forms": [], "items": []}
    assert set(report.selected_forms) == {"DM", "VS"}
    assert report.get_selected_common_items() == ["Subject"]


def test_apply_config_accepts_plain_dict(tmp_path):
    """For convenience, apply_config also accepts a raw settings dict."""
    settings = _reference_settings_dict(tmp_path)

    report = CLReport()
    report.set_data(_two_form_data())
    missing = report.apply_config(settings)

    assert missing == {"forms": [], "items": []}
    assert "DM" in report.selected_forms


def test_apply_config_reports_forms_and_items_missing_from_data(tmp_path):
    """Config referencing forms/items absent from the loaded data is reconciled."""
    settings = _reference_settings_dict(tmp_path)

    report = CLReport()
    # Only DM is present, and it is missing the configured 'Age' column.
    report.set_data({"DM": pd.DataFrame({"Subject": ["001"], "Weight": [70]})})
    missing = report.apply_config(ReportConfig.from_dict(settings))

    assert "VS" in missing["forms"]
    assert "DM.Age" in missing["items"]
    assert "VS" not in report.selected_forms


def test_apply_config_without_data_drops_everything(tmp_path):
    """set_data must come first; otherwise reconciliation drops all selections."""
    config = ReportConfig.from_dict(_reference_settings_dict(tmp_path))

    report = CLReport()  # note: no set_data
    missing = report.apply_config(config)

    assert sorted(missing["forms"]) == ["DM", "VS"]
    assert report.selected_forms == {}


def test_apply_config_then_create_report_matches_reference(tmp_path):
    """The strongest guarantee: a config replayed via the API yields the same
    DataFrame as the report that produced it."""
    reference = _configure_reference_report()
    expected = reference.create_report().reset_index(drop=True)

    path = tmp_path / "setting.json"
    reference.save_setting_to_json(str(path), setting_name="baseline")

    replayed = CLReport()
    replayed.set_data(_two_form_data())
    replayed.apply_config(ReportConfig.from_settings_json(str(path)))
    actual = replayed.create_report().reset_index(drop=True)

    assert list(actual.columns) == ["Subject", "DM.Age", "VS.Pulse"]
    assert_frame_equal(actual, expected)


# ---------------------------------------------------------------------------
# loaders
# ---------------------------------------------------------------------------


def test_parse_study_name_uses_third_segment_when_present():
    assert parse_study_name("Corelisting_Export_STUDY01_2026.zip") == "STUDY01"
    assert parse_study_name("/some/dir/Listing_For_ABC123_cut.zip") == "ABC123"


def test_parse_study_name_falls_back_to_stem():
    assert parse_study_name("demo.zip") == "demo"
    assert parse_study_name("one_two.zip") == "one_two"


def test_strip_subject_prefix_variants():
    assert strip_subject_prefix("UPCC-12345") == "12345"
    assert strip_subject_prefix("UPCC 987") == "987"
    assert strip_subject_prefix("100-555") == "555"
    assert strip_subject_prefix("NO_PREFIX") == "NO_PREFIX"
    assert strip_subject_prefix(123) == 123  # non-string passes through


def test_build_additional_data_map_shapes_inputs():
    file_path = "/data/labs.csv"
    inputs = {
        file_path: pd.DataFrame(
            {
                "Subject": ["UPCC-111", "UPCC222", "100-333"],
                "Result": [1, 2, 3],
                "Unnamed: 0": [0, 0, 0],
            }
        )
    }
    form_names = {file_path: "LABS"}
    column_names = {(file_path, "Result"): "Lab Result"}

    data_map = build_additional_data_map(inputs, form_names, column_names)

    assert list(data_map) == ["LABS"]
    df = data_map["LABS"]
    # Unnamed column dropped, Result renamed, Subject prefixes stripped.
    assert list(df.columns) == ["Subject", "Lab Result"]
    assert df["Subject"].tolist() == ["111", "222", "333"]


def test_build_additional_data_map_form_name_defaults_to_filename():
    file_path = "/data/sample.csv"
    inputs = {file_path: pd.DataFrame({"Subject": ["001"], "A": [1]})}

    data_map = build_additional_data_map(inputs, form_names={}, column_names={})

    assert "sample.csv" in data_map


def test_package_reexports_are_the_canonical_readers():
    """The public package API does not duplicate reader implementations."""
    assert api.load_tabular_file is data.load_tabular_file
    assert api.load_additional_inputs is data.load_additional_inputs
    assert api.read_data_dict_zip_corelisting is data.read_data_dict_zip_corelisting
    assert api.try_load_tabular_files is data.try_load_tabular_files


def test_load_additional_inputs_via_loaders(tmp_path):
    csv_path = tmp_path / "extra.csv"
    csv_path.write_text("Subject,Value\n001,5\n", encoding="utf-8")

    loaded = data.load_additional_inputs([str(csv_path)])

    assert len(loaded) == 1
    (df,) = loaded.values()
    assert df["Value"].tolist() == [5]


# ---------------------------------------------------------------------------
# exporter
# ---------------------------------------------------------------------------


def test_prepare_export_dataframe_formats_dates_without_mutating_input():
    original = pd.DataFrame(
        {
            "Subject": ["001", "002"],
            "Visit Date": pd.to_datetime(["2024-01-05", "2024-02-10"]),
            # object dtype: datetime objects mixed with a non-date sentinel
            "D+28": pd.Series([pd.Timestamp("2025-11-11"), "N/A"], dtype=object),
            "Age": [30, 40],
        }
    )

    exported = prepare_export_dataframe(original)

    # Datetime-like values rendered as short-date text.
    assert exported["Visit Date"].tolist() == ["1/5/2024", "2/10/2024"]
    assert exported["D+28"].tolist() == ["11/11/2025", "N/A"]
    # Non-date columns untouched.
    assert exported["Age"].tolist() == [30, 40]
    # Input DataFrame is not mutated.
    assert pd.api.types.is_datetime64_any_dtype(original["Visit Date"])


def test_write_xlsx_writes_styled_short_date_output(tmp_path):
    df = pd.DataFrame(
        {
            "Subject": ["001", "002"],
            "Visit Date": pd.to_datetime(["2024-01-05", "2024-02-10"]),
        }
    )
    out_path = tmp_path / "report.xlsx"

    returned = write_xlsx(df, str(out_path))

    assert returned == str(out_path)
    worksheet = openpyxl.load_workbook(out_path).active

    # Header row uses the bold style applied by get_excel_formats.
    header_cells = [worksheet.cell(row=1, column=c) for c in (1, 2)]
    assert [c.value for c in header_cells] == ["Subject", "Visit Date"]
    assert all(c.font.bold for c in header_cells)

    # Dates are written as plain strings, not native Excel datetimes.
    date_cells = [worksheet.cell(row=r, column=2) for r in (2, 3)]
    assert [c.value for c in date_cells] == ["1/5/2024", "2/10/2024"]
    assert all(c.data_type == "s" for c in date_cells)


def test_dataframe_to_xlsx_bytes_is_loadable(tmp_path):
    df = pd.DataFrame({"Subject": ["001"], "Age": [30]})

    payload = dataframe_to_xlsx_bytes(df)

    assert isinstance(payload, bytes) and payload
    worksheet = openpyxl.load_workbook(io.BytesIO(payload)).active
    assert worksheet.cell(row=1, column=1).value == "Subject"
    assert worksheet.cell(row=2, column=1).value == "001"


def test_write_csv_uses_short_date_formatting(tmp_path):
    df = pd.DataFrame(
        {
            "Subject": ["001"],
            "Visit Date": pd.to_datetime(["2024-01-05"]),
        }
    )
    out_path = tmp_path / "report.csv"

    returned = write_csv(df, str(out_path))

    assert returned == str(out_path)
    reloaded = pd.read_csv(out_path)
    assert reloaded.loc[0, "Visit Date"] == "1/5/2024"


# ---------------------------------------------------------------------------
# End-to-end chaining
# ---------------------------------------------------------------------------


def test_full_chaining_pipeline_load_configure_run_export(tmp_path):
    """Exercise the documented tool-chaining recipe end to end."""
    # 1. Build the data dict (here directly; in practice via loaders).
    data = _two_form_data()

    # Persist a configuration the way the UI would.
    setting_path = tmp_path / "setting.json"
    _configure_reference_report().save_setting_to_json(
        str(setting_path), setting_name="batch"
    )

    # 2. Load data + 3. apply config + 4. run.
    report = CLReport()
    report.set_data(data)
    missing = report.apply_config(ReportConfig.from_settings_json(str(setting_path)))
    assert missing == {"forms": [], "items": []}

    result = report.create_report()
    assert list(result.columns) == ["Subject", "DM.Age", "VS.Pulse"]

    # 5. Export to both a file and in-memory bytes.
    xlsx_path = tmp_path / "out.xlsx"
    write_xlsx(result, str(xlsx_path))
    assert xlsx_path.exists() and xlsx_path.stat().st_size > 0

    payload = dataframe_to_xlsx_bytes(result)
    worksheet = openpyxl.load_workbook(io.BytesIO(payload)).active
    headers = [
        worksheet.cell(row=1, column=c).value for c in range(1, result.shape[1] + 1)
    ]
    assert headers == list(result.columns)


# ---------------------------------------------------------------------------
# session.apply_saved_setting
# ---------------------------------------------------------------------------


def _three_forms():
    return {
        "DM": pd.DataFrame(columns=["Subject", "Site", "Age"]),
        "AE": pd.DataFrame(columns=["Subject", "Site", "Term"]),
        "VS": pd.DataFrame(columns=["Subject", "Site", "Pulse"]),
    }


def _joins_settings():
    report = CLReport()
    report.set_data(_three_forms())
    for form in ("DM", "AE", "VS"):
        report.add_selected_form(form)
    report.set_common_item_state("Subject", selected=True)
    report.set_common_item_state("Site", selected=True)
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.update_join_items("DM", [], 1, "Left join")
    report.update_join_items("AE", ["Subject", "Site"], 2, "Left join")
    report.update_join_items("VS", ["Subject", "Site"], 3, "Left join")
    return report.settings_to_dict("Joins")


def test_a_saved_setting_without_a_study_keeps_the_reports():
    settings = _joins_settings()
    settings["study_name"] = None
    report = session.new_report("DEMO01", _three_forms())

    session.apply_saved_setting(report, settings)

    assert report.study_name == "DEMO01"

    settings["study_name"] = "DEMO02"
    session.apply_saved_setting(report, settings)

    assert report.study_name == "DEMO02"


def test_a_saved_settings_joins_are_tidied_when_it_is_applied():
    settings = _joins_settings()
    settings["selected_forms"]["AE"].update(
        join_items=["Site", "Site", "Subject", "Visit"],
        join_order=7,
        join_how="Sideways",
    )
    report = session.new_report("DEMO01", _three_forms())

    session.apply_saved_setting(report, settings)

    assert report.get_join_list_dict()["AE"] == {
        "items": ["Site", "Subject"],
        "order": 3,
        "how": "Left join",
    }


def test_applying_a_saved_setting_says_what_the_data_lacks():
    settings = _joins_settings()
    settings["selected_forms"]["LAB"] = {
        "selected_form_items": ["Result"],
        "join_items": ["Subject", "Site"],
        "join_order": 3,
        "join_how": "Left join",
    }
    settings["selected_forms"]["DM"]["selected_form_items"].append("Height")
    report = session.new_report("DEMO01", _three_forms())

    missing = session.apply_saved_setting(report, settings)

    assert missing == {"forms": ["LAB"], "items": ["DM.Height"]}


# ---------------------------------------------------------------------------
# session.apply_additional_inputs
# ---------------------------------------------------------------------------


def test_additional_inputs_are_merged_into_the_report_by_their_form_names():
    dm = pd.DataFrame({"Subject": ["001"], "Age": [41]})
    lab = pd.DataFrame(
        {"Subject": ["001"], "Visit Dt": ["2026-09-01"], "Unnamed: 2": [None]}
    )
    report = session.new_report("DEMO01", {"DM": dm})

    applied = session.apply_additional_inputs(
        report,
        {"/x/lab.csv": lab},
        {"/x/lab.csv": "LAB"},
        {("/x/lab.csv", "Visit Dt"): "Visit Date"},
    )

    assert list(applied.forms) == ["LAB"]
    assert applied.signature == {"LAB": ("Subject", "Visit Date")}
    assert sorted(report.data) == ["DM", "LAB"]

    again = session.apply_additional_inputs(
        report, {"/x/lab.csv": lab}, {"/x/lab.csv": "LAB2"}, {}, previous_keys={"LAB"}
    )

    assert again.signature == {"LAB2": ("Subject", "Visit Dt")}
    assert sorted(report.data) == ["DM", "LAB2"]
    assert sorted(report.loaded_data) == ["DM", "LAB2"]
    assert report.loaded_data["DM"] is dm
