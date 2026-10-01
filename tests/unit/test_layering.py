"""The design system (cci_ui) never imports the tools.

The tools build on cci_ui, so cci_ui importing a tool would tie the kit to it
(and risk import cycles). Where the kit needs something from a tool, such as
the workbook a workflow returns, it takes it duck-typed (cci_ui.files).
"""

import ast
from pathlib import Path

CCI_UI = Path(__file__).resolve().parents[2] / "src" / "cci_ui"
TOOL_PACKAGES = (
    "clinical_reporting",
    "cci_automation",
    "safety_automation",
    "peer_review_automation",
)


def _imported_packages(path: Path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module.split(".")[0]


def test_cci_ui_imports_no_tool():
    files = sorted(CCI_UI.rglob("*.py"))
    found = {
        str(path.relative_to(CCI_UI)): sorted(
            set(_imported_packages(path)) & set(TOOL_PACKAGES)
        )
        for path in files
    }

    assert len(files) > 20
    assert {name: tools for name, tools in found.items() if tools} == {}
