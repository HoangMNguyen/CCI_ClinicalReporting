# CCI Clinical Reporting & Automation Suite

A suite of four PySide6 desktop applications for clinical trial reporting,
built on a single shared headless backend (`clinical_reporting`). The Clinical
Reporting Tool is the flagship configurable report builder; the three
automation apps cover department-specific workflows (enrollment logs, DSMB
reports, safety listings, and SDS peer review). Each app runs from source with
`python -m <package>` and ships as its own standalone executable.

## Applications at a glance

| Application | What it produces | Run from source | Spec file |
| --- | --- | --- | --- |
| Clinical Reporting Tool | Configurable clinical report exports from Corelisting/CSV/Excel data | `python -m clinical_reporting` | `CCI Clinical Reporting.spec` |
| CCI Automation | Enrollment Logs, DSMB Reports, Clockify dashboards, formatting fixes | `python -m cci_automation` | `CCI Automation.spec` |
| Safety Automation | Corelisting AE & DLT listing workbook | `python -m safety_automation` | `Safety Automation.spec` |
| Peer Review Automation | Medidata SDS peer-review error report | `python -m peer_review_automation` | `Peer Review Automation.spec` |

## Setup

Python 3.10+ is required. The `python -m ...` commands are identical on every
platform; only venv activation and environment variables are shell-specific.

### 1. Create the environment (once per machine)

Linux / macOS (bash):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Windows (cmd.exe): activate with `.venv\Scripts\activate.bat` instead.

The requirements files build on each other:

| File | Contents | Install it to |
|---|---|---|
| `requirements-core.txt` | The Qt-free processing engine (pandas, numpy, xlsxwriter, openpyxl, requests, python-dateutil) | Run reports headless or on a server |
| `requirements.txt` | Core + PySide6 | Run the desktop apps |
| `requirements-dev.txt` | Desktop + `pytest` and `ruff` | Develop and test |
| `requirements-build.txt` | Desktop + PyInstaller | Build the executables |

Each dependency is pinned to its current major version so DSMB and safety
outputs stay reproducible; raise a bound deliberately after testing.
If PowerShell blocks `Activate.ps1`, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. If `python` is not
on PATH on Windows, use the `py` launcher (`py -m venv .venv`, etc.).

### 2. Run from the environment (each terminal session)

The packages are not pip-installed; every app imports from `src/` directly,
so activate the venv and put `src/` on the Python path:

Linux / macOS (bash):

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
```

Windows (cmd.exe): `set PYTHONPATH=src` after activating.

Then run any app the same way on every platform:

```bash
python -m clinical_reporting
python -m cci_automation
python -m safety_automation
python -m peer_review_automation
```

One-off alternative on bash without exporting:
`PYTHONPATH=src python -m clinical_reporting`.

## Clinical Reporting Tool

Desktop application for assembling clinical report outputs through a guided
UI. Users pick source forms, choose common or per-form items, set
joins/filters, comparisons, and export configured report settings.

- Use Core Listing and other sources from both Excel and CSV files.
- Form, common, and per-form item pickers with regex-based case-insensitive search filters.
- Join, rename, comparison, and filter configuration tables tailored for clinical datasets.
- Save/load settings plus quick run helpers for generating reports.
- Form names cannot include `.` because it is reserved for the form/item separator. Additional inputs default to the file name and must be renamed to remove dots.
- Headless reporting engine that can be driven programmatically without the UI, so the same logic can be reused in scripts, batch jobs, and tool chains. See [Programmatic / API usage](#programmatic--api-usage).

## CCI Automation

One window, five workflows, selected from a dropdown. Reports are written as
styled `.xlsx` files to a chosen output folder.

| Workflow | Input | Notes |
| --- | --- | --- |
| Enrollment Log | Corelisting ZIP | Studies 03325, 03821, 10325, 11823, 12423, 15122, 15420, 16321, 30425, 50425. Optional cut-off date. |
| DSMB Report | Corelisting ZIP | Studies 03325, 03821, 10325, 11823, 12423, 15122, 15420, 16321. Optional cut-off date. |
| Clockify Dashboard | Clockify detailed-report CSV, or live API when no file is selected | Produces a per-project dashboard with task/milestone/role hour breakdowns and validation tabs. |
| Add templated tasks | — | Creates the standard task template in a selected Clockify project. |
| Format for lab range issue and no leading 0 date | CSV or XLSX | Fixes scientific-notation lab ranges and strips leading zeros from dates. |

Enrollment Log and DSMB builders are per-study modules under
`src/cci_automation/enrollment_log/` and `src/cci_automation/dsmb/`; adding a
study means adding a module there and listing it in the dispatcher and the
combo box in `src/cci_automation/app.py`.

### Clockify configuration

Only the two Clockify workflows need credentials. Configure them either as
environment variables:

```powershell
$env:CCI_CLOCKIFY_API_KEY = "<api key>"
$env:CCI_CLOCKIFY_WORKSPACE_ID = "<workspace id>"
```

or as a git-ignored `src/cci_automation/clockify.json` next to `util.py`:

```json
{"api_key": "<api key>", "workspace_id": "<workspace id>"}
```

Environment variables take precedence over the file. When neither is set, the
app shows a clear error dialog instead of crashing. Never hardcode these
values in source.

## Safety Automation

Single workflow: **Corelisting AE & DLT report**. Select a Corelisting ZIP —
the study number is detected from the file name — and the app produces the
standardized Adverse Event / Dose-Limiting Toxicity listing workbook for the
Safety Department.

Supported studies are driven by `STUDY_KEY_MAP` in
`src/safety_automation/ae_corelisting/AECoreListing.py` (currently 03325,
10325, 12423, 15420, 16321), which maps each study to its form-name keys.
Adding a study is usually just a new map entry describing which Corelisting
forms hold the AE, dose-level, infusion, and end-of-study data.

## Peer Review Automation

Validates a Medidata **SDS (Study Design Spec)** workbook — the
`Form Definitions` and `Codelists` sheets — and writes every finding to
`<study> Peer Review Automation Output.xlsx`.

Checks include:

- Item names longer than 32 characters.
- Fields not marked Required (excluding Label/Boolean types).
- Date fields missing the "No Future Date" flag.
- Item/Item Group names not matching their External ID.
- Codelist display types (picklist vs. other) inconsistent with the number of visible options.
- Shared vs. non-shared naming conventions (`_YS_`/`_NS_`), and codelist/unit attachments matching item names.
- Optional naming-convention checks (`CL_`/`DT_`/`NM_`/`TX_`/... prefixes, help-text `YH`/`NH` markers) via the checkbox.
- Optional cross-check against an exported validation CSV, with a built-in ignore list for known-acceptable error names; results land on a separate "Validation Review" sheet.

The review logic is headless (`src/peer_review_automation/sds.py`) and usable
without the GUI: `SDSData(name_check, sds_path, validation_csv_path).output(out_dir)`.

## Shared backend

All three automation apps use `clinical_reporting` as their backend rather
than carrying their own copies: Corelisting ZIP loading and cleaning comes
from `clinical_reporting.data.read_data_dict_zip_corelisting`, study-name
parsing from `clinical_reporting.data.parse_study_name`, and shared Excel cell
styles from `clinical_reporting.export.get_named_excel_formats`. Their report
builders are Qt-free, so they can be scripted the same way as the reporting
engine below.

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
config = ReportConfig.from_dict(
    {
        "study_name": "STUDY01",
        "selected_common_items": ["Subject"],
        "selected_forms": {
            "DM": {
                "name": "DM",
                "selected_form_items": ["Age"],
                "join_items": [],
                "join_order": 1,
                "join_how": "Left join",
            },
            "VS": {
                "name": "VS",
                "selected_form_items": ["Pulse"],
                "join_items": ["Subject"],
                "join_order": 2,
                "join_how": "Left join",
            },
        },
        "rename_dict": {"DM.Age": "Age"},
        "static_filter_items": [["DM.Age", ">", "18"]],
        "dynamic_filter_items": [],
    }
)
report.apply_config(config)
```

> Note: form-specific items only exist when more than one form is loaded. With a
> single form every column is treated as a common item, so a column selected as
> a form item is reconciled into the common pool.

### Additional inputs and export options

```python
from clinical_reporting.data import (
    load_additional_inputs,
    build_additional_data_map,
)
from clinical_reporting.export import dataframe_to_xlsx_bytes, write_csv

# Combine a Corelisting zip with extra CSV/Excel files
base = read_data_dict_zip_corelisting("study_export.zip")
inputs = load_additional_inputs(["labs.csv"])  # {resolved_path: DataFrame}
extra = build_additional_data_map(
    inputs,
    form_names={path: "LABS" for path in inputs},  # path -> form name
    column_names={},  # (path, original_col) -> new name
)
report.set_data({**base, **extra})

# Export options
write_csv(df, "report.csv")  # CSV on disk
xlsx_bytes = dataframe_to_xlsx_bytes(df)  # in-memory bytes (e.g. stream over HTTP)
```

### Persisting a configuration

A programmatically built configuration can be written back to the same JSON the
UI reads, so headless runs and the UI stay interchangeable:

```python
report.save_setting_to_json("my_setting.json", setting_name="batch-run")
# or, from a ReportConfig:
config.to_settings_json("my_setting.json")
```

To store settings somewhere other than a JSON file, take the dictionary and
hand it to a settings store (the desktop app uses the local-folder store):

```python
from clinical_reporting.settings_store import LocalFolderStore

settings = report.settings_to_dict("batch-run")
LocalFolderStore("C:/Reports/settings").save("batch-run", settings)
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

### Linting and formatting

Ruff is configured in `pyproject.toml`. Apply all configured safe lint fixes
in one batch with:

```bash
python -m ruff check src tests --fix
```

Verify the result without changing files with:

```bash
python -m ruff check src tests
```

When a repository-wide formatting pass is intentional, run:

```bash
python -m ruff format src tests
```

VS Code will recommend the Ruff extension and apply the same fixes whenever a
Python file is saved. Unsafe Ruff fixes remain disabled by default.

Testing notes:
- `tests/conftest.py` inserts both project root and `src/` into `sys.path`, runs
  Qt offscreen (no windows appear), and provides one shared `qapp` fixture.
- Larger sample artifacts are stored in `tests/data/`.
- Keep logic tests in `tests/unit/`, workflow-level checks in
  `tests/integration/`, and tests of the shared design system (`cci_ui`) in
  `tests/ui/`.
- `tests/ui/test_theme_tokens.py` checks that the design tokens still match the
  approved mockup in `docs/design/clinical-reporting-mockup.html`; change both
  together.

## Project Structure

The processing modules are the Qt-free core: the `clinical_reporting` modules
below (everything except `__main__.py` and `ui/`) and the sibling tools'
processing packages never import PySide6, and
`tests/unit/test_headless_imports.py` enforces this. The core can therefore run
headless or behind a future web front end. Front ends (`ui/`, the sibling
`app.py` files) only collect input and show results; decisions about how the
report changes belong in the core.

```text
src/clinical_reporting/
  __main__.py                  # runtime entry: python -m clinical_reporting
  models.py                    # form/config models, labels, identifiers
  report.py                    # report state, persistence, reconciliation
  session.py                   # what happens to a report when the user acts
  settings_store.py            # where saved settings live (local folder today)
  feedback.py                  # status messages tagged info/success/warning/error
  filenames.py                 # safe file names for exports and saved settings
  pipeline.py                  # joins, filters, ordering, renames, formatting
  validation.py                # executable-report validation
  data.py                      # Corelisting ZIP, CSV, Excel, extra inputs (paths or uploads)
  export.py                    # xlsx/csv/bytes rendering
  ui/                          # PySide6 desktop front end
    window.py                  # main window composed from feature mixins
    settings_tab.py            # inputs, cutoff, and saved settings
    selection_tabs.py          # forms, common items, and form items
    filters_tab.py             # static and dynamic filters
    join_config.py             # join order, type, and items
    ordering_tab.py            # output order and renames
    run_save_tab.py            # preview, run, and save
    _generated/ui_form.py      # generated UI binding; do not edit

src/cci_ui/                    # shared design system for all four tools
  app.py                       # create_app(): style, font, theme, error dialog
  assets.py                    # finds bundled files from source or a built exe
  theme/tokens.py              # colors, sizes, type scale (no Qt; also exports CSS)
  theme/qss.py                 # stylesheet built from the tokens (no Qt)
  theme/palette.py             # Qt palette built from the tokens
  theme/fonts.py               # loads the bundled Inter font
  theme/manager.py             # System/Light/Dark and density, shared by all tools
  assets/fonts/                # Inter 4.1 (SIL Open Font License)

src/cci_automation/            # Enrollment Log, DSMB, Clockify tools
  __main__.py                  # runtime entry: python -m cci_automation
  util.py                      # Clockify API and shared stats helpers
  enrollment_log/  dsmb/  clockify/  format_tools/

src/safety_automation/         # Corelisting AE & DLT report
  __main__.py                  # runtime entry: python -m safety_automation
  ae_corelisting/

src/peer_review_automation/    # Medidata SDS peer review
  __main__.py                  # runtime entry: python -m peer_review_automation
  sds.py                       # headless SDS review logic

resource/                      # Designer assets and generated UI resources
tests/
  unit/                        # fast logic-focused tests
  integration/                 # workflow/reporting behavior tests
  data/                        # sample test inputs
```

## Building the Executables

Each application has a PyInstaller spec file at the repository root. Install
the build requirements first:

```bash
python -m pip install -r requirements-build.txt
```

Then build the app(s) you need:

```bash
python -m PyInstaller "CCI Clinical Reporting.spec"
python -m PyInstaller "CCI Automation.spec"
python -m PyInstaller "Safety Automation.spec"
python -m PyInstaller "Peer Review Automation.spec"
```

Executables land in `dist/`. All four builds are one-file, windowed, and
exclude PyQt5/matplotlib.

### Versioning a release

There is **one spec per application, not one per version**. The spec file
names are permanent; the version lives in exactly one place per app:

| Application | Version constant |
| --- | --- |
| Clinical Reporting Tool | `src/clinical_reporting/__init__.py` |
| CCI Automation | `src/cci_automation/__init__.py` |
| Safety Automation | `src/safety_automation/__init__.py` |
| Peer Review Automation | `src/peer_review_automation/__init__.py` |

To cut a release, bump that one string and rebuild:

```python
__version__ = "2.01"
```

`build_support.py` reads it and stamps it into both the executable's file
name (`CCI Automation V1.22.exe`) and its Windows VERSIONINFO resource, so
the version shown in Explorer under **Properties -> Details** can never drift
from the version in the file name. The running app can also report its own
version via `<package>.__version__`.

For a one-off build without editing the source, override with an environment
variable:

```powershell
$env:APP_VERSION = "2.01"; python -m PyInstaller "CCI Automation.spec"
```

```bash
APP_VERSION=2.01 python -m PyInstaller "CCI Automation.spec"
```

Credential files bundled at build time (both are ignored by Git and must exist
locally before building):

- **CCI Clinical Reporting** embeds `src/clinical_reporting/telemetry.json` so
  users do not need to configure environment variables; use
  `telemetry.example.json` as the schema when creating or rotating it.
- **CCI Automation** embeds `src/cci_automation/clockify.json` (see
  [Clockify configuration](#clockify-configuration)).
- Safety Automation and Peer Review Automation need no bundled data files.

Note: the `.spec` files and `build_support.py` are tracked in Git like any
other source file — `.gitignore` no longer ignores `*.spec`. A spec diff now
always means a real change to the build recipe, never a version bump.

## Notes
- The UI resizes dynamically.
- Avoid modifying generated `build/` and `dist/` artifacts in normal development workflows.
