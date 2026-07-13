"""Validation for report definitions before DataFrame execution.

The report model is intentionally mutable because it is edited by the Qt UI.
This module provides the boundary that turns that partially configured state
into either a valid executable definition or a structured list of problems.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from clinical_reporting.core.constants import (
    FORM_ITEM_SEPARATOR,
    JoinHow,
    Operator,
    qualify,
)


@dataclass(frozen=True)
class ReportValidationIssue:
    """One actionable problem in a report definition."""

    code: str
    message: str
    field: Optional[str] = None

    def to_dict(self) -> dict[str, Optional[str]]:
        """Return a serialization-friendly representation of this issue."""

        return {"code": self.code, "message": self.message, "field": self.field}


class ReportValidationError(ValueError):
    """Raised when report execution is requested with invalid configuration."""

    def __init__(self, issues: Iterable[ReportValidationIssue]):
        self.issues = tuple(issues)
        details = "\n".join(f"- {issue.message}" for issue in self.issues)
        super().__init__(f"Report configuration is invalid:\n{details}")


def _add_issue(
    issues: list[ReportValidationIssue],
    code: str,
    message: str,
    field: Optional[str] = None,
) -> None:
    issues.append(ReportValidationIssue(code=code, message=message, field=field))


def _is_positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _columns_for(data: dict, form_name: str) -> set[str]:
    source = data.get(form_name)
    return set(getattr(source, "columns", ()))


def _validate_filter_identifier(
    identifier: Any,
    *,
    common_items: set[str],
    qualified_items: set[str],
    item_forms: dict[str, set[str]],
) -> tuple[bool, bool]:
    """Return ``(exists, ambiguous)`` for a selected report identifier."""

    if not isinstance(identifier, str) or not identifier:
        return False, False
    if identifier in common_items or identifier in qualified_items:
        return True, False
    forms = item_forms.get(identifier, set())
    return bool(forms), len(forms) > 1


def validate_report(report) -> list[ReportValidationIssue]:
    """Validate a mutable report model before it reaches the execution engine.

    The function does not mutate ``report``. Every detected problem is returned
    so the UI or a headless caller can fix the full configuration in one pass.
    """

    issues: list[ReportValidationIssue] = []
    data = getattr(report, "data", None) or {}
    selected_forms = getattr(report, "selected_forms", None) or {}
    selected_common = list(getattr(report, "selected_common_items", None) or [])

    if not data:
        _add_issue(issues, "no_data", "Load report data before running.", "data")
    if not selected_forms:
        _add_issue(
            issues,
            "no_selected_forms",
            "Select at least one form before running.",
            "selected_forms",
        )

    duplicate_common = sorted(item for item, count in Counter(selected_common).items() if count > 1)
    for item in duplicate_common:
        _add_issue(
            issues,
            "duplicate_common_item",
            f"Common item '{item}' is selected more than once.",
            "selected_common_items",
        )

    selected_common_set = set(selected_common)
    for item in selected_common:
        missing_from = [
            form_name
            for form_name in selected_forms
            if item not in _columns_for(data, form_name)
        ]
        if missing_from:
            _add_issue(
                issues,
                "missing_common_item",
                f"Common item '{item}' is missing from selected form(s): {', '.join(missing_from)}.",
                f"selected_common_items.{item}",
            )

    valid_orders = True
    order_to_forms: dict[int, list[str]] = {}
    qualified_items: set[str] = set()
    item_forms: dict[str, set[str]] = {}
    logical_output: list[str] = list(selected_common)

    for form_name, form in selected_forms.items():
        if FORM_ITEM_SEPARATOR in form_name:
            _add_issue(
                issues,
                "invalid_form_name",
                f"Form name '{form_name}' cannot contain '{FORM_ITEM_SEPARATOR}'.",
                f"selected_forms.{form_name}",
            )

        if form_name not in data:
            _add_issue(
                issues,
                "missing_form",
                f"Selected form '{form_name}' is not present in the loaded data.",
                f"selected_forms.{form_name}",
            )
        columns = _columns_for(data, form_name)

        order = form.get_join_order()
        if not _is_positive_integer(order):
            valid_orders = False
            _add_issue(
                issues,
                "invalid_join_order",
                f"Form '{form_name}' needs a positive integer join order.",
                f"selected_forms.{form_name}.join_order",
            )
        else:
            order_to_forms.setdefault(order, []).append(form_name)

        selected_items = list(form.get_selected_form_items())
        for item in sorted(item for item, count in Counter(selected_items).items() if count > 1):
            _add_issue(
                issues,
                "duplicate_form_item",
                f"Item '{item}' is selected more than once on form '{form_name}'.",
                f"selected_forms.{form_name}.selected_form_items",
            )
        for item in selected_items:
            identifier = qualify(form_name, item)
            qualified_items.add(identifier)
            item_forms.setdefault(item, set()).add(form_name)
            logical_output.append(identifier)
            if item not in columns:
                _add_issue(
                    issues,
                    "missing_form_item",
                    f"Selected item '{item}' is missing from form '{form_name}'.",
                    f"selected_forms.{form_name}.selected_form_items",
                )

        join_items = [item for item in form.get_join_items() if item]
        for item in sorted(item for item, count in Counter(join_items).items() if count > 1):
            _add_issue(
                issues,
                "duplicate_join_item",
                f"Join item '{item}' is repeated on form '{form_name}'.",
                f"selected_forms.{form_name}.join_items",
            )
        for item in join_items:
            if item not in columns:
                _add_issue(
                    issues,
                    "missing_join_item",
                    f"Join item '{item}' is missing from form '{form_name}'.",
                    f"selected_forms.{form_name}.join_items",
                )
            if item not in selected_common_set:
                _add_issue(
                    issues,
                    "join_item_not_common",
                    f"Join item '{item}' on form '{form_name}' must be a selected common item.",
                    f"selected_forms.{form_name}.join_items",
                )

        contributes = bool(
            columns.intersection(selected_common_set)
            or columns.intersection(selected_items)
            or columns.intersection(join_items)
        )
        if form_name in data and not contributes:
            _add_issue(
                issues,
                "form_has_no_columns",
                f"Selected form '{form_name}' contributes no selected or join columns.",
                f"selected_forms.{form_name}",
            )

    for order, forms in sorted(order_to_forms.items()):
        if len(forms) > 1:
            valid_orders = False
            _add_issue(
                issues,
                "duplicate_join_order",
                f"Join order {order} is assigned to multiple forms: {', '.join(sorted(forms))}.",
                "selected_forms.join_order",
            )

    if selected_forms and valid_orders:
        ordered_forms = sorted(
            selected_forms,
            key=lambda name: selected_forms[name].get_join_order(),
        )
        for form_name in ordered_forms[1:]:
            form = selected_forms[form_name]
            join_items = [item for item in form.get_join_items() if item]
            if not join_items:
                _add_issue(
                    issues,
                    "missing_join_items",
                    f"Form '{form_name}' needs at least one join item because it is not first.",
                    f"selected_forms.{form_name}.join_items",
                )
            if form.get_join_how() not in JoinHow.ALL:
                _add_issue(
                    issues,
                    "invalid_join_how",
                    f"Form '{form_name}' has an invalid join type: {form.get_join_how()!r}.",
                    f"selected_forms.{form_name}.join_how",
                )

    active_identifiers = selected_common_set | qualified_items

    for index, raw_filter in enumerate(getattr(report, "static_filter_items", None) or []):
        field = f"static_filter_items.{index}"
        if not isinstance(raw_filter, (list, tuple)) or len(raw_filter) != 3:
            _add_issue(issues, "invalid_static_filter", f"Static filter {index + 1} must have item, operator, and value.", field)
            continue
        item, operator, _ = raw_filter
        if operator not in Operator.STATIC:
            _add_issue(issues, "invalid_static_operator", f"Static filter {index + 1} has an invalid operator: {operator!r}.", field)
        exists, ambiguous = _validate_filter_identifier(
            item,
            common_items=selected_common_set,
            qualified_items=qualified_items,
            item_forms=item_forms,
        )
        if ambiguous:
            _add_issue(issues, "ambiguous_filter_item", f"Static filter item '{item}' is ambiguous; qualify it with a form name.", field)
        elif not exists:
            _add_issue(issues, "missing_filter_item", f"Static filter item '{item}' is not selected in the report.", field)

    for index, raw_filter in enumerate(getattr(report, "dynamic_filter_items", None) or []):
        field = f"dynamic_filter_items.{index}"
        if not isinstance(raw_filter, (list, tuple)) or len(raw_filter) != 3:
            _add_issue(issues, "invalid_dynamic_filter", f"Dynamic filter {index + 1} must have two items and an operator.", field)
            continue
        item1, operator, item2 = raw_filter
        if operator not in Operator.DYNAMIC:
            _add_issue(issues, "invalid_dynamic_operator", f"Dynamic filter {index + 1} has an invalid operator: {operator!r}.", field)
        for operand_name, operand in (("left", item1), ("right", item2)):
            exists, ambiguous = _validate_filter_identifier(
                operand,
                common_items=selected_common_set,
                qualified_items=qualified_items,
                item_forms=item_forms,
            )
            if ambiguous:
                _add_issue(issues, "ambiguous_filter_item", f"Dynamic filter {operand_name} item '{operand}' is ambiguous; qualify it with a form name.", field)
            elif not exists:
                _add_issue(issues, "missing_filter_item", f"Dynamic filter {operand_name} item '{operand}' is not selected in the report.", field)

    rename_dict = getattr(report, "rename_dict", None) or {}
    renamed_output: list[str] = []
    for identifier in logical_output:
        configured_name = rename_dict.get(identifier, identifier)
        # Invalid targets are reported below. Keep the original identifier in
        # duplicate detection so malformed, unhashable values cannot make the
        # validator itself fail.
        renamed_output.append(
            configured_name
            if isinstance(configured_name, str) and configured_name.strip()
            else identifier
        )
    for original_name, new_name in rename_dict.items():
        if original_name not in active_identifiers:
            _add_issue(
                issues,
                "unknown_rename_item",
                f"Rename source '{original_name}' is not selected in the report.",
                f"rename_dict.{original_name}",
            )
        if not isinstance(new_name, str) or not new_name.strip():
            _add_issue(
                issues,
                "invalid_output_name",
                f"Rename target for '{original_name}' must be a non-empty string.",
                f"rename_dict.{original_name}",
            )

    duplicate_outputs = sorted(
        str(item) for item, count in Counter(renamed_output).items() if count > 1
    )
    for output_name in duplicate_outputs:
        _add_issue(
            issues,
            "duplicate_output_name",
            f"Output column name '{output_name}' would be duplicated.",
            "rename_dict",
        )

    for attribute in ("order_list", "selected_items_order_list"):
        for identifier in getattr(report, attribute, None) or []:
            if identifier not in active_identifiers:
                _add_issue(
                    issues,
                    "unknown_order_item",
                    f"Ordered item '{identifier}' is not selected in the report.",
                    attribute,
                )

    return issues


def raise_for_report(report) -> None:
    """Raise :class:`ReportValidationError` when ``report`` is not executable."""

    issues = validate_report(report)
    if issues:
        raise ReportValidationError(issues)
