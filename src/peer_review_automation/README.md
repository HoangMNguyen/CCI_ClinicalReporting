# Peer Review Automation

Reviews a Medidata **SDS (Study Design Spec)** workbook and lists every
problem it finds in an error-report workbook.

Run it from the repository root once the environment is
[set up](../../README.md#setup):

```bash
python -m peer_review_automation
```

## Using it

One page: **SDS peer review**. Choose the SDS workbook (its
`Form Definitions` and `Codelists` sheets are checked), and optionally Rave's
validation report, switch on the naming-convention checks if you want them,
choose an output folder, change the suggested file name if you like, and Run.
Every finding goes to a workbook named, by default, after the SDS file (its
name up to the first "-", usually the study):
`<that name> Peer Review Automation Output YYMMDD_HHMMSS.xlsx`, never over an
existing file.

Checks include:

- Item names longer than 32 characters.
- Fields not marked Required (excluding Label/Boolean types).
- Date fields missing the "No Future Date" flag.
- Item/Item Group names not matching their External ID.
- Codelist display types (picklist vs. other) inconsistent with the number
  of visible options.
- Shared vs. non-shared naming conventions (`_YS_`/`_NS_`), and codelist/unit
  attachments matching item names.
- Optional naming-convention checks (`CL_`/`DT_`/`NM_`/`TX_`/... prefixes,
  help-text `YH`/`NH` markers) via the switch.
- Optional cross-check against Rave's validation report (a CSV), with a
  built-in ignore list for known-acceptable error names; results land on a
  separate "Validation Review" sheet.

A problem with an input names the file it is about: one that is gone or
can't be opened, a workbook without the Form Definitions or Codelists sheet,
a validation report without its columns, or an SDS sheet without a column a
check needs.

## Scripting it

The review is `run()` in `src/peer_review_automation/sds.py`: it takes the
files (paths or open files) and returns the workbook as an `OutputFile`,
without touching a folder.

```python
from peer_review_automation import sds

output = sds.run("STUDY01-SDS.xlsx", validation="validation.csv", check_naming=True)
with open(output.name, "wb") as file:
    file.write(output.data)
```

## Package layout

```text
src/peer_review_automation/
  __main__.py                  # runtime entry: python -m peer_review_automation
  app.py                       # the window: one WorkflowPage
  sds.py                       # run(): the review workbook, Qt-free
```
