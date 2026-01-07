# Clinical Reporting Tool

Desktop application for assembling clinical report outputs through a guided PySide6 UI. Users can pick source forms, choose common or per-form items, set joins/filters, comparisons, and export configured report settings.

## Features
- Use Core Listing and other sources both Excel and CSV files as inputs.
- Form, common and per-form item pickers with regex-based case insensitive search filters.
- Join, rename, comparison and filter configuration tables tailored for clinical datasets.
- Save/load settings plus quick run helpers for generating reports.

## Project Structure
- `src/clinical_reporting/core/`: Core domain models (`forms.py`, `report.py`).
- `src/clinical_reporting/services/util.py`: Shared helpers.
- `src/clinical_reporting/ui/`: PySide6 UI, tabs, and widget mixins; entry widget in `main_widget.py`.
- `resource/`: Qt Designer `.ui` sources and generated `ui_form.py`.
- `tests/`: Pytest suites (unit + integration).

## Setup
```bash
python3 -m pip install -r requirements.txt        # PySide6 UI deps
# Optional for analytics/tests
python3 -m pip install pandas pytest
```

## Building the Executable

To build the application into a standalone executable, use the following `pyinstaller` command. This will create an optimized `.exe` file named "CCI Cilnical Reporting V1.00" and exclude certain dependencies for a smaller file size.

```bash
pyinstaller --onefile --strip --name "CCI Cilnical Reporting V1.00" --windowed "Clinical_Reporting.py" --exclude PyQt5 --exclude matplotlib
```

**Note**: Ensure that PyInstaller is installed as listed in the `requirements.txt`.

## Run the App
```bash
PYTHONPATH=src python3 -m clinical_reporting.app
# or
python3 src/clinical_reporting/Clinical_Reporting.py
```

## Tests
```bash
python -m pytest -q
```

## Notes
- The UI resizes dynamically.
