# Clinical Reporting Tool

The suite's configurable report builder. Users pick source forms, choose
common items or form items, set joins, filters, and comparisons, preview the
result, and export it, keeping the choices as a saved setting to reuse. The
package is also the suite's Qt-free backend: the automation tools build on its
[shared modules](../../README.md#shared-backend).

Run it from the repository root once the environment is
[set up](../../README.md#setup):

```bash
python -m clinical_reporting
```

## Using it

- Use a Corelisting export plus additional inputs (Excel or CSV files).
- Form, common item, and form item pickers with regex-based case-insensitive
  search filters.
- Join, rename, comparison, and filter configuration tables tailored for
  clinical datasets.
- Save/load settings plus quick run helpers for generating reports.
- Form names cannot include `.` because it is reserved for the form/item
  separator. Additional inputs default to the file name and must be renamed
  to remove dots.
- A saved setting also keeps the form and column names given to its
  additional input files. On the Additional input page, each file you add
  has a Saved names dropdown: greyed out with None until you load a setting
  that has such names (and again once it is forgotten, by a new ZIP for
  example), then listing them by form name, or by file name for names that
  only rename columns (hover an entry to see the file it was saved for).
  - A file with the same name (from any folder), or else the same column
    headers, gets its names picked and filled in, as long as the match is
    unambiguous.
  - Check the names, or pick another entry or None, then click Apply to
    report; the setting's selections on those forms come back.
  - Names you typed yourself are never replaced by a pick, nor cleared by
    picking None.
  - A "Still to add" banner on Additional input lists the setting's files
    that aren't added yet. When the setting is loaded, its "Missing forms"
    warning on Source data says which files to add, or which added files to
    check and apply.
  - Saved column names a file can't use, because its export renamed or
    dropped the column, are ignored and never stop Apply to report. The
    message after the pick, a standing banner, and the Apply result list
    them ("lab.csv has no Visit Dt"); renaming a column to the saved name
    by hand clears them.
- On the Stacked forms page, put the rows of two or more loaded forms
  (Corelisting forms or applied additional inputs, never another stacked
  form) one under another as a new form. It then goes through every later
  step like any form; its members stay usable on their own.
  - An item every member has under the same name is stacked by itself; any
    other item is left out unless you match it. A match lines up left-out
    items from different members (Event Date with Collection Date), or keeps
    a single one, under one of their names or a new one.
  - Each member's cell in a matched row is a dropdown: "—" (gives nothing),
    its current item, then its left-out items, names like the match's first
    (type to filter). Items of one name move together: picking one brings in
    every member's item of that name, and clearing one takes them all back
    to Left out. A match left with no item goes.
  - Apply to report adds the stacked forms. A saved setting keeps the applied
    ones and rebuilds them whenever the data is loaded or changes (a new ZIP
    starts a new report, so apply them again). A member or matched item the
    data lacks is warned about. A stacked form named like a loaded form, or a
    match that later data makes ambiguous (a member with two of its items, a
    match named like an item every member now has), stops the export until it
    is fixed on the page.
- The steps sit in a sidebar with status badges. Reading the ZIP, building
  the preview, and exporting run in the background, and a ZIP or additional
  file that can't be read, or clashing form names, are explained on the page.
- Headless reporting engine that can be driven programmatically without the
  UI, so the same logic can be reused in scripts, batch jobs, and tool chains.
  See [Programmatic / API usage](#programmatic--api-usage).

Keyboard shortcuts:

| Keys | Does |
|---|---|
| Ctrl+Tab / Ctrl+PgDown, Ctrl+Shift+Tab / Ctrl+PgUp | Next / previous step |
| Ctrl+\\ | Show or hide the sidebar |
| Ctrl+F | Search (Forms, Common items, Form items, Stacked forms, Order & rename) |
| F5 | Build the preview again (Preview & export) |
| Ctrl+E | Export to Excel (Preview & export) |
| Ctrl+S | Save the setting (Preview & export) |

## Programmatic / API usage

The reporting engine is decoupled from the PySide6 UI, so it can be driven
directly from another Python program (scripts, batch jobs, tool chains, or a
future service layer). The UI is just one client of the same core engine.

The pipeline has four headless building blocks:

| Step | Module | What it does |
| --- | --- | --- |
| Load data | `clinical_reporting.data` | Read a Corelisting ZIP / CSV / Excel into a `{form_name: DataFrame}` dict and shape additional inputs. |
| Configure | `clinical_reporting.models.ReportConfig` | A typed wrapper over the same settings JSON the UI saves/loads. |
| Run | `clinical_reporting.report.CLReport` | Apply the saved setting to the data and execute `create_report()`. |
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

# 2. Apply a saved setting from the UI (load + reconcile in one call)
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

`set_data()` must be called before `apply_config()` so the saved setting can be
reconciled against the columns actually present. `apply_config()` returns a
`{"forms": [...], "items": [...]}` report of anything dropped because the
current data no longer supports it — the same information the UI shows as a
warning label.

### Building a saved setting in code

Any `.json` saved from the UI is a valid saved setting, but you can also
build one in memory using the same schema:

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

> Note: form items only exist when more than one form is loaded. With a
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

# Combine a Corelisting ZIP with additional inputs (CSV/Excel files)
base = read_data_dict_zip_corelisting("study_export.zip")
inputs = load_additional_inputs(["labs.csv"])  # {resolved_path: DataFrame}
# try_load_tabular_files(paths) skips unreadable files instead of raising and
# returns (loaded, failures), both keyed by the paths as given
form_names = {path: "LABS" for path in inputs}  # path -> form name
column_names = {}  # (path, original_col) -> new name
extra = build_additional_data_map(inputs, form_names, column_names)
report.set_data({**base, **extra})

# Keep those names with a setting, and reuse them for next month's files
from clinical_reporting.additional_names import (
    add_to_settings,
    from_settings,
    ignored_names,
    match,
    names_from,
)
from clinical_reporting.data import named_columns

settings = add_to_settings(
    report.settings_to_dict("monthly"), inputs, form_names, column_names
)
saved = from_settings(settings)  # [] for settings saved without names
next_inputs = load_additional_inputs(["2026-10/LABS.csv"])
files = {path: named_columns(df) for path, df in next_inputs.items()}
for path, found in match(saved, files).items():  # by file name, then columns
    given = names_from(saved[found.index], files[path])
    # given.form_name, given.column_names ({original: new})
    lost = ignored_names(saved[found.index], path, files[path], given.column_names)
    # [IgnoredName(file_name, column, new_name)]: saved names it can't use

# Export options
write_csv(df, "report.csv")  # CSV on disk
xlsx_bytes = dataframe_to_xlsx_bytes(df)  # in-memory bytes (e.g. stream over HTTP)
```

### Stacked forms

```python
from clinical_reporting.stacking import (
    Match,
    StackedForm,
    layout,
    match_choices,
    set_match_item,
)

visits = StackedForm(
    "VISITS",
    members=("SV", "DSSVLTFU"),
    matches=(Match("Visit Name", {"SV": "Event Group Name", "DSSVLTFU": "Event Label"}),),
)
report.set_stacked_forms([visits])  # rebuilds report.data; VISITS is a form now
lined_up = layout(visits, report.loaded_data)  # every / matched / left_out, item order
# What SV's cell in the first match offers, then SV giving Visit Status instead.
choices = match_choices(lined_up, report.loaded_data, 0, "SV")
visits = set_match_item(visits, report.loaded_data, 0, "SV", "Visit Status")
```

`report.loaded_data` keeps the forms as loaded; `report.data` adds the stacked
forms built from them, again whenever `set_data` runs.
`clinical_reporting.session.apply_stacked_forms(report, stacked_forms)` does
the same while keeping the selections that still exist. `report.stacked_build`
says what building them found: stacked forms not built because a loaded form
has their name (also the validation issue `stacked_form_name_clash`, which
`create_report()` refuses); matches the data makes ambiguous since they were
applied (`conflicts`, the validation issue `stacked_form_conflict`, refused
the same way); and members or matched items the data lacks or replaces
(`reconcile_with_current_data()` reports those as missing forms and items).

### Persisting a saved setting

A saved setting built in code can be written back to the same JSON the
UI reads, so headless runs and the UI stay interchangeable:

```python
report.save_setting_to_json("my_setting.json", setting_name="batch-run")
# or, from a ReportConfig:
config.to_settings_json("my_setting.json")
```

The settings dictionary can also go to a folder of saved settings (the store
the desktop app uses), or become the saved JSON text without any file:

```python
from clinical_reporting.settings_store import (
    LocalFolderStore,
    settings_from_json,
    settings_to_json,
)

settings = report.settings_to_dict("batch-run")
LocalFolderStore("C:/Reports/settings").save("batch-run", settings)
text = settings_to_json(settings)  # the exact text a saved setting file holds
assert settings_from_json(text) == settings
```

A setting saved from the desktop app may also hold `additional_input_names`:
the form and column names given to its additional input files, by file name
and original column headers, never by folder
(`clinical_reporting.additional_names`). The key is optional and compatible
both ways. Settings saved without it load as before, and versions before 2.11
ignore it, as they ignore any key they don't know. Re-saving such a setting
in an older version drops the names. A damaged entry is skipped and logged;
the rest of the setting still loads. Saving keeps the names of the files
listed at the time, as the Additional input page shows them: re-saving a
setting in a run without some of its files drops their names, just as the
forms those files would bring drop out of the setting.

It may also hold `stacked_forms`: the stacked forms applied to the report,
each with its name, members and matches, a match keeping the item each member
gave it (`clinical_reporting.stacking`). Only applied stacked forms are saved;
the key is written only when there are some, so other settings save exactly as
before. Loading a setting rebuilds its stacked forms before reading its
selections. Versions without stacked forms ignore the key: a setting that
selects a stacked form reports it as a missing form there, and re-saving it
there drops the stacked forms. A damaged entry is skipped and logged.

The column order is `selected_items_order_list`, with `order_list_customized`
set once the Order & rename page changed it (a setting saved before the flag
existed counts as customized when it has an order). A setting may also keep
an order in `order_list`, a key versions before 2.15 read first. That order
is used unless the setting's own order is customized. New saves don't write
`order_list`; older versions, finding none, use `selected_items_order_list`.

## Usage telemetry

Saving a report or a setting is reported to a usage counter, silently and in
the background (`telemetry.py`); a failed delivery never affects the save.
Counting is off unless an endpoint and a token are configured, either by the
environment variables `CLINICAL_REPORTING_RUN_COUNTER_URL` and
`CLINICAL_REPORTING_RUN_COUNTER_TOKEN` (these win) or by
`src/clinical_reporting/telemetry.json`.

The release build embeds `telemetry.json` (ignored by Git; it must exist
locally before building) so usage counting works without environment
variables; use `telemetry.example.json` as the schema when creating or
rotating it. Its token can only add counts, not read them.

## Changing the UI

The window is built on the shared design system,
[`cci_ui`](../cci_ui/README.md), in Python code (no Qt Designer files). Its
pages are one module per step in `src/clinical_reporting/ui/pages/`, each
holding the page's widgets and its behavior (the mixin the window inherits);
`ui/main_ui.py` lists them in step order (`PAGE_CLASSES`) and puts them in the
shell: a sidebar of steps (an icon strip on narrow windows), a header, and a
status bar. Each step's sidebar badge (a count, done, optional, or a problem)
comes from `clinical_reporting/steps.py`, which works it out from the report
without Qt; problems are mapped to the step that fixes them by validation
issue code. The steps' titles are there too (`TITLES`), and so is the list of
steps that need data (`NEEDS_DATA`): their pages show "No data loaded" and a
Choose ZIP… button until some is loaded.

The preview tool opens the real window on made-up DEMO01 data (never a real
study), with forms, items, joins, a filter, and a comparison already chosen:

```bash
python -m clinical_reporting.ui.preview                          # open it
python -m clinical_reporting.ui.preview joins --theme dark --size 1920x1001
python -m clinical_reporting.ui.preview all --screenshot shots --size 1000x620,1920x1001
python -m clinical_reporting.ui.preview --help                   # page names, options
```

`--empty` starts without data. Like the design system's
[gallery](../cci_ui/README.md#checking-the-look-the-gallery), it never changes
the saved appearance. (The sample isn't a real ZIP, so turning the cut-off
date on shows a read error.)

- **Change a page:** edit its module in `ui/pages/`, which holds both its
  widgets and its behavior, then check it with the preview tool.
- **Give a page's behavior mixin a new widget:** the mixins reach widgets as
  `self.ui.<name>`, so add the widget to the page and its name to that page's
  `EXPORTS`: both are in the page's module, so it is a one-module edit.
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
the Preview panel rearrange on narrow windows, and that long paths in the
panel's messages wrap instead of widening it), and `test_preview_tool.py`
pins the step order (update it when you reorder steps).

## Testing notes

The suite-wide testing setup is in the
[root README](../../README.md#testing-and-linting). For Clinical Reporting:

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

## Package layout

Everything except `__main__.py` and `ui/` is Qt-free (see
[Qt-free core](../../README.md#qt-free-core-thin-front-ends)).

```text
src/clinical_reporting/
  __main__.py                  # runtime entry: python -m clinical_reporting
  models.py                    # forms, ReportConfig, labels, identifiers
  report.py                    # report state, persistence, reconciliation
  session.py                   # what happens to a report when the user acts; build/export
  settings_store.py            # saved settings as JSON files in a folder; their JSON text
  feedback.py                  # status messages tagged info/success/warning/error
  filenames.py                 # safe file names; "<name> YYMMDD_HHMMSS.xlsx" outputs
  pipeline.py                  # joins, filters, ordering, renames, formatting
  report_columns.py            # the output columns and their names, before running
  workflow.py                  # the tools' workflows: OutputFile, input errors, reading inputs
  validation.py                # executable-report validation; "Cannot run" messages
  steps.py                     # the steps: titles, badges, and what they say
  data.py                      # Corelisting ZIP, CSV, Excel, additional inputs (paths or uploads)
  additional_names.py          # additional inputs' form/column names kept with a saved setting
  stacking.py                  # stacked forms: how they line up, building them, their settings key
  export.py                    # xlsx/csv/bytes rendering
  telemetry.py                 # reports saves to the usage counter (off unless configured)
  ui/                          # PySide6 desktop front end
    app.py                     # entry point: starts the app and opens the window
    window.py                  # QMainWindow plus the behavior mixins
    main_ui.py                 # builds the pages into the window's shell
    navigation.py              # page changes; badges, header, status bar, toasts
    pages/                     # one module per step: its widgets and behavior mixin
      source_data.py           # Corelisting ZIP, cut-off date, and saved settings
      additional_input.py      # additional inputs, form and column names, saved names
      stacked_forms.py         # stacked forms: members, matches, and Apply
      selection.py             # forms, common items, and form items
      filters.py               # filters and comparisons
      joins.py                 # join order, type, and items
      order_rename.py          # output order and renames
      preview_export.py        # preview, export, and save a setting
      _common.py               # the table helper the pages share
    preview.py                 # python -m clinical_reporting.ui.preview
    sample_data.py             # made-up DEMO01 data for previews and UI tests
    base.py                    # window-level mixin: shared state, refresh coordinators, helpers
    dialogs.py                 # dialogs shared by more than one page
    table_actions.py           # original-name/new-name tables (renames)
    preview_model.py           # Qt table model for the preview grid
```
