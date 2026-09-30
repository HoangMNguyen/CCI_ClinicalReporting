"""Tests for the component gallery (python -m cci_ui.gallery)."""

import os
import subprocess
import sys
from pathlib import Path

import shiboken6
from PySide6.QtWidgets import QApplication

from cci_ui import gallery
from cci_ui.theme.manager import theme_events
from cci_ui.theme.tokens import Color

SRC_DIR = Path(__file__).resolve().parents[2] / "src"


def test_contrast_ratio_matches_wcag():
    black, white = Color(0, 0, 0), Color(255, 255, 255)

    assert round(gallery.contrast_ratio(black, white), 1) == 21.0
    assert gallery.contrast_ratio(white, white) == 1.0


def test_every_gallery_page_builds_and_shows(make_manager):
    window, shell = gallery.build_gallery(make_manager())
    window.resize(1100, 700)
    window.show()
    try:
        for page in gallery.PAGES:
            shell.set_current(page.key)
            QApplication.processEvents()
            assert shell.stack.currentWidget() is shell.page(page.key)
        assert len(shell.sidebar.keys()) == len(gallery.PAGES)
    finally:
        window.close()


def test_a_closed_gallery_ignores_later_theme_changes(make_manager, monkeypatch):
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: raised.append(args[1]))
    window, _shell = gallery.build_gallery(make_manager())
    shiboken6.delete(window)

    theme_events().changed.emit()

    assert raised == []


def test_screenshot_mode_saves_every_page_and_quits(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cci_ui.gallery",
            "--screenshot",
            str(tmp_path),
            "--theme",
            "dark",
            "--density",
            "compact",
            "--size",
            "1000x620",
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
    assert len(saved) == len(gallery.PAGES)
    assert all(name.endswith("-dark-compact.png") for name in saved)
