# CCI Clinical Reporting & Automation Suite

A suite of four PySide6 desktop applications for clinical trial reporting,
built on a single shared headless backend (`clinical_reporting`) and a shared
design system (`cci_ui`). The Clinical Reporting Tool is the flagship
configurable report builder; the three automation apps cover
department-specific workflows. Each app runs from source with
`python -m <package>` and ships as its own standalone executable.

## Applications

| Application | What it produces | Package and details |
| --- | --- | --- |
| Clinical Reporting Tool | Configurable clinical report exports from Corelisting/CSV/Excel data | [`clinical_reporting`](src/clinical_reporting/README.md) |
| CCI Automation | Enrollment Logs, DSMB Reports, formatting fixes | [`cci_automation`](src/cci_automation/README.md) |
| Safety Automation | Corelisting AE & DLT listing workbook | [`safety_automation`](src/safety_automation/README.md) |
| Peer Review Automation | Medidata SDS peer-review error report | [`peer_review_automation`](src/peer_review_automation/README.md) |

All four share the design system, [`cci_ui`](src/cci_ui/README.md).

## Setup

Python 3.14 is required; `requirements-lock.txt` is compiled for it. Create
the environment once per machine:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
```

On Windows cmd.exe, activate with `.venv\Scripts\activate.bat`. If
PowerShell blocks `Activate.ps1`, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. If `python` is not
on PATH on Windows, use the `py` launcher (`py -m venv .venv`, etc.).

The requirements files build on each other:

| File | Contents | For |
|---|---|---|
| `requirements-core.txt` | The Qt-free processing engine (pandas, numpy, xlsxwriter, openpyxl, python-dateutil) | Run reports headless or on a server |
| `requirements.txt` | Core + PySide6 | Run the desktop apps |
| `requirements-dev.txt` | Desktop + `pytest`, `pytest-cov` and `ruff` | Develop and test |
| `requirements-build.txt` | Desktop + PyInstaller | Build the executables |

Each dependency is bounded to its current major version so DSMB and safety
outputs stay reproducible; raise a bound deliberately after testing. Those
four files are the source of `requirements-lock.txt`, which pins one exact
version per package for both Linux and Windows. Development and the builds
install the lock, so everyone runs the same versions; it needs plain `pip`,
not `uv`.

The packages are not pip-installed; every app imports from `src/` directly.
In each terminal session, activate the venv and put `src/` on the Python path
(`export PYTHONPATH=src` in bash, `$env:PYTHONPATH = "src"` in PowerShell,
`set PYTHONPATH=src` in cmd.exe), then run any app the same way on every
platform:

```bash
python -m clinical_reporting
python -m cci_automation
python -m safety_automation
python -m peer_review_automation
```

One-off alternative on bash without exporting:
`PYTHONPATH=src python -m clinical_reporting`.

### Upgrading a library

Change the bound in the requirements file the package comes from and rerun
the compile below; to move to newer versions within the existing bounds, add
`--upgrade` to it. `uv` is needed only here:

```bash
uv pip compile requirements-dev.txt requirements-build.txt --universal \
    --python-version 3.14 -o requirements-lock.txt
```

Install the new lock, run `python -m pytest -q`, and commit the lock on its
own, with the reason for the change.

## How the tools fit together

### Qt-free core, thin front ends

The processing modules never import PySide6: `clinical_reporting` (everything
except `__main__.py` and `ui/`), the automation tools (everything except each
tool's `__main__.py` and `app.py`), and `cci_ui`'s design values.
`tests/unit/test_headless_imports.py` enforces this, so the core can run
headless or behind a future web front end. Front ends
(`clinical_reporting/ui/` and each tool's `app.py`) only collect input and
show results; decisions about the output belong in the core.

### Shared backend

The automation apps take what they share from `clinical_reporting` rather
than carrying their own copies:

- `clinical_reporting.workflow`:
  - `OutputFile`, what every workflow returns: a file name and the
    workbook's bytes.
  - `named_output(data, file_name=..., default_name=...)` wraps a
    workbook's bytes in an `OutputFile` named
    `<file name, or the default if blank> YYMMDD_HHMMSS.xlsx`; pass `now` to
    stamp it with another time (a server passes the user's local time).
  - `WorkflowInputError` for problems the user can fix, and
    `UnsupportedStudyError` for a study a workflow doesn't cover.
  - `reading_input` turns a missing, locked or unreadable input file into a
    `WorkflowInputError` that names the file. `read_corelisting` reads a
    Corelisting export through it, with
    `clinical_reporting.data.read_data_dict_zip_corelisting`.
  - `study_named_by` reads the study from a ZIP's file name, and
    `check_study` refuses a ZIP named for another study than the one chosen
    (CCI Automation).
- `clinical_reporting.filenames.output_file_name` makes the
  `<name> YYMMDD_HHMMSS.xlsx` file names.
- `clinical_reporting.data.parse_study_name` reads the study from a file
  name (Safety Automation directly; `study_named_by` builds on it).
- `clinical_reporting.export.get_named_excel_formats` provides shared Excel
  cell styles (the DSMB modules).
- `clinical_reporting.export.to_short_date_string` writes dates as
  `m/d/yyyy` without leading zeros (CCI Automation's
  `util.remove_leading_zeros_from_dates`).

### What the automation tools share

CCI Automation, Safety Automation and Peer Review Automation work the same
way. Each workflow is one page (`cci_ui`'s `WorkflowPage`): choose the inputs
and an output folder (remembered), accept or change the suggested file name,
and Run. The work runs in the background and is saved as
`<name> YYMMDD_HHMMSS.xlsx`, never over an existing file. Problems the user
can fix (an unsupported study, a missing or unreadable file, a missing form
or sheet) are shown as messages, not tracebacks.

Each workflow's `run()` is Qt-free and returns the workbook as an `OutputFile`
without touching the user's folders, so it can be scripted like the
[reporting engine](src/clinical_reporting/README.md#programmatic--api-usage).
Each tool's README has an example.

### Design system

`src/cci_ui` holds the colors, sizes and type, the components, the icons, the
small tools' window and workflow page, and the app icons; every window is
built from it in Python code. Light and dark mode and the Comfortable or
Compact density are shared by all four tools, and every window reopens where
it was. Check a change in the gallery, which shows every component:

```bash
python -m cci_ui.gallery
```

How to change the theme, components, icons and app icons is in the
[design system's README](src/cci_ui/README.md).

### Repository layout

```text
src/
  clinical_reporting/          # Clinical Reporting Tool and the shared backend
  cci_ui/                      # shared design system for all four tools
  cci_automation/              # Enrollment Log, DSMB, format tools
  safety_automation/           # Corelisting AE & DLT report
  peer_review_automation/      # Medidata SDS peer review
tests/
  unit/                        # fast Qt-free logic tests
  integration/                 # Clinical Reporting end-to-end report/settings/API tests
  ui/                          # design-system, window and page tests (need Qt)
docs/design/clinical-reporting-mockup.html  # the approved mockup the design follows
*.spec, build_support.py       # PyInstaller builds (see Building the executables)
```

Each package's README describes its own files.

## Testing and linting

`pytest` is used for both unit and integration tests:

```bash
python -m pytest -q                    # the full suite
python -m pytest -q tests/unit         # unit tests only
python -m pytest -q tests/integration  # integration tests only
python -m pytest -q tests/ui           # design-system, window and page tests only
python -m pytest -q tests/unit tests/integration   # no Qt needed (requirements-core.txt + pytest)
python -m pytest -q tests/ui/test_join_deduplication.py  # one file
python -m pytest -x -vv                # stop at the first failure, verbose
```

Ruff is configured in `pyproject.toml`:

```bash
python -m ruff check src tests --fix   # apply all configured safe lint fixes
python -m ruff check src tests         # verify without changing files
python -m ruff format src tests        # an intentional repository-wide format pass
```

VS Code will recommend the Ruff extension and apply the same fixes whenever a
Python file is saved. Unsafe Ruff fixes remain disabled by default.

GitHub Actions (`.github/workflows/tests.yml`) runs the lint check and the
full suite on Linux and Windows for every push and pull request, and
`tests/unit` and `tests/integration` on `requirements-core.txt` alone.

Testing notes:

- `tests/conftest.py` inserts both project root and `src/` into `sys.path`, runs
  Qt offscreen (no windows appear), blanks the usage counter's endpoint so no
  test counts a run (even with a local `telemetry.json`), and provides one
  shared `qapp` fixture.
- Tests build their own made-up data in code (Clinical Reporting's
  `clinical_reporting/ui/sample_data.py`, small DataFrames, and tiny ZIPs
  written to pytest's `tmp_path`) and never read real study exports. Keep
  real exports outside the repository: Git ignores `tests/data/` and every
  `.zip`, `.csv` and Excel file so one can't be committed by accident, but
  the repository folder still syncs to Dropbox.
- `tests/unit/` holds Qt-free logic (the automation workflows' `run()` tests
  are there too) and `tests/integration/` Clinical Reporting's end-to-end
  report, settings and API tests; both run on `requirements-core.txt` alone,
  and `tests/unit/test_suites_are_qt_free.py` fails on a Qt import there.
  Desktop behaviour (the shared design system `cci_ui`, whole windows and the
  window's pages) goes in `tests/ui/`.
- Slow work (reading inputs, previews, exports, the tools' workflows) runs on
  a background thread. Tests that wait for it use the `settle` fixture in
  `tests/ui/conftest.py`, which blocks in `TaskRunner.wait()` so the worker
  can run; a `QTest.qWait` loop holds Python's GIL and slows the worker down
  many times over. Test stand-ins without a `task_runner` run the work
  directly (`cci_ui.tasks.run_task`).
- The tests that guard the look (the tokens against the mockup, no stray
  windows, the icons) are described in the
  [design system's README](src/cci_ui/README.md). Clinical Reporting's own
  testing notes (tagged status messages, sidebar badges) are in its
  [README](src/clinical_reporting/README.md#testing-notes), and the tests
  that guard its pages under
  [Changing the UI](src/clinical_reporting/README.md#changing-the-ui).

## Building the executables

Each application has a PyInstaller spec file at the repository root. Install
the locked versions, then build the app(s) you need:

```bash
python -m pip install -r requirements-lock.txt
python -m PyInstaller "CCI Clinical Reporting.spec"
python -m PyInstaller "CCI Automation.spec"
python -m PyInstaller "Safety Automation.spec"
python -m PyInstaller "Peer Review Automation.spec"
```

Executables land in `dist/`; don't edit the generated `build/` and `dist/`
folders by hand. All four builds are one-file, windowed, and exclude
PyQt5/matplotlib. Each gets its tool's
[icon](src/cci_ui/README.md#app-icons) and the design system's fonts and
icons. Clinical Reporting also embeds `src/clinical_reporting/telemetry.json`,
which must exist locally before building (see its
[README](src/clinical_reporting/README.md#usage-telemetry)); the other three
need no bundled data files.

If the repository is in a Dropbox folder, mark `build/` and `dist/` as
ignored by Dropbox first (once per clone and machine), or Dropbox locks the
new executable while PyInstaller writes its icon and version resources and
the build fails with `EndUpdateResourceW`:

```powershell
New-Item -ItemType Directory -Force build, dist | Out-Null
Set-Content -Path build -Stream com.dropbox.ignored -Value 1
Set-Content -Path dist -Stream com.dropbox.ignored -Value 1
```

To check a build without clicking through it, run it with
`CCI_UI_SELFTEST` set to a file path: the app starts, writes what it loaded
(style, font, assets, window icon, and, for Clinical Reporting, whether it
has its bundled `telemetry.json`) to that file as JSON, and quits with exit
code 0 (1 if a check failed; the report then says why under `error`). All
four tools support it:

```powershell
$env:CCI_UI_SELFTEST = "$PWD\dist\selftest.json"
$exe = Get-Item ".\dist\CCI Clinical Reporting V*.exe" | Sort-Object LastWriteTime | Select-Object -Last 1
Remove-Item .\dist\selftest.json -ErrorAction SilentlyContinue
$run = Start-Process -FilePath $exe -Wait -PassThru
Remove-Item Env:CCI_UI_SELFTEST
$run.ExitCode; Get-Content .\dist\selftest.json
```

### Versioning a release

There is **one spec per application, not one per version**. The spec file
names are permanent; the version lives in exactly one place per app:

| Application | Version constant |
| --- | --- |
| Clinical Reporting Tool | `src/clinical_reporting/__init__.py` |
| CCI Automation | `src/cci_automation/__init__.py` |
| Safety Automation | `src/safety_automation/__init__.py` |
| Peer Review Automation | `src/peer_review_automation/__init__.py` |

To cut a release, bump that one `__version__` string and rebuild.
`build_support.py` reads it and stamps it into both the executable's file
name (`CCI Automation V<version>.exe`) and its Windows VERSIONINFO resource, so
the version shown in Explorer under **Properties -> Details** can never drift
from the version in the file name. The running app can also report its own
version via `<package>.__version__`.

For a one-off build without editing the source, override with an environment
variable:

```powershell
$env:APP_VERSION = "1.26-test"; python -m PyInstaller "CCI Automation.spec"
Remove-Item Env:APP_VERSION  # or every later build gets 1.26-test too
```

```bash
APP_VERSION=1.26-test python -m PyInstaller "CCI Automation.spec"
```

A suffix such as `-test` shows in the file name and as the Product version in
Properties -> Details; the File version there uses only the digits
(1.26.0.0).

The `.spec` files and `build_support.py` are tracked in Git like any other
source file, so a spec diff always means a real change to the build recipe,
never a version bump.
