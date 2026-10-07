"""Import direction: the design system never imports the tools, and Clinical
Reporting's Qt-free core never imports its desktop front end.

The tools build on cci_ui, so cci_ui importing a tool would tie the kit to it
(and risk import cycles). Where the kit needs something from a tool, such as
the workbook a workflow returns, it takes it duck-typed (cci_ui.files).
Likewise no Clinical Reporting module outside its ``ui`` package and
``__main__.py`` imports ``clinical_reporting.ui``, so the core runs without
Qt (ADR 0002).
"""

import ast
from pathlib import Path

CCI_UI = Path(__file__).resolve().parents[2] / "src" / "cci_ui"
REPORTING = CCI_UI.parent / "clinical_reporting"
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


def _imported_modules(path: Path):
    """Every module (or module.name) *path* imports, relative ones resolved."""
    here = ["clinical_reporting", *path.relative_to(REPORTING).parent.parts]
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = here[: len(here) - node.level + 1] if node.level else []
            module = ".".join([*base, *([node.module] if node.module else [])])
            yield module
            yield from (f"{module}.{alias.name}" for alias in node.names)


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


def test_reporting_core_imports_no_ui():
    core = [
        path
        for path in sorted(REPORTING.rglob("*.py"))
        if path.relative_to(REPORTING).parts[0] not in {"ui", "__main__.py"}
    ]
    found = [
        str(path.relative_to(REPORTING))
        for path in core
        for module in _imported_modules(path)
        if module == "clinical_reporting.ui"
        or module.startswith("clinical_reporting.ui.")
    ]

    assert len(core) > 10
    assert found == []
