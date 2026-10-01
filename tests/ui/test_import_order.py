"""Every desktop module imports on its own, as the first thing a process does.

One test run imports everything in some order, which can hide a circular
import: a module that only works because another one happened to load first.
Here each module is the first import of a fresh process (a few at a time).
"""

import os
import pkgutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cci_ui
import clinical_reporting.ui

SRC_DIR = Path(__file__).resolve().parents[2] / "src"


def _modules():
    names = []
    for package in (cci_ui, clinical_reporting.ui):
        prefix = package.__name__ + "."
        for module in pkgutil.walk_packages(package.__path__, prefix):
            if not module.name.endswith("__main__"):
                names.append(module.name)
    names += [
        "safety_automation.app",
        "peer_review_automation.app",
        "cci_automation.app",
    ]
    return names


def _import_alone(name: str) -> str:
    """Why *name* fails to import first in a new process ("" if it imports)."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {name}"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR), "QT_QPA_PLATFORM": "offscreen"},
        timeout=120,
        check=False,
    )
    return result.stderr.strip().splitlines()[-1] if result.returncode else ""


def test_each_module_imports_first_in_a_fresh_process():
    modules = _modules()
    with ThreadPoolExecutor(max_workers=8) as pool:
        errors = dict(zip(modules, pool.map(_import_alone, modules)))

    assert len(modules) > 30
    assert {name: error for name, error in errors.items() if error} == {}
