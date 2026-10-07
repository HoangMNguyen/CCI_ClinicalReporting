"""The Qt-free test folders import no Qt, so they run on requirements-core.txt.

``tests/unit`` and ``tests/integration`` are read as syntax trees. Importing
``PySide6``, ``shiboken6``, ``cci_ui``, ``clinical_reporting.ui``, a tool's
desktop app (``app`` or ``__main__``) or ``tests.ui`` there fails this test,
apart from the ``cci_ui`` modules that need no Qt (``files``,
``theme.tokens``, ``theme.qss``) and imports that follow an
``importorskip`` of a Qt package in the same function, which skips without
Qt instead of failing. Desktop behaviour is tested in ``tests/ui``.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QT_FREE_FOLDERS = ("tests/unit", "tests/integration")
QT_PACKAGES = (
    "PySide6",
    "shiboken6",
    "cci_ui",
    "clinical_reporting.ui",
    "clinical_reporting.__main__",
    "cci_automation.app",
    "cci_automation.__main__",
    "safety_automation.app",
    "safety_automation.__main__",
    "peer_review_automation.app",
    "peer_review_automation.__main__",
    "tests.ui",
)
QT_FREE_CCI_UI = ("cci_ui.files", "cci_ui.theme.tokens", "cci_ui.theme.qss")


def _within(module, packages):
    return any(module == name or module.startswith(name + ".") for name in packages)


def _needs_qt(module):
    return _within(module, QT_PACKAGES) and not _within(module, QT_FREE_CCI_UI)


def _imported_modules(node):
    """Every module an import statement loads, down to the imported names."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and not node.level:
        return [f"{node.module}.{alias.name}" for alias in node.names]
    return []


def _skips_without_qt(node):
    """Whether ``node`` is an ``importorskip`` call for a Qt package."""
    if not isinstance(node, ast.Call) or not node.args:
        return False
    called = node.func
    if isinstance(called, ast.Attribute):
        name = called.attr
    else:
        name = getattr(called, "id", None)
    module = node.args[0]
    return (
        name == "importorskip"
        and isinstance(module, ast.Constant)
        and isinstance(module.value, str)
        and _needs_qt(module.value)
    )


def _skipping_imports(tree):
    """The imports that come after a Qt ``importorskip`` in their function."""
    skipping = set()
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        skips = [n.lineno for n in ast.walk(function) if _skips_without_qt(n)]
        if skips:
            skipping.update(
                id(node)
                for node in ast.walk(function)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                and node.lineno > min(skips)
            )
    return skipping


def _qt_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    skipping = _skipping_imports(tree)
    for node in ast.walk(tree):
        if id(node) in skipping:
            continue
        qt_modules = [m for m in _imported_modules(node) if _needs_qt(m)]
        if qt_modules:
            where = f"{path.relative_to(ROOT).as_posix()}:{node.lineno}"
            yield f"{where}: {', '.join(qt_modules)}"


def test_the_qt_free_test_folders_import_no_qt():
    files = [
        path
        for folder in QT_FREE_FOLDERS
        for path in sorted((ROOT / folder).rglob("*.py"))
    ]
    found = [line for path in files for line in _qt_imports(path)]

    assert len(files) > 30
    assert not found, (
        "These imports need Qt; move their tests to tests/ui:\n" + "\n".join(found)
    )
