# CCI Clinical Reporting & Automation Suite

A suite of four PySide6 desktop applications for clinical trial reporting,
built on a single shared headless backend (`clinical_reporting`) and a shared
design system (`cci_ui`). The Clinical Reporting Tool is the flagship
configurable report builder; the three automation apps cover
department-specific workflows (enrollment logs, DSMB reports, safety
listings, and SDS peer review). Each app runs from source with
`python -m <package>` and ships as its own standalone executable.

## Applications at a glance

| Application | What it produces | Run from source | Spec file |
| --- | --- | --- | --- |
| Clinical Reporting Tool | Configurable clinical report exports from Corelisting/CSV/Excel data | `python -m clinical_reporting` | `CCI Clinical Reporting.spec` |
| CCI Automation | Enrollment Logs, DSMB Reports, formatting fixes | `python -m cci_automation` | `CCI Automation.spec` |
| Safety Automation | Corelisting AE & DLT listing workbook | `python -m safety_automation` | `Safety Automation.spec` |
| Peer Review Automation | Medidata SDS peer-review error report | `python -m peer_review_automation` | `Peer Review Automation.spec` |

## Setup

Python 3.11 or newer is required (pandas 3 and numpy 2.4 need it). The
`python -m ...` commands are identical on every platform; only venv
activation and environment variables are shell-specific.

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
| `requirements-core.txt` | The Qt-free processing engine (pandas, numpy, xlsxwriter, openpyxl, python-dateutil) | Run reports headless or on a server |
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

Keyboard shortcuts:

| Keys | Does |
|---|---|
| Ctrl+Tab / Ctrl+PgDown, Ctrl+Shift+Tab / Ctrl+PgUp | Next / previous step |
| Ctrl+\\ | Show or hide the sidebar |
| Ctrl+F | Search (Forms, Common items, Form items, Order & rename) |
| F5 | Build the preview again (Preview & export) |
| Ctrl+E | Export to Excel (Preview & export) |
| Ctrl+S | Save the setting (Preview & export) |

### What's new in 2.10

- A new look: the steps in a sidebar with status badges, light and dark mode,
  a compact density, and a window that opens where it was.
- Reading the ZIP, the preview, and the export run in the background, so the
  window no longer freezes.
- Pages that need data say "No data loaded" until a ZIP (or an additional
  file) is loaded. Pages also show what was read from the ZIP, the preview's
  rows and columns, and the file name an export will write.
- A ZIP or an additional file that can't be read is now explained on the page
  (2.00 showed nothing: the ZIP's error was lost and the file was skipped).
  Clashing form names are explained there too, instead of in a dialog.
- New shortcuts: Ctrl+\\, Ctrl+F, F5, Ctrl+E and Ctrl+S (see the table
  above).
- A common item that a later form doesn't join on now comes out as that form's
  own column (`AE.Visit` next to `Visit`) instead of `Visit_x` and `Visit_y`,
  and a later form can join on it again. Reports whose forms join on every
  selected common item come out exactly as before.

## CCI Automation

One window with a sidebar of its three workflows, one page each (the
sidebar folds to icons on a narrow window). Each page builds its workbook in
the background and saves it in the chosen folder as
`<name> YYMMDD_HHMMSS.xlsx`, never over an existing file; the suggested names
are below.

| Page | Input | Suggested name | Notes |
| --- | --- | --- | --- |
| Enrollment log | Study + Corelisting ZIP | `<study> Enrollment Log` | Studies 03325, 03821, 10325, 11823, 12423, 15122, 15420, 16321, 30425, 50425. Optional cut-off date. |
| DSMB report | Study + Corelisting ZIP | `<study> DSMB Report` | Studies 03325, 03821, 10325, 11823, 12423, 15122, 15420, 16321. Optional cut-off date. |
| Format tools | CSV or XLSX file | `<file>_formatted` | Keeps lab ranges such as 10-20 as text, takes the leading zeros out of dates in columns whose name says "date" (as text: 03/05/2026 becomes 3/5/2026), and drops the ".1" pandas adds to a repeated column name. A CSV saved by Excel in Windows' own encoding is read too. |

The study is picked from the list, or taken from the ZIP's file name when that
names one (a ZIP named for another study than the one chosen is refused, with
a message). Each workflow is a plain `run()` that returns the workbook as an
`OutputFile`: `enrollment_log/EnrollmentLog.py`, `dsmb/DSMB.py` and
`format_tools/change_type.py`. The per-study DSMB modules still write a file,
which `DSMB.run()` reads back from a temporary folder, so the study's data
sits there only during a run. A study without a module gets a message saying
which studies are supported. Adding a study means adding its module under
`src/cci_automation/enrollment_log/` or `src/cci_automation/dsmb/`, a branch
for it in that workflow's dispatcher, and the study in its
`SUPPORTED_STUDIES` (the page lists those).

### What's new in 1.26

- The window is on the shared design system: a sidebar of the three
  workflows instead of the dropdown, light and dark mode, a compact density,
  and a window that opens where it was.
- The work runs in the background and is saved in the output folder, which is
  remembered, as `<name> YYMMDD_HHMMSS.xlsx`, never over an existing file.
  Run asks for an output folder when none is chosen (it used to do nothing)
  or the chosen one is gone.
- The Enrollment log and DSMB names no longer begin with the date
  (`260930-15420 DSMB Report`). Before, a file was also saved exactly as
  named, replacing any file of that name.
- The study is taken from the ZIP's file name when that names one.
- The Clockify Dashboard and Add templated tasks workflows are gone.
- Problems you can fix are messages instead of tracebacks:
  - a study without a module (the DSMB report used to make nothing,
    silently);
  - a ZIP named for another study than the one chosen;
  - an export without a Demographics (DM) form, or, for the DSMB report,
    with no submitted Demographics forms up to the cut-off date;
  - files that are gone or can't be read.
- The format tool no longer stops on a repeated column name, keeps names such
  as "pH 7.4" (it used to cut them to "pH 7"), and reads a CSV saved by Excel
  in Windows' own encoding.

## Safety Automation

One page: **AE & DLT listing**. Choose a Corelisting ZIP (the study number
comes from its file name) and an output folder, change the suggested file
name if you like, and Run. The app builds the standardized Adverse Event /
Dose-Limiting Toxicity workbook for the Safety Department in the background
and saves it as `<name> YYMMDD_HHMMSS.xlsx`, never over an existing file.

The work is `run()` in `src/safety_automation/ae_corelisting/AECoreListing.py`:
it takes the ZIP (a path or an open file) and returns the workbook as an
`OutputFile` (name and bytes) without touching a folder, so a script or a
future web version can call it too. The supported studies are
`SUPPORTED_STUDIES` there (03325, 10325, 11823, 12423, 15420, 16321); another
study's export gets a message saying so. Adding a study means adding it there,
an entry in `STUDY_KEY_MAP` naming the Corelisting forms that hold its AE,
cohort, dose-level, and infusion data (when they aren't named AE, DSCA,
DSDLA, and EXINF), its columns in the `get_*_header_list` methods, and its
values in the cohort, dose-level and infusion `get_*` methods.

### What's new in 1.08

- The window is on the shared design system: one page that resizes, light
  and dark mode, a compact density, and a window that opens where it was.
- The work runs in the background and is saved in the output folder, which is
  remembered, as `<name> YYMMDD_HHMMSS.xlsx`, never over an existing file.
  Run asks for an output folder when none is chosen (it used to do nothing)
  or the chosen one is gone.
- The file name is suggested (`<study> AE DLT`). Before, you typed one and
  the file was saved exactly as typed.
- A cohort or dose-level form that a study has no columns for is left out
  instead of stopping the listing (10325 and 11823 with a DSCA form).
- Problems you can fix are messages instead of tracebacks: an unsupported
  study, a ZIP that is gone or isn't an export, or a missing form.

## Peer Review Automation

One page: **SDS peer review**. Choose a Medidata **SDS (Study Design Spec)**
workbook (its `Form Definitions` and `Codelists` sheets are checked), and
optionally Rave's validation report, switch on the naming-convention checks
if you want them, choose an output folder, change the suggested file name
if you like, and Run. Every finding goes to a workbook named, by default,
after the SDS file (its name up to the first "-", usually the study):
`<that name> Peer Review Automation Output YYMMDD_HHMMSS.xlsx`, never over an
existing file.

The review is `run()` in `src/peer_review_automation/sds.py`: it takes the
files (paths or open files) and returns the workbook as an `OutputFile`,
without touching a folder.

Checks include:

- Item names longer than 32 characters.
- Fields not marked Required (excluding Label/Boolean types).
- Date fields missing the "No Future Date" flag.
- Item/Item Group names not matching their External ID.
- Codelist display types (picklist vs. other) inconsistent with the number of visible options.
- Shared vs. non-shared naming conventions (`_YS_`/`_NS_`), and codelist/unit attachments matching item names.
- Optional naming-convention checks (`CL_`/`DT_`/`NM_`/`TX_`/... prefixes, help-text `YH`/`NH` markers) via the switch.
- Optional cross-check against Rave's validation report (a CSV), with a built-in ignore list for known-acceptable error names; results land on a separate "Validation Review" sheet.

The review works without the window too:

```python
from peer_review_automation import sds

output = sds.run("STUDY01-SDS.xlsx", validation="validation.csv", check_naming=True)
with open(output.name, "wb") as file:
    file.write(output.data)
```

### What's new in 1.02

- The window is on the shared design system: one page that resizes, light
  and dark mode, a compact density, and a window that opens where it was.
  The old "Future Project" tab is gone.
- The work runs in the background and is saved in the output folder, which is
  remembered, as `<name> YYMMDD_HHMMSS.xlsx`, never over an existing file.
  Run asks for an output folder when none is chosen (it used to try to save
  in the root of the drive) or the chosen one is gone.
- The file name is suggested from the SDS file and can be changed. Before,
  the file was always named after the SDS file, with no date and time.
- A problem names the file it is about: one that is gone or can't be
  opened, a workbook without the Form Definitions or Codelists sheet, a
  validation report without its columns, or an SDS sheet without a column a
  check needs.

## Shared backend

The automation apps take what they share from `clinical_reporting` rather
than carrying their own copies:

- `clinical_reporting.workflow`:
  - `OutputFile`, what every workflow returns: a file name and the
    workbook's bytes.
  - `WorkflowInputError` for problems the user can fix, and
    `UnsupportedStudyError` for a study a workflow doesn't cover.
  - `reading_input` turns a missing, locked or unreadable input file into a
    `WorkflowInputError` that names the file. `read_corelisting` reads a
    Corelisting export through it, with
    `clinical_reporting.data.read_data_dict_zip_corelisting`.
  - `study_named_by` reads the study from a ZIP's file name, and
    `check_study` refuses a ZIP named for another study than the one chosen
    (CCI Automation).
- `clinical_reporting.filenames.output_file_name` makes the
  `<name> YYMMDD_HHMMSS.xlsx` file names.
- `clinical_reporting.data.parse_study_name` reads the study from a file
  name (Safety Automation directly; `study_named_by` builds on it).
- `clinical_reporting.export.get_named_excel_formats` provides shared Excel
  cell styles (two of the DSMB modules).

Their windows are built on the shared design system, `cci_ui` (see
[Updating the UI](#updating-the-ui)). Each workflow's `run()` is Qt-free and
returns the workbook without touching the user's folders, so it can be
scripted the same way as the reporting engine below:

```python
from cci_automation.dsmb import DSMB

output = DSMB.run("Core_Listings_15420.zip", study="15420")
with open(output.name, "wb") as file:  # "15420 DSMB Report YYMMDD_HHMMSS.xlsx"
    file.write(output.data)
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

Output columns (before renames) are named the way filters and renames refer
to them: selected common items keep their plain names, and a form's selected
items are `FORM.item` (`DM.Age`). A later form (join order 2 or higher) that
doesn't join on a selected common item puts out its own values of it under its
name too: in the example above, selecting `Visit` as a common item while VS
joins on `Subject` only gives both `Visit` (DM's values) and `VS.Visit`.
`clinical_reporting.report_columns.output_identifiers(report)` lists the
columns a report will put out, in their default order.

A filter on a common item applies to every form that has it, before the forms
are joined; a filter on `VS.Visit` applies to VS's copy only.

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
# try_load_tabular_files(paths) skips unreadable files instead of raising and
# returns (loaded, failures), both keyed by the paths as given
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

Run only the design-system and window tests:
```bash
python -m pytest -q tests/ui
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

### Testing notes

- `tests/conftest.py` inserts both project root and `src/` into `sys.path`, runs
  Qt offscreen (no windows appear), and provides one shared `qapp` fixture.
- Tests build their own made-up data in code (Clinical Reporting's
  `clinical_reporting/ui/sample_data.py`, small DataFrames, and tiny ZIPs
  written to pytest's `tmp_path`) and never read real study exports. Keep
  real exports outside the repository: Git ignores `tests/data/` and every
  `.zip`, `.csv` and Excel file so one can't be committed by accident, but
  the repository folder still syncs to Dropbox.
- Keep logic tests in `tests/unit/` (the automation workflows' `run()` tests
  are there too), Clinical Reporting's end-to-end report, settings and API
  tests in `tests/integration/`, and tests of the shared design system
  (`cci_ui`) and of whole windows in `tests/ui/`.
- Slow work (reading the ZIP and additional files, preview, export) runs on a
  background thread. Tests that wait for it use the `settle` fixture in
  `tests/ui/conftest.py`, which blocks in `TaskRunner.wait()` so the worker
  can run; a `QTest.qWait` loop holds Python's GIL and slows the worker down
  many times over. Test stand-ins without a `task_runner` run the work
  directly (`cci_ui.tasks.run_task`).
- Messages shown in the app's status labels are tagged with how serious they
  are: pass `feedback.info/success/warning/error(...)` (from
  `clinical_reporting.feedback`) to `_set_label_text`, adding the traceback as
  `details` for errors. `tests/unit/test_message_kinds.py` fails on text built
  inside those calls (literals, f-strings, joins), and the window tests in
  `tests/ui/test_clinical_reporting_tasks.py` fail on any untagged message
  shown during those tests. The status bar repeats the latest message, and a
  success or error shown on a page other than the open one also pops up as a
  toast.
- The sidebar's badges and the status bar summary refresh when control
  returns to the event loop; window tests call
  `QApplication.processEvents()` before checking them.
- The tests that guard the look and the pages (the tokens against the
  mockup, no stray windows, the widget contract, resizing) are described in
  [Updating the UI](#updating-the-ui).

## Updating the UI

The design system is `src/cci_ui`: the colors, sizes and type (`theme/`),
the components (`widgets/`), the icons, and the four tools' app icons. The
Clinical Reporting pages are built from it in
`src/clinical_reporting/ui/pages/`, in Python code (no Qt Designer files).
Safety Automation, Peer Review Automation and CCI Automation are built on it
too.

### Colors, sizes, and type

Edit `src/cci_ui/theme/tokens.py`: the light and dark colors, the
Comfortable and Compact sizes, the type scale. The stylesheet is generated
from it (`theme/qss.py`). The values match the approved mockup in
`docs/design/clinical-reporting-mockup.html`, and
`tests/ui/test_theme_tokens.py` keeps them in step: change both together.
Check the result in the gallery (below), in both schemes and densities.

### Components

Each component is a module in `src/cci_ui/widgets/` (buttons, sections,
pages, the sidebar, banners, ...). A new module goes in the import list in
`widgets/__init__.py` (that registers its stylesheet rules) and on a gallery
page (that puts it under `tests/ui/test_no_stray_windows.py`, which fails
if building one opens a stray window). Show or hide a child widget only once
it has a parent; the package docstring explains why.

The small tools are built from two pieces. `cci_ui.tool_window.ToolWindow` is
the window (the shell, a task runner behind the busy overlay; `run_tool`
starts the app and remembers the window's size). `WorkflowPage`
(`widgets/workflow_page.py`) is one workflow's page: the tool's input rows,
the output folder, a file name with the name it will save, a banner, and Run.
The tool hands `WorkflowPage.start` a job that returns the workbook; the page
runs it in the background and saves it (`cci_ui.files.save_output`). The
core side of a workflow uses `clinical_reporting.workflow` (see
[Shared backend](#shared-backend)); the page shows the errors whose types the
tool lists in `expected_errors` as warnings.

Every tool's window reopens at the size and position it had when it was
closed (`cci_ui.window_state.WindowState.remember`); the two with a sidebar
(Clinical Reporting and CCI Automation) also keep it as wide (and collapsed
or not) as it was.

A new icon is a Lucide SVG copied into `src/cci_ui/assets/icons/` (from the
version in `assets/icons/VERSION`) and a constant in `IconName`
(`cci_ui/icons.py`); `tests/ui/test_icons.py` checks that every file has a
name and every name a file.

### Checking the look: the gallery

The shared design system (`src/cci_ui`) has a gallery window showing every
component: colors (with contrast), type, icons, buttons, inputs, toggles and
segmented controls, sections, lists, tables, the side panel, the workflow
page of the small tools, banners, toasts, the status bar, the busy overlay,
and empty states.

```bash
python -m cci_ui.gallery                               # open it
python -m cci_ui.gallery --theme dark --density compact --size 1000x620
python -m cci_ui.gallery --screenshot shots            # every page, light and dark
```

`--screenshot` runs without opening a window and saves one PNG per page and
scheme (only the `--page` given, if any), which makes it easy to review a
change to `cci_ui/theme/tokens.py` or a component. The gallery never changes
the appearance saved for the real tools.

### Clinical Reporting pages

The Clinical Reporting window's pages are built in Python code, one module
per step in `src/clinical_reporting/ui/pages/`; `ui/main_ui.py` lists them in
step order (`PAGE_CLASSES`) and puts them in the shell: a sidebar of steps
(an icon strip on narrow windows), a header, and a status bar. Each step's
sidebar badge (a count, done, optional, or a problem) comes from
`clinical_reporting/steps.py`, which works it out from the report without
Qt; problems are mapped to the step that fixes them by validation issue
code. The steps' titles are there too (`TITLES`), and so is the list of
steps that need data (`NEEDS_DATA`): their pages show "No data loaded" and a
Choose ZIP… button until some is loaded. The preview tool opens the real
window on made-up DEMO01 data (never a real study), with forms, items,
joins, a filter, and a comparison already chosen:

```bash
python -m clinical_reporting.ui.preview                          # open it
python -m clinical_reporting.ui.preview joins --theme dark --size 1920x1001
python -m clinical_reporting.ui.preview all --screenshot shots --size 1000x620,1920x1001
python -m clinical_reporting.ui.preview --help                   # page names, options
```

`--empty` starts without data. Like the gallery, it never changes the saved
appearance. (The sample isn't a real ZIP, so turning the cut-off date on
shows a read error.)

- **Change a page:** edit its module in `ui/pages/`, then check it with the
  preview tool.
- **Give the behavior mixins a new widget:** they reach widgets as
  `self.ui.<name>`, so add the widget to its page and its name to that page's
  `EXPORTS`.
- **Add or reorder a step:** add its key to `STEP_KEYS` (and its title to
  `TITLES`) in `clinical_reporting/steps.py`, and a page class (with that
  `KEY`, a `SECTION`, `ICON`, and `EXPORTS`) to `PAGE_CLASSES`, in the same
  order.
- **Show a message on a page:** give it a `StatusBanner` and set it with
  `_set_label_text(banner, feedback.<kind>(...))`. The status bar repeats it
  (and a toast, when it is a success or error on another page), unless the
  banner is made with `announce=False` because it describes the page's
  current state, like the Joins banner.
- **Add a shortcut to a page:** `page.add_shortcut(keys, action)`; it works
  while the page's content is shown (not on another page, not in its empty
  state). For a button pass its `click`, which does nothing while the button
  is disabled.
- **Change the report from a new place:** call `self._report_changed()`
  afterwards, so the sidebar badges and the status bar follow. A new
  validation issue code needs a step in `steps.ISSUE_STEPS` (or a place in
  `FILTER_ITEM_ISSUE_CODES`, placed by the issue's field, or in
  `UNPLACED_ISSUE_CODES`); `tests/unit/test_steps.py` fails until it has one.

Then run `python -m pytest -q tests/ui`. Among those tests,
`test_ui_contract.py` checks that the mixins and the pages agree on widget
names and that the pages follow `STEP_KEYS`, `test_resize_behavior.py` that
no control stretches at the target window sizes (and that the sidebar and
the Preview panel rearrange on narrow windows), and `test_preview_tool.py`
pins the step order (update it when you reorder steps).

### App icons

Each tool's icon is a white line icon on a rounded square of the tool's
color: `APP_ICONS` in `src/cci_ui/app_icons.py`. The `.ico` files in
`src/cci_ui/assets/app-icons/` are drawn from it; after changing it, draw
them again and commit them:

```bash
python -m cci_ui.app_icons
```

The builds use them as the executables' icons (`build_support.app_icon`).
`create_app`, which every tool starts with (the small tools through
`run_tool`), uses the tool's icon as the window icon.

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
  session.py                   # what happens to a report when the user acts; build/export
  settings_store.py            # where saved settings live (local folder today)
  feedback.py                  # status messages tagged info/success/warning/error
  filenames.py                 # safe file names; "<name> YYMMDD_HHMMSS.xlsx" outputs
  pipeline.py                  # joins, filters, ordering, renames, formatting
  report_columns.py            # the output columns and their names, before running
  workflow.py                  # the tools' workflows: OutputFile, input errors, reading inputs
  validation.py                # executable-report validation; "Cannot run" messages
  steps.py                     # the steps: titles, badges, and what they say
  data.py                      # Corelisting ZIP, CSV, Excel, extra inputs (paths or uploads)
  export.py                    # xlsx/csv/bytes rendering
  telemetry.py                 # reports saves to the usage counter (off unless configured)
  ui/                          # PySide6 desktop front end
    app.py                     # entry point: starts the app and opens the window
    window.py                  # main window composed from feature mixins
    controller.py              # puts the behavior classes' methods on the window
    main_ui.py                 # builds the pages into the window's shell
    navigation.py              # page changes; badges, header, status bar, toasts
    contract.py                # widget names the mixins may use
    pages/                     # one module per step, built in code
    preview.py                 # python -m clinical_reporting.ui.preview
    sample_data.py             # made-up DEMO01 data for previews and UI tests
    base.py                    # helpers shared by the behavior mixins
    settings_tab.py            # inputs, cutoff, and saved settings
    additional_input_tab.py    # extra CSV/Excel inputs, form and column renames
    selection_tabs.py          # forms, common items, and form items
    filters_tab.py             # static and dynamic filters
    join_config.py             # join order, type, and items
    ordering_tab.py            # output order and renames
    run_save_tab.py            # preview, run, and save
    dialogs.py                 # dialogs shared by more than one page
    table_actions.py           # original-name/new-name tables (renames)
    preview_model.py           # Qt table model for the preview grid

src/cci_ui/                    # shared design system for all four tools
  app.py                       # create_app(): style, font, theme, error dialog
  assets.py                    # finds bundled files from source or a built exe
  icons.py                     # icon(IconName.X): icons drawn in theme colors
  theme/tokens.py              # colors, sizes, type scale (no Qt; also exports CSS)
  theme/qss.py                 # stylesheet built from the tokens (no Qt)
  theme/palette.py             # Qt palette built from the tokens
  theme/fonts.py               # loads the bundled Inter font
  theme/glyphs.py              # renders icons; writes the stylesheet's arrow/tick images
  theme/manager.py             # System/Light/Dark and density, shared by all tools
  widgets/buttons.py           # make_button/icon_button: primary, secondary, plain…
  widgets/labels.py            # type-scale labels; ElidedLabel shortens long paths
  widgets/section.py           # Section: titled card of label/field rows
  widgets/page.py              # Page: title, body, footer, empty state; form/workspace/split
  widgets/responsive.py        # breakpoints; panel beside or below the main area
  widgets/path_picker.py       # PathPicker: path + Choose… + Remove
  widgets/side_panel.py        # SidePanel: sections beside a grid, or below it
  widgets/toggle.py            # ToggleSwitch (a QCheckBox drawn as a switch)
  widgets/segmented.py         # SegmentedControl
  widgets/display.py           # Display button + popover (appearance, density)
  widgets/search.py            # SearchField
  widgets/views.py             # lists/tables with placeholder text; EmptyState
  widgets/status.py            # StatusBanner, show_toast, show_error
  widgets/busy.py              # BusyOverlay (blocks input; spinner after 150 ms)
  widgets/tables.py            # column rules, density rows, table_card, TableToolbar
  widgets/dual_list.py         # DualListPicker (available ⇄ selected lists)
  widgets/sidebar.py           # Sidebar with status badges; collapses to icons
  widgets/shell.py             # AppShell: sidebar, header, pages, status bar, busy overlay
  widgets/workflow_page.py     # WorkflowPage: a small tool's inputs, output, and Run
  tool_window.py               # ToolWindow, show_tool, run_tool: a small tool's window
  files.py                     # save_output: a workflow's workbook into the chosen folder
  window_state.py              # remembered window size/position and sidebar per tool
  tasks.py                     # run_task/TaskRunner: slow work off the GUI thread
  gallery.py                   # python -m cci_ui.gallery (every component)
  app_icons.py                 # the tools' app icons (python -m cci_ui.app_icons)
  assets/fonts/                # Inter 4.1 (SIL Open Font License)
  assets/icons/                # Lucide 1.49.0 line icons used by the apps (ISC)
  assets/app-icons/            # each tool's .ico, drawn by app_icons.py

src/cci_automation/            # Enrollment Log, DSMB, format tools
  __main__.py                  # runtime entry: python -m cci_automation
  app.py                       # the window: a sidebar of three WorkflowPages
  util.py                      # shared stats, Corelisting and formatting helpers
  enrollment_log/  dsmb/  format_tools/  # each workflow's run(), Qt-free

src/safety_automation/         # Corelisting AE & DLT report
  __main__.py                  # runtime entry: python -m safety_automation
  app.py                       # the window: one WorkflowPage
  util.py                      # study name and dose level helpers
  ae_corelisting/AECoreListing.py  # run(): the AE & DLT workbook, Qt-free

src/peer_review_automation/    # Medidata SDS peer review
  __main__.py                  # runtime entry: python -m peer_review_automation
  app.py                       # the window: one WorkflowPage
  sds.py                       # run(): the review workbook, Qt-free

tests/
  unit/                        # fast logic-focused tests
  integration/                 # Clinical Reporting end-to-end report/settings/API tests
  ui/                          # design-system and whole-window tests

docs/design/clinical-reporting-mockup.html  # the approved mockup the design follows
*.spec, build_support.py       # PyInstaller builds (see Building the Executables)
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
exclude PyQt5/matplotlib. Each gets its tool's icon (see
[App icons](#app-icons)) and the design system's fonts and icons.

If the repository is in a Dropbox folder, mark `build/` and `dist/` as
ignored by Dropbox first (once per clone and machine), or Dropbox locks the
new executable while PyInstaller writes its icon and version resources and
the build fails with `EndUpdateResourceW`:

```powershell
New-Item -ItemType Directory -Force build, dist | Out-Null
Set-Content -Path build -Stream com.dropbox.ignored -Value 1
Set-Content -Path dist -Stream com.dropbox.ignored -Value 1
```

To check a build without clicking through it, run it with
`CCI_UI_SELFTEST` set to a file path: the app starts, writes what it loaded
(style, font, assets, window icon, and, for Clinical Reporting, whether it
has its bundled `telemetry.json`) to that file as JSON, and quits with exit
code 0 (1 if a check failed; the report then says why under `error`):

```powershell
$env:CCI_UI_SELFTEST = "$PWD\dist\selftest.json"
$exe = Get-Item ".\dist\CCI Clinical Reporting V*.exe" | Sort-Object LastWriteTime | Select-Object -Last 1
Remove-Item .\dist\selftest.json -ErrorAction SilentlyContinue
$run = Start-Process -FilePath $exe -Wait -PassThru
Remove-Item Env:CCI_UI_SELFTEST
$run.ExitCode; Get-Content .\dist\selftest.json
```

(The other three tools do this too.)

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
__version__ = "2.11"
```

`build_support.py` reads it and stamps it into both the executable's file
name (`CCI Automation V<version>.exe`) and its Windows VERSIONINFO resource, so
the version shown in Explorer under **Properties -> Details** can never drift
from the version in the file name. The running app can also report its own
version via `<package>.__version__`.

For a one-off build without editing the source, override with an environment
variable:

```powershell
$env:APP_VERSION = "1.26-test"; python -m PyInstaller "CCI Automation.spec"
Remove-Item Env:APP_VERSION  # or every later build gets 1.26-test too
```

```bash
APP_VERSION=1.26-test python -m PyInstaller "CCI Automation.spec"
```

A suffix such as `-test` shows in the file name and as the Product version in
Properties -> Details; the File version there uses only the digits
(1.26.0.0).

Configuration bundled at build time:

- **CCI Clinical Reporting** embeds `src/clinical_reporting/telemetry.json`
  (ignored by Git; it must exist locally before building) so usage counting
  works without environment variables; use `telemetry.example.json` as the
  schema when creating or rotating it. Its token can only add counts, not
  read them.
- CCI Automation, Safety Automation and Peer Review Automation need no
  bundled data files.

Note: the `.spec` files and `build_support.py` are tracked in Git like any
other source file — `.gitignore` no longer ignores `*.spec`. A spec diff now
always means a real change to the build recipe, never a version bump.

## Notes
- Every window is laid out with Qt layouts, so its controls follow the
  window's size; Clinical Reporting's resize tests are described in
  [Updating the UI](#updating-the-ui).
- Avoid modifying generated `build/` and `dist/` artifacts in normal
  development workflows.
