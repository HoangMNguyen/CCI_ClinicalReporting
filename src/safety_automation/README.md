# Safety Automation

Builds the standardized Adverse Event / Dose-Limiting Toxicity (AE & DLT)
listing workbook for the Safety Department from a Corelisting export.

Run it from the repository root once the environment is
[set up](../../README.md#setup):

```bash
python -m safety_automation
```

## Using it

One page: **AE & DLT listing**. Choose a Corelisting ZIP (the study number
comes from its file name, as in CCI Automation) and an output folder, change
the suggested file name (`<study> AE DLT`) if you like, and Run. The app
builds the workbook in the background and saves it as
`<name> YYMMDD_HHMMSS.xlsx`, never over an existing file.

The supported studies are 03325, 10325, 11823, 12423, 15420, and 16321.
Another study's export, a file name without the study number
(`Core_Listings_<study>_….zip`), a ZIP that is gone or isn't an export, or a
missing form gets a message saying so. A cohort or dose-level form that a
study has no columns for is left out of the listing.

## Scripting it

The work is `run()` in `src/safety_automation/ae_corelisting/AECoreListing.py`:
it takes the ZIP (a path or an open file) and returns the workbook as an
`OutputFile` (name and bytes) without touching a folder, so a script or a
future web version can call it too.

```python
from safety_automation.ae_corelisting import AECoreListing

output = AECoreListing.run("Core_Listings_15420.zip")
with open(output.name, "wb") as file:  # "15420 AE DLT YYMMDD_HHMMSS.xlsx"
    file.write(output.data)
```

Pass `study="15420"` to name the study yourself (an upload may have no file
name). When the file name names another study, `run()` refuses it, as CCI
Automation's workflows do.

## Adding a study

All of it is in `AECoreListing.py`. Add the study to `SUPPORTED_STUDIES`,
then add an entry for it in `STUDY_KEY_MAP` naming the Corelisting forms that
hold its AE, cohort, dose-level, and infusion data (when they aren't named AE,
DSCA, DSDLA, and EXINF), its columns in the `get_*_header_list` methods, and
its values in the cohort, dose-level and infusion `get_*` methods.

## Package layout

```text
src/safety_automation/
  __main__.py                  # runtime entry: python -m safety_automation
  app.py                       # the window: one WorkflowPage
  ae_corelisting/AECoreListing.py  # run(): the AE & DLT workbook, Qt-free
```
