"""Tests for the shared start-up: look, self-test, and the error dialog hook."""

import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase

from cci_ui import app as cci_app
from cci_ui.assets import assets_root

SRC_DIR = Path(__file__).resolve().parents[2] / "src"


def test_create_app_applies_the_cci_look(themed_app, ini_settings):
    app, manager = cci_app.create_app(
        app_id="test",
        name="Theme test",
        version="1.0",
        settings=ini_settings,
        install_excepthook=False,
    )
    try:
        assert app is themed_app
        assert "Inter" in QFontDatabase.families()
        assert app.font().families()[0] == "Inter"
        assert assets_root().is_dir()
        assert app.styleSheet()
    finally:
        manager.setParent(None)
        manager.deleteLater()


def test_self_test_runs_a_real_app_and_quits(tmp_path):
    """A new process, as a built executable would run with CCI_UI_SELFTEST set."""
    report_path = tmp_path / "selftest.json"
    script = (
        "import sys\n"
        "from PySide6.QtCore import QSettings\n"
        "from cci_ui.app import create_app\n"
        "app, _ = create_app(app_id='selftest', name='Self test',\n"
        "    settings=QSettings(sys.argv[1], QSettings.Format.IniFormat))\n"
        "sys.exit(app.exec())\n"
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(SRC_DIR),
        "QT_QPA_PLATFORM": "offscreen",
        cci_app.SELF_TEST_ENV: str(report_path),
    }

    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "appearance.ini")],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    # A fresh process, so component styles can only come from create_app itself.
    assert report["components_styled"] is True
    assert report["style"] == "fusion"
    assert report["font_family"] == "Inter"
    assert report["assets_found"] is True


def test_error_hook_is_installed_once_and_passes_ctrl_c_through(monkeypatch):
    seen = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: seen.append(args[0]))

    cci_app._install_excepthook()
    hook = sys.excepthook
    cci_app._install_excepthook()

    assert sys.excepthook is hook
    hook(KeyboardInterrupt, KeyboardInterrupt(), None)
    # Offscreen (as in tests) the hook never opens a dialog; errors go on.
    hook(ValueError, ValueError("bad value"), None)
    assert seen == [KeyboardInterrupt, ValueError]
