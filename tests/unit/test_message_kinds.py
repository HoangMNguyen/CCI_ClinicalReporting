"""Every message shown in a Clinical Reporting status label has a kind.

Status labels become styled banners, which read how serious a message is
from its ``feedback`` kind. Text written straight into a status label shows
as neutral info, so this test fails on text built inside the call that sets
it: literals, f-strings, ``"sep".join(...)``, ``+``/``%``, ``str(...)``, or
either branch of ``a if cond else b`` / ``a or b``. Wrap it in
``feedback.info/success/warning/error``. A plain string passed in through a
variable can't be seen here; the kind tests next to each flow cover those.
"""

import ast
from pathlib import Path

UI_DIR = Path(__file__).resolve().parents[2] / "src" / "clinical_reporting" / "ui"
#: The window's status labels, which may also be set directly with setText.
STATUS_LABELS = {
    "banner_input_file",
    "label_run_confirmation",
    "label_save_confirmation",
    "label_setting",
}


def _is_untagged_text(node: ast.expr) -> bool:
    """True for text built in place rather than a tagged feedback message."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and node.value != ""  # "" clears.
    if isinstance(node, (ast.JoinedStr, ast.BinOp)):
        return True
    if isinstance(node, ast.IfExp):
        return _is_untagged_text(node.body) or _is_untagged_text(node.orelse)
    if isinstance(node, ast.BoolOp):
        return any(_is_untagged_text(value) for value in node.values)
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            return func.id == "str"
        # A method called on text, e.g. "\n".join(parts) or f"{x}".strip().
        return isinstance(func, ast.Attribute) and isinstance(
            func.value, (ast.Constant, ast.JoinedStr)
        )
    return False


def _message_argument(call: ast.Call, position: int):
    if len(call.args) > position:
        return call.args[position]
    for keyword in call.keywords:
        if keyword.arg in {"message", "text"}:
            return keyword.value
    return None


def _label_messages(tree: ast.AST):
    """Yield (call, message) for every status-label update in *tree*."""
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr == "_set_label_text":
            yield node, _message_argument(node, 1)
        elif (
            node.func.attr == "setText"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr in STATUS_LABELS
        ):
            yield node, _message_argument(node, 0)


def _ui_modules():
    return sorted(UI_DIR.rglob("*.py"))  # pages/ included


def test_status_label_messages_are_tagged_with_a_kind():
    scanned, untagged = 0, []
    for path in _ui_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call, message in _label_messages(tree):
            scanned += 1
            if message is not None and _is_untagged_text(message):
                untagged.append(f"{path.relative_to(UI_DIR)}:{call.lineno}")

    assert scanned > 20, f"only {scanned} label updates found under {UI_DIR}"
    assert untagged == []


def test_the_check_spots_untagged_text():
    untagged = [
        'self._set_label_text(label, "Saved")',
        'self._set_label_text(label, f"Saved {name}")',
        'self._set_label_text(label, "\\n".join(parts))',
        'self._set_label_text(label, "Saved to " + path)',
        'self._set_label_text(label, "Saved" if ok else "Failed")',
        'self._set_label_text(label, message or "Nothing to show")',
        "self._set_label_text(label, str(exc))",
        'self._set_label_text(label, message="Saved")',
        'self.label_run_confirmation.setText(f"Saved {name}")',
    ]
    tagged = [
        'self._set_label_text(label, "")',
        'self._set_label_text(label, feedback.success(f"Saved {name}"))',
        'self._set_label_text(label, feedback.info("a") if ok else "")',
        "self._set_label_text(label, message)",
        'self.label_search_result.setText(f"Matches: {count}")',
    ]

    def flagged(source):
        _call, message = next(_label_messages(ast.parse(source)), (None, None))
        return message is not None and _is_untagged_text(message)

    assert [source for source in untagged if not flagged(source)] == []
    assert [source for source in tagged if flagged(source)] == []
