# Repository Guidelines

## Project Structure & Module Organization
- Core models now reside in `src/clinical_reporting/core/` (`forms.py`, `report.py`) with shared helpers under `src/clinical_reporting/services/util.py`.
- The PySide6 UI lives in `src/clinical_reporting/ui/`; tab mixins are in `ui/tabs/` and widget glue (base, navigation, run/save) in `ui/widgets/`.
- Runtime entry points are `src/clinical_reporting/app/__main__.py` (for `python -m clinical_reporting.app`) and the legacy shim `src/clinical_reporting/Clinical_Reporting.py`. Designer assets stay in `resource/`.

## Build, Test, and Development Commands
- `python3 -m pip install -r requirements.txt` installs PySide6; tack on `pandas pytest` for analytics + tests.
- `PYTHONPATH=src python3 -m clinical_reporting.app` (or `python3 src/clinical_reporting/Clinical_Reporting.py`) launches the UI.
- `python3 -m pytest -q` executes the unit/integration suites under `tests/`; `tests/conftest.py` inserts `src/` on `sys.path`.

## Coding Style & Naming Conventions
- Use 4-space indentation, descriptive snake_case for variables/functions, and UpperCamelCase for classes (`CLReport`, `FormItemsTab`).
- Prefer explicit type hints/docstrings for public methods; follow the patterns in `core/forms.py` and `core/report.py`.
- Keep UI signal/slot wiring near widget definitions and add short comments where flow jumps between mixins.

## Testing Guidelines
- Pytest drives coverage; place fast logic tests in `tests/unit/` and workflow-style checks in `tests/integration/` with names mirroring the module (`test_clreport_reporting.py`).
- Reuse builders/fixtures to spin up `CLForm`/`CLReport` instances without touching the UI.
- Heavy sample inputs live under `tests/data/`; wrap them in helper loaders so tests remain deterministic and lightweight.

## Commit & Pull Request Guidelines
- Follow the existing short, imperative summaries from the log (`Update`, `Hoang dev (#22)`); keep the first line under 72 chars and reference issue/PR numbers in parentheses when applicable.
- Each PR should describe the motivation, include before/after notes or screenshots for UI changes, list testing commands run (`pytest`, manual UI checks), and call out any configuration steps required for reviewers.

## Agent Tips
- Many helper functions expect Pandas objects; when scripting automated checks, remember to seed `numpy`/`pandas` imports or mock them to keep headless runs lightweight.
- Avoid modifying generated `build/` or `dist/` artifacts; focus on source and tests so merges stay clean.*** End Patch
