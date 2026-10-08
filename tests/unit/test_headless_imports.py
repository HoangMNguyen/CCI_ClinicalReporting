"""The processing core must import without Qt.

The processing modules and the design values are shared with headless use
and a future web server, so importing them must never pull in PySide6. Only
the desktop shells (``*/ui``, ``*/app.py``) and the Qt parts of ``cci_ui``
may import Qt.
"""

import os
import subprocess
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[2] / "src"

CORE_MODULES = [
    "clinical_reporting",
    "clinical_reporting.additional_names",
    "clinical_reporting.data",
    "clinical_reporting.export",
    "clinical_reporting.feedback",
    "clinical_reporting.filenames",
    "clinical_reporting.models",
    "clinical_reporting.pipeline",
    "clinical_reporting.report",
    "clinical_reporting.report_columns",
    "clinical_reporting.session",
    "clinical_reporting.settings_store",
    "clinical_reporting.stacking",
    "clinical_reporting.steps",
    "clinical_reporting.telemetry",
    "clinical_reporting.validation",
    "clinical_reporting.workflow",
    "cci_automation",
    "cci_automation.util",
    "cci_automation.dsmb.DSMB",
    "cci_automation.enrollment_log.EnrollmentLog",
    "cci_automation.format_tools.change_type",
    "safety_automation",
    "safety_automation.ae_corelisting.AECoreListing",
    "peer_review_automation",
    "peer_review_automation.sds",
    # Plain file writing, run on the worker thread.
    "cci_ui.files",
    # The design values are shared with a future web front end.
    "cci_ui",
    "cci_ui.theme",
    "cci_ui.theme.tokens",
    "cci_ui.theme.qss",
]


def _tool_modules():
    """Every module of the three tools but their windows (and entry points)."""
    for package in ("cci_automation", "safety_automation", "peer_review_automation"):
        for path in sorted((SRC_DIR / package).rglob("*.py")):
            if path.name in ("app.py", "__main__.py"):
                continue
            parts = path.relative_to(SRC_DIR).with_suffix("").parts
            if parts[-1] == "__init__":
                parts = parts[:-1]
            yield ".".join(parts)


def test_core_modules_do_not_import_qt():
    script = (
        "import importlib, sys\n"
        f"for name in {CORE_MODULES + sorted(set(_tool_modules()))!r}:\n"
        "    importlib.import_module(name)\n"
        "print(sorted(m for m in sys.modules if m.startswith('PySide6')))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        cwd=SRC_DIR,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"
