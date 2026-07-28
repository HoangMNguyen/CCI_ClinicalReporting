# Clinical Reporting Tool

Desktop application for assembling clinical report outputs through a guided PySide6 UI. Users can pick source forms, choose common or per-form items, set joins/filters, comparisons, and export configured report settings.

## Features
- Use Core Listing and other sources from both Excel and CSV files.
- Form, common, and per-form item pickers with regex-based case-insensitive search filters.
- Join, rename, comparison, and filter configuration tables tailored for clinical datasets.
- Save/load settings plus quick run helpers for generating reports.
- Form names cannot include `.` because it is reserved for the form/item separator. Additional inputs default to the file name and must be renamed to remove dots.
- Headless reporting engine that can be driven programmatically without the UI, so the same logic can be reused in scripts, batch jobs, and tool chains. See [Programmatic / API usage](#programmatic--api-usage).

## Setup

### 1. Install dependencies
```bash
python -m pip install -r requirements.txt
python -m pip install pytest  # test runner
```

### 2. Run the application
Primary entry point:
```bash
PYTHONPATH=src python -m clinical_reporting
```

## Programmatic / API usage

The reporting engine is decoupled from the PySide6 UI, so it can be driven
directly from another Python program (scripts, batch jobs, tool chains, or a
future service layer). The UI is just one client of the same core engine.

The pipeline has four headless building blocks:

| Step | Module | What it does |
| --- | --- | --- |
| Load data | `clinical_reporting.data` | Read a Corelisting zip / CSV / Excel into a `{form_name: DataFrame}` dict and shape additional inputs. |
| Configure | `clinical_reporting.models.ReportConfig` | A typed wrapper over the same settings JSON the UI saves/loads. |
| Run | `clinical_reporting.report.CLReport` | Apply the config to the data and execute `create_report()`. |
| Export | `clinical_reporting.export` | Write the result to xlsx/csv, or render it to bytes. |

None of these import Qt, so they run anywhere Python + pandas are available.

### Minimal end-to-end example

```python
from clinical_reporting import CLReport, ReportConfig
from clinical_reporting.data import read_data_dict_zip_corelisting
from clinical_reporting.export import write_xlsx

# 1. Load the study data into {form_name: DataFrame}
report = CLReport()
report.set_data(read_data_dict_zip_corelisting("study_export.zip"))

# 2. Apply a configuration saved from the UI (load + reconcile in one call)
missing = report.apply_config(ReportConfig.from_settings_json("setting.json"))
if missing["forms"] or missing["items"]:
    print("Dropped (not present in current data):", missing)

# 3. Run the engine, then 4. export
df = report.create_report()
write_xlsx(df, "report.xlsx")
```

`create_report()` validates the complete definition before execution and raises
`ReportValidationError` instead of silently ignoring invalid joins, filters, or
output names. Call `report.validate()` first when a program needs to present all
issues at once; each issue exposes `code`, `message`, `field`, and `to_dict()`.

`set_data()` must be called before `apply_config()` so the configuration can be
reconciled against the columns actually present. `apply_config()` returns a
`{"forms": [...], "items": [...]}` report of anything dropped because the
current data no longer supports it — the same information the UI shows as a
warning label.

### Building a configuration in code

Any `.json` saved from the UI is a valid config, but you can also build one in
memory using the same schema:

```python
config = ReportConfig.from_dict({
    "study_name": "STUDY01",
    "selected_common_items": ["Subject"],
    "selected_forms": {
        "DM": {"name": "DM", "selected_form_items": ["Age"],
               "join_items": [], "join_order": 1, "join_how": "Left join"},
        "VS": {"name": "VS", "selected_form_items": ["Pulse"],
               "join_items": ["Subject"], "join_order": 2, "join_how": "Left join"},
    },
    "rename_dict": {"DM.Age": "Age"},
    "static_filter_items": [["DM.Age", ">", "18"]],
    "dynamic_filter_items": [],
})
report.apply_config(config)
```

> Note: form-specific items only exist when more than one form is loaded. With a
> single form every column is treated as a common item, so a column selected as
> a form item is reconciled into the common pool.

### Additional inputs and export options

```python
from clinical_reporting.data import (
    load_additional_inputs, build_additional_data_map,
)
from clinical_reporting.export import dataframe_to_xlsx_bytes, write_csv

# Combine a Corelisting zip with extra CSV/Excel files
base = read_data_dict_zip_corelisting("study_export.zip")
inputs = load_additional_inputs(["labs.csv"])          # {resolved_path: DataFrame}
extra = build_additional_data_map(
    inputs,
    form_names={path: "LABS" for path in inputs},      # path -> form name
    column_names={},                                   # (path, original_col) -> new name
)
report.set_data({**base, **extra})

# Export options
write_csv(df, "report.csv")                            # CSV on disk
xlsx_bytes = dataframe_to_xlsx_bytes(df)               # in-memory bytes (e.g. stream over HTTP)
```

### Persisting a configuration

A programmatically built configuration can be written back to the same JSON the
UI reads, so headless runs and the UI stay interchangeable:

```python
report.save_setting_to_json("my_setting.json", setting_name="batch-run")
# or, from a ReportConfig:
config.to_settings_json("my_setting.json")
```

## Testing

`pytest` is used for both unit and integration tests.

Run the full suite:
```bash
python -m pytest -q
```

Run only unit tests:
```bash
python -m pytest -q tests/unit
```

Run only integration tests:
```bash
python -m pytest -q tests/integration
```

Run a single test file while iterating:
```bash
python -m pytest -q tests/unit/test_join_deduplication.py
```

Useful local debugging options:
```bash
python -m pytest -x -vv
```

Testing notes:
- `tests/conftest.py` inserts both project root and `src/` into `sys.path`.
- Larger sample artifacts are stored in `tests/data/`.
- Keep logic tests in `tests/unit/` and workflow-level checks in `tests/integration/`.

## Project Structure

```text
src/clinical_reporting/
  __main__.py                  # runtime entry: python -m clinical_reporting
  models.py                    # form/config models, labels, identifiers
  report.py                    # report state, persistence, reconciliation
  pipeline.py                  # joins, filters, ordering, renames, formatting
  validation.py                # executable-report validation
  data.py                      # Corelisting ZIP, CSV, Excel, extra inputs
  export.py                    # xlsx/csv/bytes rendering
  ui/
    window.py                  # main window, shared behavior, navigation
    workspace.py               # inputs, cutoff, and saved settings
    selection.py               # forms, common items, and form items
    rules.py                   # joins, filters, renames, output order
    output.py                  # preview, run, and save
    _generated/ui_form.py      # generated UI binding; do not edit

resource/                      # Designer assets and generated UI resources
tests/
  unit/                        # fast logic-focused tests
  integration/                 # workflow/reporting behavior tests
  data/                        # sample test inputs
```

## Building the Executable

If you need a standalone executable, install PyInstaller first:
```bash
python -m pip install pyinstaller
```

Then build:
```bash
pyinstaller --onefile --strip --name "CCI Clinical Reporting V1.00" --windowed --paths src --add-data "src/clinical_reporting/telemetry.json;clinical_reporting" "src/clinical_reporting/__main__.py" --exclude PyQt5 --exclude matplotlib
```

The build command embeds the local `src/clinical_reporting/telemetry.json` in
the executable so users do not need to configure environment variables. The
real file contains a shared credential and is ignored by Git; use
`telemetry.example.json` as the schema when creating or rotating it. Environment
variables remain optional overrides for development and testing.

## Notes
- The UI resizes dynamically.
- Avoid modifying generated `build/` and `dist/` artifacts in normal development workflows.
