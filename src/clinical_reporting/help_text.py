"""The help the desktop app shows beside each step (no Qt needed).

:data:`HELP` holds, for every step of :data:`clinical_reporting.steps.STEP_KEYS`,
plain-language instructions in Markdown: what the step is for, what to do
before it, how to do it, the words it uses, and what is good to know. Source
data's text starts with an overview of the whole app. The examples use the
made-up DEMO01 study (:mod:`clinical_reporting.sample_data`).
"""

from __future__ import annotations

from typing import Dict

from clinical_reporting import steps

_OVERVIEW = """\
## How a report is made

A report is built in 12 steps. They are listed in the sidebar on the left, \
in this order:

1. **Source data**: choose the Corelisting ZIP the report starts from.
2. **Additional input** (optional): add CSV or Excel files as extra forms.
3. **Stacked forms** (optional): put the rows of several forms one under \
another as one new form.
4. **Coalesced items** (optional): make one item from two or more items of \
a form.
5. **Forms**: pick the forms the report uses.
6. **Common items**: pick the items every form shares, such as Subject.
7. **Form items**: pick the other items to show from each form.
8. **Filters**: keep only the rows that match a value.
9. **Joins**: set how the forms are combined into one table.
10. **Comparisons**: keep only the rows where one item compares to another.
11. **Order & rename**: set the column order and the column names.
12. **Preview & export**: check the rows, export them to Excel, and save \
your choices.

Additional input, Stacked forms and Coalesced items change the report's data. \
Your changes on them reach the report when you go to another step.

## Red fields

A field with a **red outline** has a value missing, or one the report can't \
use. Hover over it to see why. The step's badge in the sidebar turns red too.

While any field is red, the report can't be previewed or exported. \
Preview & export says which steps to fix.

On Additional input, Stacked forms and Coalesced items, a red field also \
keeps that step's changes out of the report until you fix it.

## The sidebar badges

Each step in the sidebar can show a badge:

- a **number**: how many you picked (forms, items, filters, ...);
- a **tick**: the step is done;
- **optional**: you can skip the step;
- a **warning**: something needs a look, but the report still runs;
- a **red mark**: a problem to fix before the report can run.

Hover over a step to see what its badge means. On a narrow window, or in \
Compact density, the sidebar shows only icons, with each step's badge \
beside its icon. Press Ctrl+\\\\ to show or hide the sidebar.

## Keyboard shortcuts

- **Ctrl+Tab** or **Ctrl+PgDown**: next step.
- **Ctrl+Shift+Tab** or **Ctrl+PgUp**: previous step.
- **Ctrl+\\\\**: show or hide the sidebar.
- **Ctrl+F**: search (Forms, Common items, Form items, Stacked forms, \
Order & rename).
- **F5**: build the preview again (Preview & export).
- **Ctrl+E**: export to Excel (Preview & export).
- **Ctrl+S**: save the setting (Preview & export).

## Display settings

The **◐** button at the top right opens the display settings:

- **Appearance**: System (follows your computer), Light or Dark.
- **Density**: how much fits on the screen. Compact fits more; \
Comfortable gives more room.

"""

_SOURCE = """\
## What this step is for

Every report starts here. You choose the **Corelisting export**: the ZIP \
file of the study's forms. You can also start from a **saved setting**: \
the choices you saved for an earlier report.

## Before you start

Have the Corelisting ZIP at hand, for example \
Core_Listings_DEMO01_20261001.zip.

## Step by step

1. Click **Choose ZIP…** and pick the Corelisting ZIP.
2. To leave out later records, turn on **Apply cut-off date** and set the \
**Cut-off** date.
3. To reuse earlier choices, turn on **Start from a saved setting**. Check \
the **Folder**, or click **Settings folder…** to choose another one. Then \
pick a setting in **Setting**.
4. Go on to the next step.

## Words used here

- **Corelisting export**: the ZIP file with the study's forms.
- **Form**: one table of the export, such as DM (demographics) or AE \
(adverse events).
- **Cut-off date**: only records on or before this date are read from \
the ZIP.
- **Saved setting**: the choices of an earlier report, saved under a name: \
its forms, items, joins, filters, comparisons, column order and names, \
stacked forms, coalesced items, and the names given to additional files.

## Good to know

- The study number comes from the ZIP's name: in \
Core_Listings_DEMO01_20261001.zip it is DEMO01. The Setting list shows only \
that study's saved settings.
- The cut-off date isn't kept in a saved setting. It never cuts rows from \
additional files.
- If a saved setting can't be loaded, the Setting box turns red and the \
message under it says why.
- If the setting needs forms or items the export doesn't have, a \
**Missing forms** warning lists them. A form that comes from an additional \
file is added once you add that file on Additional input.
- Choosing another ZIP starts a new report. Your additional files, stacked \
forms and coalesced items carry over to it.
- The **Remove file** button next to the ZIP takes it out of the report. \
Forms from additional files stay. Stacked forms and coalesced items made only \
from the ZIP's forms go with it; with no additional files either, they all go.
"""

_ADDITIONAL = """\
## What this step is for

Add CSV or Excel files to the report. Each file becomes a form, next to the \
forms of the Corelisting export.

## Before you start

Have the files at hand. Each file should have a column the report can join \
on, such as Subject.

## Step by step

1. Click **Add files…** and pick one or more CSV or Excel files.
2. In **Form names**, type a **New name** for each file, for example LAB.
3. To rename a column, select its file, then type a **New name** in \
**Column names**.
4. Go to another step. Your files then reach the report as forms.

## Words used here

- **Additional input**: a CSV or Excel file added as a form.
- **Form**: a table of the report. Each additional file is one form.
- **Saved names**: the form and column names a saved setting kept for its \
additional files.

## Good to know

- Until a file has a form name, its **New name** is red: a file's own name \
can't be used, because a form name can't contain ".".
- A form name can't be one a loaded form or a stacked form already has, nor \
another file's.
- After you pick a saved setting on Source data, a file that matches one it \
saved names for gets those names. Check them in **Saved names**, or pick \
another entry or None.
- **Still to add** lists the setting's files you haven't added yet.
- A saved column name the file doesn't have is ignored, and the form is still \
added. Renaming the column by hand puts it back.
- **Remove** takes the selected files out. Their forms leave the report when \
you go to another step. With no ZIP loaded, removing the last file also \
removes every stacked form and coalesced item at once.
"""

_STACKED = """\
## What this step is for

Put the rows of two or more forms one under another, as one new form. For \
example, stack EOT (end of treatment) and DS (disposition) as DISP, so each \
subject's end of study is in one form.

## Before you start

Load the Corelisting ZIP, and add on Additional input any file whose form \
you want to stack.

## Step by step

1. Click **New stacked form**.
2. Type its **Name**, for example DISP.
3. In **Members**, tick the forms to stack, for example EOT and DS.
4. Look at the items grid. Items every member has, such as Subject and \
Visit, are stacked by themselves.
5. To line up items that have different names, select them in **Left out** \
(Ctrl-click for several) and click **Match**, for example Reason with \
Status. Give the match a name.
6. Go to another step. The stacked form then reaches the report.

## Words used here

- **Stacked form**: a new form made of the rows of other forms.
- **Member**: a form whose rows go into the stacked form.
- **Stacked item**: an item of the stacked form.
- **Match**: items of different members lined up under one name.

## Good to know

- A stacked form needs a name and at least two members. Until it has them, \
its Name and Members are red.
- In a matched row, each member's cell is a dropdown. Choose **—** when the \
member gives nothing for that item. **Unmatch** takes the items back to Left \
out.
- A cell turns red when a member has two of the match's items: choose one, \
or **—**.
- The members stay usable on their own.
- **Remove** takes the selected stacked form out. It leaves the report when \
you go to another step.
"""

_COALESCED = """\
## What this step is for

Make one item from two or more items of a form whose values exclude each \
other. For example, in the stacked form DISP, each row has either a Reason \
(from EOT) or a Status (from DS): coalesce them into one item, Outcome.

## Before you start

Load the Corelisting ZIP. To coalesce items of a stacked form, set up the \
stacked form first.

## Step by step

1. Click **New coalesced item**.
2. Pick its **Form**, for example DISP.
3. Give it a **Name**, for example Outcome.
4. Pick its items in order: the first gives each row's value, for example \
Reason; the second fills in after it, for example Status. Click \
**Add item** for a third.
5. For a later item, choose a condition if it should also replace values, \
not only fill empty ones.
6. Choose what happens **When values overlap**.
7. Go to another step. The coalesced item then reaches the report.

## Words used here

- **Coalesced item**: one item made from two or more items of a form.
- **Overlap**: a row where an earlier item already has a value and a later \
item has one too, so one of the two would be lost.

## Good to know

- The first item gives each row's value. Each later item fills the rows \
where the value so far is empty, or meets its condition.
- **Move up** and **Move down** change the order of the items.
- With **Refuse**, overlapping rows are a problem: the item's **Rows** cell \
and **When values overlap** turn red. Change a condition, or choose \
**Keep the earlier value**.
- Empty items, a missing name, or a condition without a value are red until \
you fill them in.
- The coalesced item takes the place of its first item, and its items leave \
the form.
"""

_FORMS = """\
## What this step is for

Pick the forms the report uses.

## Before you start

Load the Corelisting ZIP on Source data.

## Step by step

1. Find a form in the list on the left. Type in the search box to narrow \
the list.
2. Double-click it, or select it and click the add arrow, to move it to the \
selected list.
3. To take a form out, double-click it in the selected list.

## Words used here

- **Form**: one table of the data, such as DM, VS or AE.

## Good to know

- The search is case-insensitive and takes patterns: dm|ae finds DM and AE.
- The double arrows add or remove all forms at once.
- A newly selected form joins last, on Subject, with a Left join. Change \
that on Joins.
"""

_COMMON = """\
## What this step is for

Pick the **common items**: the items every form has, such as Subject, Site \
and Visit. Each one becomes a column of the report.

## Before you start

Select the forms on Forms.

## Step by step

1. Double-click an item on the left to add it, or select it and click the \
add arrow.
2. Double-click an item on the right to take it out.

## Words used here

- **Common item**: an item every form has.

## Good to know

- Subject is chosen for you.
- A common item is only one that every loaded form has. An additional file \
without Visit, for example, takes Visit out of the common items.
- The forms join on common items (see Joins).
"""

_FORM_ITEMS = """\
## What this step is for

Pick the other items each selected form adds to the report.

## Before you start

Select the forms on Forms.

## Step by step

1. Find an item on the left, for example DM.Age. Type in the search box to \
narrow the list.
2. Double-click it, or select it and click the add arrow.
3. Double-click an item on the right to take it out.

## Words used here

- **Form item**: an item of one form. It is named with its form, as \
FORM.item: DM.Age, AE.Grade, VS.Pulse.

## Good to know

- Each form item becomes a column of the report, named like DM.Age until \
you rename it on Order & rename.
- If a selected form adds nothing to the report, the selected list turns \
red.
"""

_FILTERS = """\
## What this step is for

Keep only the rows that match every **filter**. For example, DM.Age >= 18 \
keeps adults only.

## Before you start

Pick the items to filter on: Common items and Form items.

## Step by step

1. Click **+** to add a filter.
2. Pick its **Item**, for example DM.Age.
3. Pick its **Operator**, for example >=.
4. Type its **Value**, for example 18.
5. To take a filter out, select its row and click **−**.

## Words used here

- **Filter**: a rule a row must meet to stay in the report.

## Good to know

- Each filter works on its own form, before the forms are joined.
- An operator that needs a value needs one: the Value stays red until you \
type it. "is Null" and "is not Null" take no value.
- A filter row that isn't finished is red until you finish it or remove it.
"""

_JOINS = """\
## What this step is for

Set how the selected forms are combined into one table.

## Before you start

Select at least two forms, and their common items.

## Step by step

1. Look at the order: forms are joined from top to bottom. The first form \
starts the report.
2. To change the order, select a form and click **Move up** or \
**Move down**.
3. For each form after the first, pick the items it joins on in \
**Item 1**, **Item 2** and **Item 3**, for example Subject.
4. Pick its **Type**.

## Words used here

- **Join order**: the order in which the forms are combined.
- **Join item**: a common item a form is matched on, such as Subject.

## Good to know

The join types:

- **Left join**: keep every row so far, adding this form's values where \
they match.
- **Inner join**: keep only the rows found in both.
- **Right join**: keep every row of this form.
- **Outer join**: keep all the rows of both.

A new form joins on Subject with a Left join. A form after the first needs \
at least one join item: its Item 1 is red until you pick one. The first \
form's items and type are greyed out: it joins on nothing.
"""

_COMPARISONS = """\
## What this step is for

Keep only the rows where one item compares to another. For example, \
AE.End Date >= AE.Start Date keeps adverse events that end on or after they \
start.

## Before you start

Pick the items to compare: Common items and Form items.

## Step by step

1. Click **+** to add a comparison.
2. Pick **Item 1**, for example AE.End Date.
3. Pick the **Operator**, for example >=.
4. Pick **Item 2**, for example AE.Start Date.
5. To take one out, select its row and click **−**.

## Words used here

- **Comparison**: a rule that compares two items of the same row.

## Good to know

- Comparisons work after the forms are joined, so the two items can come \
from different forms.
- A comparison needs both items: they stay red until you pick them.
"""

_ORDER = """\
## What this step is for

Set the order of the report's columns, and give them readable names.

## Before you start

Pick the items on Common items and Form items.

## Step by step

1. Select one or more columns. Ctrl-click or Shift-click selects several.
2. Move them with **Move to top**, **Move up**, **Move down** or \
**Move to bottom**.
3. To rename a column, click its **Output name** (the column with the \
pencil) and type, for example Age (years) for DM.Age.

## Words used here

- **Output name**: the column's name in the Excel file.

## Good to know

- Press Ctrl+F to search the columns; **Next match** and \
**Select all matches** go through the results.
- An output name made only of spaces, or one another column has, is red.
- A column without an output name keeps its own name, such as DM.Age.
"""

_PREVIEW = """\
## What this step is for

Check the report's rows, export them to Excel, and save your choices for \
next time.

## Before you start

Go through the steps before. Fix any step with a red badge.

## Step by step

1. Look at the preview. It is built when you open this step; click \
**Refresh** (F5) to build it again.
2. In **Folder**, click **Choose…** and pick where to save the file.
3. Optionally, type a **File name**.
4. Click **Export to Excel** (Ctrl+E).
5. To reuse your choices, turn on **Save these settings for reuse**, type a \
**Name**, check the **Folder**, and click **Save setting** (Ctrl+S).

## Words used here

- **Saved setting**: your choices, saved under a name to start a later \
report from (on Source data).

## Good to know

- If something stops the report, the message above **Export to Excel** \
says "Cannot run" and names the steps to fix.
- The Folder is red until you choose one.
- The file's name ends with the date and time of the export, so files \
never overwrite each other.
- The setting's Name is red while it is empty. While Additional input, \
Stacked forms or Coalesced items has changes that can't reach the report, \
Save setting waits until you fix them.
"""

#: The help of each step, in Markdown, by step key.
HELP: Dict[str, str] = {
    steps.SOURCE: _OVERVIEW + _SOURCE,
    steps.ADDITIONAL: _ADDITIONAL,
    steps.STACKED: _STACKED,
    steps.COALESCED: _COALESCED,
    steps.FORMS: _FORMS,
    steps.COMMON: _COMMON,
    steps.FORM_ITEMS: _FORM_ITEMS,
    steps.FILTERS: _FILTERS,
    steps.JOINS: _JOINS,
    steps.COMPARISONS: _COMPARISONS,
    steps.ORDER: _ORDER,
    steps.PREVIEW: _PREVIEW,
}


def help_markdown(step: str) -> str:
    """The help of *step* (a key of :data:`~clinical_reporting.steps.STEP_KEYS`)."""
    return HELP[step]


__all__ = ["HELP", "help_markdown"]
