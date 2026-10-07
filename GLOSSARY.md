# CCI Clinical Reporting

Tools that turn a study's clinical-trial data exports into Excel reports for the CCI team: a configurable report builder (Clinical Reporting) and department-specific automations built alongside it.

## Language

### Inputs

**Study**:
A clinical trial the tools report on, identified by its five-digit study number (for example 15420).

**Corelisting export**:
The ZIP of per-form data files exported for one study; the main input of every tool except the peer review.
_Avoid_: core listing, listing ZIP

**Form**:
One data collection form of a study (for example DM or AE): one data file in a Corelisting export, or one additional input.
_Avoid_: source, file, extra form

**Item**:
One field recorded on a form, such as Subject, Visit or Age; in a report, each chosen item becomes a column.
_Avoid_: field, column (column means a report's column)

**Common item**:
An item present in every loaded form, including additional inputs; forms are joined on selected common items. For example, an additional input without Visit, even one not selected, takes Visit out of the common items.
_Avoid_: shared item

**Form item**:
An item that is not a common item; the report names its column after its form (for example DM.Age).
_Avoid_: per-form item, form-specific item

**Cut-off date**:
The last date a report includes: records of a Corelisting export dated after it are left out; additional inputs are never cut.
_Avoid_: cutoff

**Additional input**:
A CSV or Excel file the user adds next to a Corelisting export so its columns can be reported as if it were another form.
_Avoid_: extra input, extra file

### Reports

**Saved setting**:
A named, reusable definition of a Clinical Reporting report for one study: which forms and items, how they join, the filters and comparisons, the column order and names, and the names given to additional inputs. It does not hold the cut-off date.
_Avoid_: configuration, config, template

**Join order**:
The sequence in which selected forms are combined: the first starts the report, and each later form is joined to the accumulated result on selected common items.
_Avoid_: merge order

**Filter**:
A rule that keeps only the rows whose item matches a value, applied to each form before the forms are joined.
_Avoid_: static filter

**Comparison**:
A rule that keeps only the rows where one item compares with another (for example an end date on or after the start date), applied after the forms are joined.
_Avoid_: dynamic filter

**Base report**:
The table Clinical Reporting produces by applying a saved setting to a Corelisting export (with its cut-off date and additional inputs). Exported unchanged it is the Clinical Reporting workbook; an automation may build on it instead.
_Avoid_: base table, raw report

**Automation**:
A workflow that turns a study's inputs into one department-specific workbook (DSMB report, Enrollment Log, AE & DLT listing, SDS peer review); future automations build on a base report.
_Avoid_: script, tool (when the workflow, not the app, is meant)

### Versions

**Desktop version**:
Clinical Reporting run as a program on a user's PC.
_Avoid_: local version, exe

**Web version**:
Clinical Reporting used in a browser, with the same behavior, inputs and outputs as the desktop version, that keeps nothing between sessions: saved settings and workbooks stay as files on the user's machine.
_Avoid_: cloud version, AWS version, online version
