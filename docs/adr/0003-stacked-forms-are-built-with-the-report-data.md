# Stacked forms are built with the report's data; matches line up names

Clinical Reporting stacks forms (puts their rows one under another) as **stacked forms**: definitions kept in the saved setting and built by `CLReport` whenever its data is set, so every later step treats them as forms and a loaded setting brings them back without a click. Items every member has under the same name stack by themselves; any other item is left out unless the user matches it, so a stacked form never takes an item out of the common items. A match lines up whole same-name groups and keeps the item each member gave it: names decide what lines up (a member added later joins by name, and a match can't split one name across two stacked items), while the kept items let a warning name an item a member no longer has.

## Considered options

- **Its own output on the Stacked forms page** (a separate preview and export): rejected. It repeats filters, renames and export, and selecting only the stacked form already gives that table.
- **A pipeline step inside `create_report`**, stacking selected forms after their filters: rejected. Selection, joins and common items all work on forms, so a stacked form must exist before them to be filtered and joined like one.
- **A free per-member column mapping**, as ETL union tools offer: rejected. It can split same-name items and rename a common item, which takes that item out of every form's common items and breaks joins on it.
- **Keeping every item, blank where a member lacks it**: rejected by the user. Unshared items stay out unless matched; a match may hold a single item to keep it.
- **Offering a setting's stacked forms for review before Apply**, like saved names for additional inputs: rejected. Members are named forms, so nothing needs matching, and a base report run through the core (ADR 0001) applies a setting without clicks.

## Consequences

- `CLReport.data` holds the stacked forms; `CLReport.loaded_data` holds the forms as loaded. Code that rebuilds a report's data starts from `loaded_data`.
- Loading a setting rebuilds the data before reading its selections, so they find the setting's stacked forms.
- A stacked form named like a loaded form isn't built, and export stays off until it is renamed.
- Data that changes after Apply can make a match ambiguous (a member with two of its items, a match named like an item every member now has), and so can an edited setting (two matches holding one item name). Building reports that as a conflict that stops the report until the match is fixed; it never picks one of the items or lets the match give way quietly.
- Versions before Clinical Reporting 2.16 ignore the `stacked_forms` key; a setting that selects a stacked form reports it missing there.
