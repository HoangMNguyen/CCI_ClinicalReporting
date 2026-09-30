"""The processing core must import without Qt.

Everything outside the desktop shells (``*/ui``, ``*/app.py``, ``cci_ui``) is
shared with headless use and a future web server, so importing it must never
pull in PySide6.
"""

import os
import subprocess
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[2] / "src"

CORE_MODULES = [
    "clinical_reporting",
    "clinical_reporting.data",
    "clinical_reporting.export",
    "clinical_reporting.feedback",
    "clinical_reporting.filenames",
    "clinical_reporting.models",
    "clinical_reporting.pipeline",
    "clinical_reporting.report",
    "clinical_reporting.session",
    "clinical_reporting.settings_store",
    "clinical_reporting.telemetry",
    "clinical_reporting.validation",
    "cci_automation",
    "cci_automation.util",
    "cci_automation.dsmb.DSMB",
    "cci_automation.enrollment_log.EnrollmentLog",
    "cci_automation.clockify.Clockify",
    "cci_automation.format_tools.change_type",
    "safety_automation",
    "safety_automation.util",
    "safety_automation.ae_corelisting.AECoreListing",
    "peer_review_automation",
    "peer_review_automation.sds",
]


def test_core_modules_do_not_import_qt():
    script = (
        "import importlib, sys\n"
        f"for name in {CORE_MODULES!r}:\n"
        "    importlib.import_module(name)\n"
        "print(sorted(m for m in sys.modules if m.startswith('PySide6')))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=SRC_DIR,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"
