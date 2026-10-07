# CCI Automation

Builds study Enrollment Logs and DSMB Reports from a Corelisting export, and
fixes common formatting problems in a CSV or XLSX file.

Run it from the repository root once the environment is
[set up](../../README.md#setup):

```bash
python -m cci_automation
```

## Using it

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
a message). Other problems you can fix are messages too: a study without a
module (the message says which studies are supported), an export without a
Demographics (DM) form or, for the DSMB report, with no submitted
Demographics forms up to the cut-off date, and files that are gone or can't
be read.

## Scripting it

Each workflow is a plain, Qt-free `run()` that returns the workbook as an
`OutputFile` (a file name and the workbook's bytes) without touching the
user's folders: `enrollment_log/EnrollmentLog.py`, `dsmb/DSMB.py` and
`format_tools/change_type.py`. The per-study DSMB modules still write a file,
which `DSMB.run()` reads back from a temporary folder, so the study's data
sits there only during a run.

```python
from cci_automation.dsmb import DSMB

output = DSMB.run("Core_Listings_15420.zip", study="15420")
with open(output.name, "wb") as file:  # "15420 DSMB Report YYMMDD_HHMMSS.xlsx"
    file.write(output.data)
```

## Adding a study

Add its module under `src/cci_automation/enrollment_log/` or
`src/cci_automation/dsmb/`, and the study in that workflow's
`SUPPORTED_STUDIES` (the page lists those). The enrollment log needs a branch
in `EnrollmentLog.collect_data`; the DSMB report needs a branch in
`_report_builder` (`dsmb/DSMB.py`), plus an entry in `_WRITES_WHEN_BUILT` if
the module writes its report while it is built instead of in `run()`.

## Package layout

```text
src/cci_automation/
  __main__.py                  # runtime entry: python -m cci_automation
  app.py                       # the window: a sidebar of three WorkflowPages
  util.py                      # helpers shared by the DSMB and Enrollment Log modules
  enrollment_log/              # EnrollmentLog.run() and one module per study
  dsmb/                        # DSMB.run() and one module per study
    DSMB_util.py               # DSMB statistics, number formatting and listing helpers
  format_tools/                # change_type.run(): the format tool
```
