# Clinical Reporting Tool

Desktop application for assembling clinical report outputs through a guided PySide6 UI. Users can pick source forms, choose common or per-form items, set joins/filters, comparisons, and export configured report settings.

## Features
- Use Core Listing and other sources from both Excel and CSV files.
- Form, common, and per-form item pickers with regex-based case-insensitive search filters.
- Join, rename, comparison, and filter configuration tables tailored for clinical datasets.
- Save/load settings plus quick run helpers for generating reports.
- Form names cannot include `.` because it is reserved for the form/item separator. Additional inputs default to the file name and must be renamed to remove dots.

## Setup

### 1. Install dependencies
```bash
python -m pip install -r requirements.txt
python -m pip install pytest  # test runner
```

### 2. Run the application
Primary entry point:
```bash
PYTHONPATH=src python -m clinical_reporting.app
```

Legacy compatibility entry point:
```bash
python src/clinical_reporting/Clinical_Reporting.py
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

Run a single test file while iterating:
```bash
python -m pytest -q tests/unit/test_join_deduplication.py
```

Useful local debugging options:
```bash
python -m pytest -x -vv
```

Testing notes:
- `tests/conftest.py` inserts both project root and `src/` into `sys.path`.
- Larger sample artifacts are stored in `tests/data/`.
- Keep logic tests in `tests/unit/` and workflow-level checks in `tests/integration/`.

## Project Structure

```text
src/clinical_reporting/
  app/
    __main__.py                # main runtime entry: python -m clinical_reporting.app
  core/
    forms.py                   # CLForm and related form parsing/model logic
    report.py                  # CLReport and report configuration/execution logic
  services/
    util.py                    # shared helper functions used across layers
  ui/
    main_widget.py             # primary PySide6 widget and app wiring
    tabs/                      # tab mixins (forms, items, filters, comparisons, settings)
    widgets/                   # base/navigation/run-save widget glue
    form.ui                    # Qt Designer source layout
    ui_form.py                 # generated UI binding module
  Clinical_Reporting.py        # legacy launcher shim (backward compatibility)

resource/                      # Designer assets and generated UI resources
tests/
  unit/                        # fast logic-focused tests
  integration/                 # workflow/reporting behavior tests
  data/                        # sample test inputs
```

## Building the Executable

If you need a standalone executable, install PyInstaller first:
```bash
python -m pip install pyinstaller
```

Then build:
```bash
pyinstaller --onefile --strip --name "CCI Clinical Reporting V1.00" --windowed "src/clinical_reporting/Clinical_Reporting.py" --exclude PyQt5 --exclude matplotlib
```

## Notes
- The UI resizes dynamically.
- Avoid modifying generated `build/` and `dist/` artifacts in normal development workflows.
