# CCI_ClinicalReporting

Four PySide6 desktop apps for clinical trial reporting: Clinical Reporting (the configurable report builder), CCI Automation, Safety Automation and Peer Review Automation. They share a Qt-free backend (`clinical_reporting`) and a design system (`cci_ui`). Setup, layout and how the tools fit together: `README.md`.

## Environment
- The checkout path contains a space (`Current Work`): quote paths.
- `source .venv/bin/activate` (Python 3.14, locked versions), then `export PYTHONPATH=src`.
- pytest makes Qt offscreen and blanks the usage counter itself (`tests/conftest.py`). Any other Qt command (the apps, `python -m clinical_reporting.ui.preview`, `python -m cci_ui.gallery`) needs the prefix `env -u WAYLAND_DISPLAY -u DISPLAY -u QT_QPA_PLATFORMTHEME QT_QPA_PLATFORM=offscreen CLINICAL_REPORTING_RUN_COUNTER_URL= CLINICAL_REPORTING_RUN_COUNTER_TOKEN=`: the desktop exports Wayland settings, and the blank counter keeps runs off the production usage endpoint.
- Dropbox syncs this folder to the user's Windows PC, where the executables are built: after a merge, update local `main`.

## Privacy
- Real study exports live only in `~/cci-golden/exports`, never in the repo. Never open or print their contents.
- Never put anything from a real export (study numbers, counts, IDs, dates, values) in commits, PR titles or bodies, or anything else pushed to GitHub; write "a real export" or "study A".
- Tests, docs and examples use made-up data: the DEMO01 sample (`clinical_reporting.sample_data`), small DataFrames, tiny ZIPs in `tmp_path`.

## Code
- Qt-free core: all of `clinical_reporting` except `__main__.py` and `ui/`, and every tool except its `__main__.py` and `app.py` (enforced by `tests/unit/test_headless_imports.py` and `tests/unit/test_layering.py`). Decisions about output belong in the core; front ends only collect input and show results.
- Use the domain words in `GLOSSARY.md`.
- Each package's README documents its tool (`src/<package>/README.md`); Clinical Reporting's has the base-report API and the package layout.

## Tests
- `python -m pytest -q` runs everything; `python -m pytest -q tests/unit tests/integration` needs no Qt (`tests/unit/test_suites_are_qt_free.py` fails on a Qt import there).
- Test through public seams (a module's public functions, a mixin's `click_*`/`update_*_ui` handlers, a workflow's `run()`): no private calls, no mocks of internal collaborators; stubbing Qt dialogs, the clock, the network or the environment is fine. Expected values are literals. No tests of wiring, source text or incidental defaults.

## Output and the golden harness
- Output: every workbook part byte for byte (but `docProps/core.xml`, the creation time), output file names, saved-setting JSON, the telemetry payload and the app windows.
- A change meant to keep output must pass the harness in `~/cci-golden` (outside the repo and Dropbox). From that folder: `python golden.py run --src <worktree>/src --out runs/<label>`, then `python golden.py diff runs/main-a runs/<label>` must print ALL IDENTICAL and exit 0 (25 cases: 22 on real exports, 3 Clinical Reporting cases on DEMO01).
- Its case ids hold study numbers: report only "25 cases, ALL IDENTICAL". `runs/` keeps the baselines `main-a` (matches `main`), `main-a-plan1`, `main-b` and `tip`; never delete or rebaseline them without asking.

## Changes, PRs and merging
- Work in a worktree under `.claude/worktrees/<name>` (git-ignored), on its own branch. One commit per step: an imperative subject in the repo's style, no co-author lines.
- Before a PR: the full suite, `python -m ruff check src tests` (CI runs it) and `python -m ruff format --check` on the changed `.py` files; don't reformat files you didn't change.
- PR body: what changes for users; how it was checked (which harness cases ran on real exports, which on DEMO01); not changed; not checked yet.
- Merge only when every CI check is green (Full suite and Core only, no Qt, on Ubuntu and Windows), the PR is mergeable and `main` hasn't moved since CI ran. Squash-merge; keep the branch on origin.
- After merging: update local `main`; remove the worktree, local branch and `/tmp` scratch; list the user's Windows follow-ups (exe build and self-test, `README.md` "Building the executables"; hands-on checks).
