# Repository Guidelines

## Project Structure & Module Organization
- Headless report modules are flat under `src/clinical_reporting/`: `models.py`, `report.py`, `pipeline.py`, `validation.py`, `data.py`, and `export.py`.
- The PySide6 UI lives in `src/clinical_reporting/ui/` and is grouped by feature: workspace, selection, rules, output, and the main window. Generated bindings live under `ui/_generated/`.
- The runtime entry point is `src/clinical_reporting/__main__.py` for `python -m clinical_reporting`. Designer assets stay in `resource/`.

## Build, Test, and Development Commands
- `python3 -m pip install -r requirements.txt` installs PySide6; tack on `pandas pytest` for analytics + tests.
- `PYTHONPATH=src python3 -m clinical_reporting` launches the UI.
- `python3 -m pytest -q` executes the unit/integration suites under `tests/`; `tests/conftest.py` inserts `src/` on `sys.path`.

## Coding Style & Naming Conventions
- Use 4-space indentation, descriptive snake_case for variables/functions, and UpperCamelCase for classes (`CLReport`, `FormItemsTab`).
- Prefer explicit type hints/docstrings for public methods; follow the patterns in `models.py` and `report.py`.
- Keep UI signal/slot wiring in its feature module and add short comments where flow crosses feature controllers.

## Testing Guidelines
- Pytest drives coverage; place fast logic tests in `tests/unit/` and workflow-style checks in `tests/integration/` with names mirroring the module (`test_clreport_reporting.py`).
- Reuse builders/fixtures to spin up `CLForm`/`CLReport` instances without touching the UI.
- Heavy sample inputs live under `tests/data/`; wrap them in helper loaders so tests remain deterministic and lightweight.

## Commit & Pull Request Guidelines
- Follow the existing short, imperative summaries from the log (`Update`, `Hoang dev (#22)`); keep the first line under 72 chars and reference issue/PR numbers in parentheses when applicable.
- Each PR should describe the motivation, include before/after notes or screenshots for UI changes, list testing commands run (`pytest`, manual UI checks), and call out any configuration steps required for reviewers.

## Agent Tips
- Many helper functions expect Pandas objects; when scripting automated checks, remember to seed `numpy`/`pandas` imports or mock them to keep headless runs lightweight.
- Avoid modifying generated `build/` or `dist/` artifacts; focus on source and tests so merges stay clean.
- Form names must not include `.` (reserved for form/item separators); additional inputs default to the file name and require a dot-free rename or they will be rejected.
- Join key selections are deduplicated in the UI; update tests accordingly when changing join behavior.
