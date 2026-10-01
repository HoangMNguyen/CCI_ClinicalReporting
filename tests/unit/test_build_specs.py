"""The PyInstaller build recipes (the ``*.spec`` files at the repository root)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = sorted(ROOT.glob("*.spec"))
ICONS = ROOT / "src" / "cci_ui" / "assets" / "app-icons"


def test_every_build_has_its_tools_icon():
    assert len(SPECS) == 4
    for spec in SPECS:
        text = spec.read_text(encoding="utf-8")
        package = re.search(r'^PACKAGE = "(\w+)"', text, re.MULTILINE).group(1)
        app_id = package.replace("_", "-")

        assert f'icon=app_icon("{app_id}")' in text, spec.name
        assert (ICONS / f"{app_id}.ico").is_file(), spec.name
