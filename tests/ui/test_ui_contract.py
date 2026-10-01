"""The behavior mixins and the code-built pages agree on widget names.

The mixins reach widgets as ``self.ui.<name>``; the pages provide them
through ``EXPORTS`` (see ``clinical_reporting.ui.contract``). These tests
fail when either side changes without the other.
"""

import ast
from pathlib import Path

from PySide6.QtWidgets import QMainWindow

from clinical_reporting import steps
from clinical_reporting.ui import window as window_module
from clinical_reporting.ui.contract import UI_CONTRACT
from clinical_reporting.ui.main_ui import (
    PAGE_CLASSES,
    WINDOW_NAMES,
    ClinicalReportingUi,
)

UI_DIR = Path(window_module.__file__).parent
#: ClinicalReportingUi's own methods, called by the window.
UI_METHODS = {"setup"}


def _built_ui():
    host = QMainWindow()
    ui = ClinicalReportingUi()
    ui.setup(host)
    return host, ui


def _names_used_by_mixins():
    """Every ``<x>.ui.<name>`` and ``getattr(<x>.ui, "<name>")`` in ui/*.py."""
    used = {}
    for path in sorted(UI_DIR.glob("*.py")):
        if path.name in {"main_ui.py", "contract.py", "preview.py"}:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "ui"
            ):
                used.setdefault(node.attr, f"{path.name}:{node.lineno}")
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"getattr", "hasattr"}
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Attribute)
                and node.args[0].attr == "ui"
                and isinstance(node.args[1], ast.Constant)
            ):
                used.setdefault(node.args[1].value, f"{path.name}:{node.lineno}")
    return used


def test_every_contract_name_is_a_widget_of_the_built_ui(qapp):
    _host, ui = _built_ui()

    missing = sorted(name for name in UI_CONTRACT if not hasattr(ui, name))

    assert missing == []


def test_no_name_is_exported_twice():
    exported = [name for page in PAGE_CLASSES for name in page.EXPORTS]

    assert len(exported) == len(set(exported))
    assert WINDOW_NAMES.isdisjoint(exported)


def test_every_page_names_its_step():
    keys = tuple(page.KEY for page in PAGE_CLASSES)

    assert keys == steps.STEP_KEYS  # The steps' badges are keyed by these.
    assert all(page.SECTION and page.ICON for page in PAGE_CLASSES)


def test_mixins_only_use_contract_names():
    used = _names_used_by_mixins()

    unknown = {
        name: where
        for name, where in used.items()
        if name not in UI_CONTRACT | UI_METHODS
    }
    assert unknown == {}
    assert len(used) > 50, "the scan found too few names; is UI_DIR right?"


def test_every_contract_name_is_used():
    assert UI_CONTRACT - set(_names_used_by_mixins()) == set()


def test_no_behavior_method_is_hidden_by_the_window():
    """compose_behaviors skips names the window already has; none may clash."""
    hidden = []
    for behavior in window_module.BEHAVIORS:
        for name, value in behavior.__dict__.items():
            if name.startswith("__") or not callable(value):
                continue
            if window_module.Widget.__dict__.get(name) is not value:
                hidden.append(f"{behavior.__name__}.{name}")

    assert hidden == []
