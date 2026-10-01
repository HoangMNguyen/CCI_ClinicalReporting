"""Tests for the page preview tool (python -m clinical_reporting.ui.preview)."""

import os
import subprocess
import sys
from pathlib import Path

from clinical_reporting.ui.preview import PAGE_KEYS

SRC_DIR = Path(__file__).resolve().parents[2] / "src"


def test_screenshot_mode_saves_the_pages_asked_for_and_quits(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "clinical_reporting.ui.preview",
            "joins",
            "preview",
            "--screenshot",
            str(tmp_path),
            "--theme",
            "dark",
            "--size",
            "1000x620,1920x1001",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    saved = sorted(path.name for path in tmp_path.glob("*.png"))
    assert len(saved) == 4
    assert all(name.split("-")[0] in {"joins", "preview"} for name in saved)
    assert all("-dark-" in name for name in saved)
    assert {name.rsplit("-", 1)[1] for name in saved} == {
        "1000x620.png",
        "1920x1001.png",
    }


def test_page_names_follow_the_step_order():
    assert PAGE_KEYS == (
        "source",
        "additional",
        "forms",
        "common",
        "formitems",
        "filters",
        "joins",
        "comparisons",
        "order",
        "preview",
    )
