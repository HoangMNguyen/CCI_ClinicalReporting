"""The help the desktop app shows beside each step (no Qt needed).

:data:`HELP` holds, for every step of :data:`clinical_reporting.steps.STEP_KEYS`,
plain-language instructions in Markdown, in three sections: what the step is
for, how to use it step by step (its options explained), and what is good to
know. Source data's also lists the keyboard shortcuts that work on every step.
"""

from __future__ import annotations

from typing import Dict

from clinical_reporting import steps

_SOURCE = """\
## What this step is for

Every report starts here. Choose the Corelisting ZIP the report is made from \
and, if you want, a cut-off date and a saved setting to start from.

## Step by step

1. Click **Choose ZIP…** and pick the Corelisting ZIP.
2. To leave out later records, turn on **Apply cut-off date**, then set the \
**Cut-off** date. Only records on or before that date are read from the ZIP.
3. To start from the choices of an earlier report, turn on \
**Start from a saved setting**:
    - **Folder**: where the saved settings are kept. Click \
**Settings folder…** to choose another folder.
    - **Setting**: pick the saved setting to start from.
4. Go on to the next step.

## Good to know

- The study number is read from the ZIP's file name. The **Setting** list \
shows only that study's saved settings.
- A saved setting keeps the forms, items, joins, filters, comparisons, column \
order and names, stacked forms, coalesced items, and the names given to \
additional files. It doesn't keep the cut-off date.
- The cut-off date never leaves out rows of additional files.
- If a saved setting can't be loaded, the **Setting** box turns red and the \
message below it says why.
- If the setting needs forms or items the ZIP doesn't have, a \
**Missing forms** warning lists them. A form that comes from an additional \
file is added once you add that file on Additional input.
- Choosing another ZIP starts a new report. Your additional files, stacked \
forms and coalesced items carry over to it.
- **Remove file** (the × next to the ZIP) takes it out of the report. Forms from \
additional files stay. Stacked forms and coalesced items made only from the \
ZIP's forms go with it; with no additional files either, they all go.
- Keyboard shortcuts on every step: **Ctrl+Tab** or **Ctrl+PgDown** goes to \
the next step, **Ctrl+Shift+Tab** or **Ctrl+PgUp** to the previous one, and \
**Ctrl+\\\\** shows or hides the sidebar.
"""

_ADDITIONAL = """\
## What this step is for

Add CSV or Excel files to the report. Each file becomes a form, next to the \
forms of the Corelisting ZIP.

## Step by step

1. Click **Add files…** and pick one or more CSV or Excel files.
2. In **Form names**, type each file's form name in **New name**.
    - **Saved names**: once you've picked a saved setting on Source data that \
kept names for files, choose the names it kept for this file, or **None** to \
clear the names it filled in.
3. To rename a file's columns, select the file in **Form names**, then type \
the new names in **New name** under **Column names**.
4. Go to another step. The files then reach the report as forms. With a \
saved setting, they reach it as soon as every file the setting needs is added \
and no **New name** is red.

## Good to know

- A file's **New name** is red until it can be used: while it is empty (a \
form name can't contain ".", so a file's own name can't be used), when it \
contains ".", or when a loaded form, a stacked form or another file already \
has it. Hover over it to see why. While a name is red, none of the files \
reach the report.
- After you pick a saved setting, a file that matches one it kept names for \
(by its file name, or else by its columns) gets those names filled in. Names \
you typed are never replaced.
- **Still to add** lists the files the saved setting needs that aren't added \
yet. Once the last one is in (added, or picked in **Saved names**) and no \
**New name** is red, the files reach the report at once, without leaving the \
step; changes after that wait until you go to another step.
- A saved column name a file doesn't have is ignored, and the form is still \
added. Renaming the column by hand puts it back.
- Right-click column names and choose \
**Copy Original Item Name to New Item Name** to start from their own names.
- **Remove** takes the selected files out. Their forms leave the report when \
you go to another step. With no ZIP loaded, removing the last file also \
removes every stacked form and coalesced item at once.
- Files that finish loading after you've gone to another step reach the \
report right away.
"""

_STACKED = """\
## What this step is for

Put the rows of two or more forms one under another, as one new form.

## Step by step

1. Click **New stacked form**.
2. Type its **Name**.
3. In **Members**, tick the forms to stack: two or more.
4. Check the new form's items, below the table:
    - **In every member**: items all the members have. They are stacked by \
themselves.
    - **Matched**: items of different members lined up under one name. Click \
the name to pick one of the matched names or type a new one. In each \
member's cell, pick the item that member gives, or **—** for none.
    - **Left out**: items that not every member has. To line them up, select \
them (Ctrl-click for several) and click **Match**. To keep a single item, \
select it and click **Match**, or double-click it.
5. To undo a match, select it and click **Unmatch**: its items go back to \
Left out.
6. Go to another step. The stacked form then reaches the report.

## Good to know

- The **Name**, **Members**, a match's name or a member's cell turn red when \
they can't be used: no name yet, fewer than two members, a name that's taken, \
or a member giving two of a match's items. Hover over it to see why. While \
anything is red, no stacked form reaches the report.
- Only loaded forms (from the ZIP or from additional files) can be members, \
not other stacked forms. The members stay usable on their own.
- A member that isn't loaded is left out, with a warning. It stays ticked in \
**Members**, so adding its file brings it back.
- **Search items** (Ctrl+F) narrows the list of items.
- **Remove** takes the selected stacked form out. It leaves the report when \
you go to another step.
"""

_COALESCED = """\
## What this step is for

Make one item from two or more items of a form whose values exclude each \
other: where the first item has no value, a later one gives it.

## Step by step

1. Click **New coalesced item**.
2. Pick its **Form**: a loaded form or a stacked form.
3. In the items table, pick its items in order:
    - The first row's item gives each row's value to start with.
    - Each later row's item fills the rows where the value so far is empty. \
To have it also replace values, choose a condition on the value so far in \
**Fills where the value so far is empty or**, and type the condition's \
**Value** if it needs one. **—** means no condition.
    - **Rows** shows how many rows take their value from each item.
    - **Add item**, **Remove item**, **Move up** and **Move down** change the \
list.
4. Set its **Name**: pick one of its items' names or type a new one.
5. Choose what happens **When values overlap**, that is, where a later item \
has a value and the value so far has one too:
    - **Refuse**: overlapping rows are a problem to fix.
    - **Keep the earlier value**: the value so far stays.
6. Go to another step. The coalesced item then reaches the report.

## Good to know

- Under the items table, the editor says how the form's rows take their \
value.
- The coalesced item takes the place of its first item, and its other items \
leave the form.
- An item can be in one coalesced item only. With two or more forms loaded, \
a common item can only be coalesced under its own name, so the forms still \
join on it.
- Coalesced items are made after the stacked forms: a member's coalesced \
item doesn't reach its stacked form. Coalesce the stacked form instead.
- A field turns red when it can't be used: no form or one that isn't \
loaded, fewer than two items, an empty row, an item that's taken or not in \
the form, no name or a taken one, a condition without a value, or refused \
overlaps (the **Rows** cell and **When values overlap**). Hover over it to \
see why. While anything is red, no coalesced item reaches the report.
- **Remove** takes the selected coalesced item out. It leaves the report when \
you go to another step.
"""

_FORMS = """\
## What this step is for

Pick the forms the report uses.

## Step by step

1. Find a form in **Available**. Type in **Search forms** to narrow the list.
2. Double-click it, or select it and click **›** (Add selected), to move it \
to **Selected**. Ctrl-click selects several.
3. To take a form out, double-click it in **Selected**, or select it and \
click **‹** (Remove selected).
4. **»** (Add all) and **«** (Remove all) move every form at once.

## Good to know

- The search (Ctrl+F) isn't case-sensitive, and takes patterns: a | between \
two names finds either.
- A form you add joins the others last, on Subject, with a Left join. Change \
that on Joins.
"""

_COMMON = """\
## What this step is for

Pick the common items: items every form has. Each one becomes a column of \
the report, and the forms are joined on them.

## Step by step

1. Double-click an item in **Available**, or select it and click **›** \
(Add selected). Type in **Search common items** to narrow the list.
2. To take one out, double-click it in **Selected**, or select it and click \
**‹** (Remove selected).
3. **»** (Add all) and **«** (Remove all) move every item at once.

## Good to know

- Subject is chosen for you when a ZIP is loaded.
- Only items every loaded form has are listed: an additional file without \
one of them takes it off the list.
- A form that doesn't join on a common item (see Joins) also gives the \
report its own column of it, named with the form.
- The search (Ctrl+F) isn't case-sensitive, and takes patterns.
"""

_FORM_ITEMS = """\
## What this step is for

Pick the other items each selected form adds to the report.

## Step by step

1. Find an item in **Available**. Each one is named with its form, as \
FORM.item. Type in **Search form items** to narrow the list.
2. Double-click it, or select it and click **›** (Add selected).
3. To take one out, double-click it in **Selected**, or select it and click \
**‹** (Remove selected).
4. **»** (Add all) and **«** (Remove all) move every item at once.

## Good to know

- Each item becomes a column named FORM.item, until you rename it on \
Order & rename.
- If a selected form adds nothing to the report, the **Selected** list turns \
red.
- The search (Ctrl+F) isn't case-sensitive, and takes patterns.
"""

_FILTERS = """\
## What this step is for

Keep only the rows that match every filter.

## Step by step

1. Click **+** to add a filter.
2. Pick its **Item**. Type in the box to find one.
3. Pick its **Operator**:
    - **=** and **!=**: equal to, not equal to.
    - **>**, **>=**, **<** and **<=**: greater or less than.
    - **Contains** and **Does not contain**: has the text somewhere, or not.
    - **In** and **Not in**: one of a list, or none of it. Separate the \
values with commas.
    - **is Null** and **is not Null**: empty, or not empty. These take no \
value.
4. Type its **Value**.
5. To take filters out, select their rows and click **−**.

## Good to know

- Text is compared without regard to case; values that are numbers are \
compared as numbers.
- A filter on a common item works on every form, one on a form's item on \
that form, before the forms are joined.
- **Item** and **Value** stay red until they're filled in; hover over them \
to see why. While a filter is red, the report can't be previewed or exported.
"""

_JOINS = """\
## What this step is for

Set how the selected forms are combined into one table.

## Step by step

1. Check the order: the forms are joined from top to bottom, and the first \
form starts the report.
2. To change the order, select a form and click **Move up** or **Move down**.
3. For each form below the first, pick the common items it joins on in \
**Item 1**, **Item 2** and **Item 3**.
4. Pick its **Type**:
    - **Left join**: keep every row so far, adding this form's values where \
they match.
    - **Inner join**: keep only the rows found in both.
    - **Right join**: keep every row of this form.
    - **Outer join**: keep all the rows of both.

## Good to know

- The first form's items and type are greyed: it joins on nothing.
- A form you add joins last, on Subject, with a Left join. A form moved out \
of first place joins on Subject.
- A form below the first needs at least one join item: its **Item 1** is red \
until you pick one.
- A common item a form doesn't join on stays as that form's own column, \
named with the form. The message on this step lists them.
"""

_COMPARISONS = """\
## What this step is for

Keep only the rows where one item compares to another.

## Step by step

1. Click **+** to add a comparison.
2. Pick **Item 1**.
3. Pick the **Operator**: **=**, **!=**, **>**, **>=**, **<** or **<=**.
4. Pick **Item 2**.
5. To take comparisons out, select their rows and click **−**.

## Good to know

- Comparisons work after the forms are joined, so the two items can come \
from different forms.
- **Item 1** and **Item 2** stay red until you pick them.
"""

_ORDER = """\
## What this step is for

Set the order of the report's columns, and the names they get in the Excel \
file.

## Step by step

1. Select one or more columns. Ctrl-click or Shift-click selects several.
2. Move them with the arrow buttons: **Move to top**, **Move up**, \
**Move down** or **Move to bottom** (hover over a button to see which).
3. To rename a column, click its **Output name** and type the new name.

## Good to know

- **Search columns** (Ctrl+F) finds columns by their own name; \
**Next match** and **Select all matches** go through the results.
- Right-click selected rows and choose \
**Copy Original Item Name to New Item Name** to start from their own names.
- An output name made only of spaces, or one another column already has, is \
red.
- A column without an output name keeps its own name.
"""

_PREVIEW = """\
## What this step is for

Check the report's rows, export them to Excel, and save your choices for \
next time.

## Step by step

1. Check the preview. It's built when you open this step; click **Refresh** \
(F5) to build it again.
2. Under **Export**:
    - **Folder**: click **Choose…** and pick where the file goes.
    - **File name**: optional. The date and time of the export are added to \
it.
    - Click **Export to Excel** (Ctrl+E).
3. To save your choices, under **Save setting**:
    - Turn on **Save these settings for reuse**.
    - **Name**: the name the setting is saved under.
    - **Folder**: click **Choose…** to pick where settings are saved.
    - Click **Save setting** (Ctrl+S).

## Good to know

- If something stops the report, the message above **Export to Excel** \
starts with "Cannot run" and names the steps to fix.
- The export **Folder** is red until you choose one, and the setting's \
**Name** while it's empty.
- While Additional input, Stacked forms or Coalesced items has changes that \
can't reach the report, **Save setting** waits until you fix them.
- Saved settings are offered on Source data for reports of the same study.
"""

#: The help of each step, in Markdown, by step key.
HELP: Dict[str, str] = {
    steps.SOURCE: _SOURCE,
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
