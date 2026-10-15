"""The columns a report puts out, and their names, worked out before it runs.

The engine (:class:`clinical_reporting.pipeline.ReportEngine`) joins the
selected forms in join order. A selected common item keeps its plain name;
every other column of a later form (join order 2 or higher) gets the form's
name in front: its selected items (``AE.Term``), and also each selected common
item it doesn't join on. That form has its own values for the item, so they
go out as ``AE.Visit`` next to the plain ``Visit``, which keeps the values of
the forms joined before it.

The Order & rename list, renames, filters and validation all take the output
columns from :func:`output_identifiers`, so they always match what the engine
produces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Mapping

from clinical_reporting.models import is_positive_integer, qualify

if TYPE_CHECKING:
    from clinical_reporting.report import CLReport

#: Where a form without a valid join order goes: after all the others.
_LAST = 999


def forms_in_join_order(selected_forms: Mapping[str, Any]) -> List[str]:
    """Selected form names in the order the engine joins them.

    Forms without a valid join order go last; ties keep the selection order.
    """

    def order(name: str) -> int:
        value = selected_forms[name].get_join_order()
        return value if is_positive_integer(value) else _LAST

    return sorted(selected_forms, key=order)


def unjoined_common_items(report: "CLReport") -> Dict[str, List[str]]:
    """Each later form's selected common items that it doesn't join on.

    Keyed by form name in join order. The engine puts these forms' own values
    of the items out as ``FORM.item``. Left out: the first form (nothing is
    joined to it), forms that join on every selected common item, and forms
    with no join items yet, which can't be joined at all (validation says so).
    """
    selected_forms = getattr(report, "selected_forms", None) or {}
    common = list(getattr(report, "selected_common_items", None) or [])
    unjoined: Dict[str, List[str]] = {}
    for name in forms_in_join_order(selected_forms)[1:]:
        keys = {item for item in selected_forms[name].get_join_items() if item}
        if not keys:
            continue
        items = [item for item in common if item not in keys]
        if items:
            unjoined[name] = items
    return unjoined


def output_identifiers(report: "CLReport") -> List[str]:
    """The report's output columns in their default order, before renames.

    The selected common items first, then each form in join order: the
    common items it doesn't join on, then its selected items, both as
    ``FORM.item``.
    """
    selected_forms = getattr(report, "selected_forms", None) or {}
    unjoined = unjoined_common_items(report)
    identifiers = list(getattr(report, "selected_common_items", None) or [])
    for name in forms_in_join_order(selected_forms):
        identifiers.extend(qualify(name, item) for item in unjoined.get(name, ()))
        identifiers.extend(
            qualify(name, item)
            for item in selected_forms[name].get_selected_form_items()
        )
    return identifiers


def output_names(report: "CLReport") -> Dict[str, str]:
    """Each output column's name in the workbook, by its identifier.

    Its rename when that is a non-blank text, else the identifier itself.
    """
    renames = getattr(report, "rename_dict", None) or {}
    names: Dict[str, str] = {}
    for identifier in output_identifiers(report):
        rename = renames.get(identifier)
        names[identifier] = (
            rename if isinstance(rename, str) and rename.strip() else identifier
        )
    return names


__all__ = [
    "forms_in_join_order",
    "output_identifiers",
    "output_names",
    "unjoined_common_items",
]
