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
  - The Joins table lists the selected forms in join order: the first
    starts the report, each one below joins it on Item 1–3. Select a form,
    then Move up or Move down to change its place. A newly selected form
    goes last and joins on Subject with a left join; a form moved out of
    first place joins on Subject.
  - The Joins step keeps every form's joins tidy, a loaded setting's
    included: the forms are ranked by join order (one that isn't a number
    counts as 1; tied orders keep the selection order) and numbered 1 to the
    number of selected forms; the first joins on nothing, with a left join;
    any other form joins on at most three items, its first three, keeping
    only selected common items, each once; an unknown join type becomes a
    left join.
- Every step marks each problem on the field or cell that fixes it: a red
  border (and red text when it has text), the reason as its tooltip, and a
  red badge on the step. A missing value is red as soon as its field is
  there (a new filter row shows its empty Item and Value red); a wrong one
  as it is typed. While any step has a problem, the report can't be
  previewed or exported (Preview & export says which steps to fix). A filter
  whose operator needs a value needs one, in the window and in
  `build_base_report` alike.
- Additional input, Stacked forms and Coalesced items (the Data steps) have
  no Apply button: their changes reach the report when you go to another
  step. A Data step with a problem is held: nothing from it reaches the
  report until it is fixed, and Save setting waits, since its changes would
  be lost. Changes made while the step isn't open (files that finish loading
  after you left, names a picked setting fills in, a new Corelisting ZIP)
  reach the report right away. On Additional input, so do the files once
  every file the loaded saved setting needs is added and no New name is red,
  without leaving the step: the change that makes it so (adding the last
  file, picking its Saved names, typing the last red name, removing the file
  with it) brings them in, and later changes wait until you leave.
- Removing an input takes along what it leaves with nothing to be made from:
  removing the Corelisting ZIP drops the stacked forms all of whose members
  are its forms, and the coalesced items of its forms or of those stacked
  forms (`session.without_removed_forms`). Once no input is left at all (no
  ZIP and no additional files), every stacked form and coalesced item goes
  at once, from the pages and the report.
- Save/load settings plus quick run helpers for generating reports.
- An export needs a file name: Export to Excel waits, and File name is red,
  until one is typed. The date and time of the export are added to the name
  unless Add the date and time is unticked, which saves each export as
  `<name>.xlsx`. Exporting over a file that's already there asks first
  (Replace or Cancel); a file open in Excel can't be written, and the message
  says to close it.
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
  - Check the names, or pick another entry or None; when they reach the
    report, the setting's selections on those forms come back.
  - Names you typed yourself are never replaced by a pick, nor cleared by
    picking None.
  - A "Still to add" banner on Additional input lists the setting's files
    that aren't added yet. When the setting is loaded, its "Missing forms"
    warning on Source data says which files to add, or which added files to
    check. Once the last of them is added (and no New name is red), the
    files reach the report at once, and the setting's selections on their
    forms come back.
  - Saved column names a file can't use, because its export renamed or
    dropped the column, are ignored and never stop the file's form from
    being added. The message after the pick, a standing banner, and the
    result list them ("lab.csv has no Visit Dt"); renaming a column to the saved name
    by hand clears them.
- A saved setting also keeps the export's File name and Add the date and
  time. Picking the setting on Source data fills them in on Preview & export;
  picking one saved without a file name (every setting saved before 2.21)
  clears File name and ticks the box, so a name has to be typed before
  exporting. Applying the setting again later, once its additional files are
  added, leaves them as they are.
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
  - The grid's columns fit their names (the first up to 45% of the grid),
    and the grid scrolls sideways when they don't fit. Drag any column edge
    to resize it, or double-click it to fit it again; a dragged width holds
    until the app closes.
  - A stacked form's Name, Members, match names and matched cells turn red
    with what they lack (no name, fewer than two members, a taken name, a
    member giving two of a match's items), the reason as their tooltip.
  - The stacked forms reach the report when you go to another step. A saved
    setting keeps them and rebuilds them whenever the data is loaded or
    changes (a new ZIP brings them along). A member or matched item the
    data lacks is warned about; a loaded setting's "Missing forms" warning
    also names the members that aren't loaded, whether the stacked form is
    built or not (one named like a loaded form names none). A stacked form
    named like a loaded form, or a match that later data makes ambiguous (a
    member with two of its items, a match named like an item every member now
    has), stops the export until it is fixed on the page.
- On the Coalesced items page, make one item from two or more items of one
  form (a Corelisting form, an applied additional input or an applied
  stacked form) whose values exclude each other, such as Race and Race Other
  Specify. It then goes through every later step like any item.
  - The first item gives each row's value. Each later item fills it where
    the value so far is empty (an empty cell, or only spaces) or meets that
    item's condition: a Filters operator and value, tested on the value so
    far (`= Other` lets Race Other Specify replace an Other). A value nothing
    fills stays. With three items, the third fills what the first two gave.
  - The coalesced item takes one of its items' names or a new one and sits
    where its first item was; its items leave the form. An item is in one
    coalesced item at most. With two or more forms loaded, a common item can
    only be coalesced under its own name, so the forms still join on it.
  - A row overlaps where the value so far is neither empty nor meeting the
    later item's condition, and that item has a value too: one of the two
    would be lost. Overlaps are a problem (the later item's Rows cell and
    When values overlap turn red, naming the first rows) unless When values
    overlap is set to Keep the earlier value. As you edit, the page shows how
    the form's rows take their value, and marks each problem on its field.
  - The coalesced items reach the report when you go to another step, made
    after the stacked forms: a member's coalesced item doesn't reach its
    stacked form (coalesce the stacked form itself). A saved setting keeps
    them and rebuilds them whenever the data is loaded or changes (a new ZIP
    brings them along). A form or item the data lacks is warned
    about, and the coalesced item is built from the items left; an overlap
    later data brings to one that refuses them, or its name now given to
    another item of its form, stops the export until it is fixed on the page.
- The "?" button at the top right, left of the ◐ Display button, opens help
  beside the pages for the open step: what it is for, how to use it step by
  step, and what is good to know (on Source data, also the keyboard
  shortcuts that work on every step). It follows the step you open; drag its
  edge to make it wider. It always starts closed.
- The steps sit in a sidebar with status badges. On a narrow window, and in
  Compact density until you open it (Ctrl+\\), the sidebar is an icon strip
  with each step's count or mark beside its icon; each density remembers
  whether you left it open. Reading the ZIP, building the preview, and
  exporting run in the background, and a ZIP or additional file that can't
  be read, or clashing form names, are explained on the page.
- In every table, a pencil after a column's name marks the columns you can
  change. A name or value you type opens on one click (the pointer turns into
  a text cursor over it); one that doesn't apply, such as the Value of a
  filter whose operator takes none, is grey.
- A base report (a saved setting run on a Corelisting export) can be built
  without the window, giving the workbook the desktop exports byte for byte
  (but for its creation time), so automations, the web version and scripts
  reuse the same logic. See [Programmatic / API usage](#programmatic--api-usage).

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
directly from another Python program (an automation, a batch job, or the web
version). The UI is just one client of the same core engine, and none of the
modules below imports Qt.

### The base report

A base report is a saved setting run on a Corelisting export: the table the
desktop app exports for the same inputs ([GLOSSARY](../../GLOSSARY.md)).
Build it with `clinical_reporting.build_base_report`:

```python
from datetime import date
from pathlib import Path

import clinical_reporting

base = clinical_reporting.build_base_report(
    "Core_Listings_DEMO01_20261001.zip",  # a path, or an open binary file
    "settings/monthly_ae_review.json",  # a saved setting's file, or its dict
    cut_off_date=date(2026, 9, 30),  # optional, as on Source data
    additional_inputs=["lab_results.csv"],  # optional, by their saved names
)
base.setting_name  # "monthly AE review" (its file's stem when it has no name)
base.file_name  # "DEMO01 AE review": the file name the setting keeps ("" if none)
base.add_date_time  # True unless the setting keeps Add the date and time unticked
base.table  # the report's rows: a pandas DataFrame, columns as exported
base.warnings  # what the desktop would warn about; () when nothing
base.table.groupby("Site").size()  # an automation builds on the table

workbook = base.to_workbook()  # an OutputFile: .name and .data (bytes)
Path(workbook.name).write_bytes(workbook.data)
# workbook.name is "DEMO01 AE review 261011_142233.xlsx": the file name the
# setting keeps and the time, or just "DEMO01 AE review.xlsx" if the setting
# keeps Add the date and time unticked (base.add_date_time is False).
# to_workbook(file_name="AE review") names it instead, add_date_time=False
# leaves out the date and time, and now=datetime(...) stamps it with another
# time.
```

The workbook's name is the one the desktop export would get. A setting that
keeps no file name (every setting saved before 2.21) needs
`to_workbook(file_name=...)`, just as the desktop waits for a name to be
typed: without it, `to_workbook()` raises `WorkflowInputError` ("Give the
workbook a file name: the saved setting “monthly AE review” doesn't keep
one."). The table is built either way. Without the date and time the name is
the same every run, so writing it replaces the last workbook, where the
desktop asks first.

The workbook is byte for byte the desktop export for the same inputs, but for
the creation time it holds (`docProps/core.xml`). The setting is applied as
the desktop applies one the user picks: its joins are tidied the way the Joins
step shows them, additional inputs take the form and column names the setting
saved for them, and a setting with no study name keeps the export's.

A setting the export doesn't fit is refused, with a message written for the
user; `missing_ok=True` runs it without what is missing and says so in
`warnings`:

```python
from clinical_reporting.workflow import WorkflowInputError

try:  # lab_results.csv isn't given, so the setting's LAB form is missing
    clinical_reporting.build_base_report(
        "Core_Listings_DEMO01_20261001.zip", "settings/monthly_ae_review.json"
    )
except WorkflowInputError as problem:
    print(problem)
    # The saved setting “monthly AE review” doesn't fit this export.
    # Missing forms: LAB

base = clinical_reporting.build_base_report(
    "Core_Listings_DEMO01_20261001.zip",
    "settings/monthly_ae_review.json",
    missing_ok=True,
)
for warning in base.warnings:
    print(warning)  # Missing forms: LAB (the table has no LAB columns)
```

Inputs the report, or its workbook, can't be made from raise
`clinical_reporting.workflow.WorkflowInputError`:

- an export, setting or additional input that can't be found or read, and
  an additional input given twice or as a file object without a `name`;
- additional inputs whose form names can't be used (a "." in the name, two
  files with one name, or a name a form already has). A file needs a saved
  form name: named after itself, its name holds its extension's ".";
- a setting that needs forms or items the data lacks, as above, one line per
  kind ("Missing forms: LAB", "Missing items in DM: Height"), unless
  `missing_ok=True`. The members of the setting's stacked forms, and the
  forms and items of its coalesced items, count as forms and items it needs,
  whether they are selected or not;
- a report that can't run: the desktop's "Cannot run:" list (an overlap later
  data brings to a coalesced item that refuses them is one);
- a workbook with no name: `to_workbook()` without `file_name` when the
  setting keeps none (above).

`warnings` holds, in order, the missing lines, the stacked forms' missing
members and missing or replaced matched items, the coalesced items' missing
forms and items, and the saved column names an additional input can't use.
Without `missing_ok=True` only the last can appear: the others are refusals.
Each is a
`clinical_reporting.feedback.Message`: a `str` with `kind == "warning"` and,
for the ignored names, `details` listing them by file. A setting that matches
no rows isn't refused: the table keeps its columns, and the workbook has the
header row only.

`clinical_reporting.build_base_report_from_forms(forms, setting, *,
study_name=None, additional_inputs=(), missing_ok=False)` does the same from
forms already read (`{form name: DataFrame}`), and
`clinical_reporting.settings_store.find_saved_setting(name, *, folder=None,
study_name=None)` finds the file of a setting the desktop lists by name:

```python
from clinical_reporting.settings_store import find_saved_setting
from clinical_reporting.workflow import read_corelisting

# In ~/Documents unless folder= says where; no setting or several with that
# name raise WorkflowInputError.
setting = find_saved_setting("monthly AE review", study_name="DEMO01")
forms = read_corelisting("Core_Listings_DEMO01_20261001.zip")  # {form: DataFrame}
base = clinical_reporting.build_base_report_from_forms(
    forms, setting, study_name="DEMO01", additional_inputs=["lab_results.csv"]
)
```

New automations keep their saved setting versioned in the repo next to their
code, e.g. `src/<tool>/settings/<name>.json`, and pass its path:
`Path(__file__).with_name("settings") / "<name>.json"`. To ship it inside the
tool's executable, add the folder to the tool's `.spec` `datas` under the same
package path, e.g. `('src/<tool>/settings', '<tool>/settings')`, as
`CCI Clinical Reporting.spec` does for `telemetry.json`.

### The building blocks

| Step | Module | What it does |
| --- | --- | --- |
| Load data | `clinical_reporting.data` | Read a Corelisting ZIP / CSV / Excel into a `{form_name: DataFrame}` dict and shape additional inputs. |
| Apply a setting | `clinical_reporting.session` | `apply_saved_setting(report, settings)` lines a saved setting up with the report's data, as the desktop does. |
| Run | `clinical_reporting.report.CLReport` | Hold the selections and execute `create_report()`. |
| Export | `clinical_reporting.export` | Write the result to xlsx/csv, or render it to bytes. |

```python
from clinical_reporting import session
from clinical_reporting.data import read_data_dict_zip_corelisting
from clinical_reporting.export import write_xlsx
from clinical_reporting.settings_store import read_settings_json

# 1. Load the study data into {form_name: DataFrame}
report = session.new_report(
    "DEMO01", read_data_dict_zip_corelisting("study_export.zip")
)

# 2. Apply a saved setting from the UI
missing = session.apply_saved_setting(report, read_settings_json("setting.json"))
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

The report must hold its data before `apply_saved_setting()` so the saved
setting can be reconciled against the columns actually present. It returns a
`{"forms": [...], "items": [...]}` report of anything dropped because the
current data no longer supports it — the same information the UI shows as a
warning label (`clinical_reporting.steps.setting_missing_lines` words it).

### Building a saved setting in code

Any `.json` saved from the UI is a valid saved setting, but you can also
build one in memory using the same schema:

```python
settings = {
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
session.apply_saved_setting(report, settings)
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
from clinical_reporting.data import load_additional_inputs
from clinical_reporting.export import dataframe_to_xlsx_bytes, write_csv

# Combine a Corelisting ZIP with additional inputs (CSV/Excel files)
inputs = load_additional_inputs(["labs.csv"])  # {resolved_path: DataFrame}
# try_load_tabular_files(paths) skips unreadable files instead of raising and
# returns (loaded, failures), both keyed by the paths as given
form_names = {path: "LABS" for path in inputs}  # path -> form name
column_names = {}  # (path, original_col) -> new name
# steps.additional_form_names_message(data.additional_form_names(inputs,
# form_names), taken) says why names can't be used ("." in one, a repeat, or
# a form's name); None when they can. Merging rebuilds the data and resets the
# selections, so apply the saved setting after it, as build_base_report does.
session.apply_additional_inputs(report, inputs, form_names, column_names)

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
    matches=(
        Match("Visit Name", {"SV": "Event Group Name", "DSSVLTFU": "Event Label"}),
    ),
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
`stacking.problems(stacked_forms, loaded_form_names, data)` lists what keeps
stacked forms from reaching the report, one line per problem;
`stacking.form_problems` gives the same per stacked form, each with the field
that fixes it (`name`, `members`, `match.I`, `cell.I.MEMBER`).

### Coalesced items

```python
from clinical_reporting import coalescing, session
from clinical_reporting.coalescing import CoalescedItem, Fill

race = CoalescedItem(
    "DM",
    "Race",  # one of its items' names, or a new one
    first="Race",
    fills=(Fill("Race Other Specify", "=", "Other"),),  # a Filters operator and value
)
coalescing.problems([race], report.stacked_data)  # what holds it back; [] when it fits
session.apply_coalesced_items(report, [race])  # rebuilds report.data, keeps selections
report.data["DM"]  # Race in place of Race and Race Other Specify
outcome = coalescing.build(race, report.stacked_data["DM"])  # rows by item, overlaps
```

`report.stacked_data` holds the loaded forms and the stacked forms built from
them, what coalesced items are made from; `report.data` has the coalesced
items in place, made again whenever `set_data` runs. `report.coalesced_build`
says what building them found: forms and items the data lacks
(`reconcile_with_current_data()` reports those as missing forms and items;
the coalesced item is built from the items left), and conflicts: overlaps in
one that refuses them (`on_overlap=REFUSE`, the default; `KEEP_EARLIER` keeps
the earlier value instead), or its name now given to another item of its
form. Conflicts are the validation issue `coalesced_item_conflict`, which
`create_report()` refuses. `coalescing.problems(items, data)` lists what
keeps coalesced items from reaching the report, one line per problem
(`shown=None` names every overlapping row); `coalescing.item_problems` gives
the same per item, each with the field that fixes it (`form`, `name`,
`item.K`, `value.K`, `overlap.K`), and `preview` builds one for a page that
shows one at a time.

### Persisting a saved setting

A saved setting built in code can be written back to the same JSON the
UI reads, so headless runs and the UI stay interchangeable:

```python
from clinical_reporting.settings_store import write_settings_json

write_settings_json("my_setting.json", report.settings_to_dict("batch-run"))
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
selections. Versions before 2.16 ignore the key: a setting that selects a
stacked form reports it as a missing form there, and re-saving it there drops
the stacked forms. A damaged entry is skipped and logged.

It may also hold `coalesced_items`: the coalesced items applied to the
report, each with its form, name, first item, later items (each with its
condition's operator and value, if it has one) and what it does where values
overlap (`clinical_reporting.coalescing`). Only applied coalesced items are
saved; the key is written only when there are some, so other settings save
exactly as before. Loading a setting rebuilds its stacked forms and coalesced
items before reading its selections. Versions before 2.17 ignore the key: a
setting that selects a coalesced item under a new name reports it as a
missing item there, and re-saving it there drops the coalesced items. A
damaged entry is skipped and logged.

It may also hold `export_file_name`: the export's file name and whether the
date and time are added to it, `{"name": "DEMO01 DSMB", "add_date_time":
false}` (`clinical_reporting.export_name`). Save setting writes it from File
name and Add the date and time, picking the setting fills them back in, and
`BaseReport.to_workbook()` names its workbook from it. The name is kept as the
export uses it, without a typed `.xlsx` and with characters not allowed in
file names made `_`, so it never names a folder. The key is written only when
there is a name, so other settings save exactly as before. Versions before
2.21 ignore it, and re-saving the setting there drops it. A key without a
usable name is ignored and logged; an `add_date_time` that isn't true or false
counts as true.

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
shell: a sidebar of steps (an icon strip with the steps' badges on narrow
windows, and in Compact density until opened), a header, and a
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
- **Add a table column the user can change:** give it
  `ColumnSpec(..., editable=True)` in `make_table`, whether its cells are
  plain text, dropdowns or fields; pass `make_table(..., controls=True)` when
  its cells hold dropdowns or fields, so the rows leave them room.
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
panel's messages wrap instead of widening it), `test_editable_columns.py`
that every table's pencils sit on exactly the columns with something to
change, and `test_preview_tool.py` pins the step order (update it when you
reorder steps).

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
  models.py                    # forms, labels, identifiers
  report.py                    # report state, its saved-setting dict, reconciliation
  session.py                   # what happens to a report when the user acts; build/export
  base_report.py               # a saved setting run on an export, as a table and workbook
  settings_store.py            # saved settings as JSON files in a folder; their JSON text
  feedback.py                  # status messages tagged info/success/warning/error
  filenames.py                 # safe file names; export names, with or without the date and time
  pipeline.py                  # joins, filters, ordering, renames, formatting
  report_columns.py            # the output columns and their names, before running
  workflow.py                  # the tools' workflows: OutputFile, input errors, reading inputs
  validation.py                # executable-report validation; "Cannot run" messages
  steps.py                     # the steps: titles, badges, and what they say
  help_text.py                 # the help shown beside each step (Markdown)
  data.py                      # Corelisting ZIP, CSV, Excel, additional inputs (paths or uploads)
  additional_names.py          # additional inputs' form/column names kept with a saved setting
  stacking.py                  # stacked forms: how they line up, building them, their settings key
  coalescing.py                # coalesced items: building them, their problems, their settings key
  export_name.py               # the export's file name kept with a saved setting
  export.py                    # xlsx/csv/bytes rendering
  telemetry.py                 # reports saves to the usage counter (off unless configured)
  sample_data.py               # made-up DEMO01 data for previews and tests
  ui/                          # PySide6 desktop front end
    app.py                     # entry point: starts the app and opens the window
    window.py                  # QMainWindow plus the behavior mixins
    main_ui.py                 # builds the pages into the window's shell
    navigation.py              # page changes; badges, header, status bar, toasts
    pages/                     # one module per step: its widgets and behavior mixin
      source_data.py           # Corelisting ZIP, cut-off date, and saved settings
      additional_input.py      # additional inputs, form and column names, saved names
      stacked_forms.py         # stacked forms: members, matches, and their marks
      coalesced_items.py       # coalesced items: items, conditions, overlaps, and their marks
      selection.py             # forms, common items, and form items
      filters.py               # filters and comparisons
      joins.py                 # join order (Move up/down), type, and items
      order_rename.py          # output order and renames
      preview_export.py        # preview, export, and save a setting
      _common.py               # what the pages share: the table helper, cell combo and item boxes, marks
    preview.py                 # python -m clinical_reporting.ui.preview
    base.py                    # window-level mixin: shared state, refresh coordinators, helpers
    dialogs.py                 # dialogs shared by more than one page
    table_actions.py           # original-name/new-name tables (renames)
    preview_model.py           # Qt table model for the preview grid
```
