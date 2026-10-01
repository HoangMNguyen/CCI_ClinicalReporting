"""The PyInstaller build recipes (the ``*.spec`` files at the repository root)."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = sorted(ROOT.glob("*.spec"))
ICONS = ROOT / "src" / "cci_ui" / "assets" / "app-icons"


def _string_constants(spec: Path):
    """Every string in *spec*'s code (its docstring left out)."""
    tree = ast.parse(spec.read_text(encoding="utf-8"))
    body = tree.body[1:] if ast.get_docstring(tree) else tree.body
    for statement in body:
        for node in ast.walk(statement):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                yield node.value


def test_every_build_has_its_tools_icon():
    assert len(SPECS) == 4
    for spec in SPECS:
        text = spec.read_text(encoding="utf-8")
        package = re.search(r'^PACKAGE = "(\w+)"', text, re.MULTILINE).group(1)
        app_id = package.replace("_", "-")

        assert f'icon=app_icon("{app_id}")' in text, spec.name
        assert (ICONS / f"{app_id}.ico").is_file(), spec.name


def test_no_build_bundles_clockify_credentials():
    for spec in SPECS:
        bundled = [s for s in _string_constants(spec) if "clockify.json" in s.lower()]

        assert bundled == [], spec.name
