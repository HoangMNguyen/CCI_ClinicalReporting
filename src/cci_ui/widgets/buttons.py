"""Buttons in the design system's variants.

One view should have at most one ``primary`` button (the main action). The
default ``secondary`` button is neutral, ``destructive`` is for removing or
discarding, ``plain`` is a text link, and ``ghost`` is a borderless icon or
text button for toolbars.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QAbstractButton,
    QHBoxLayout,
    QPushButton,
    QToolButton,
    QWidget,
)

from cci_ui.icons import icon
from cci_ui.theme.manager import repolish
from cci_ui.theme.qss import register_qss

VARIANTS = ("primary", "secondary", "destructive", "plain", "ghost")

register_qss(
    """
QToolButton[iconOnly="true"] {
    padding: 0;
    min-width: ${control_inner}px;
}
QWidget[cciRole="buttonGroup"] QToolButton {
    border-radius: 0;
}
QWidget[cciRole="buttonGroup"] QToolButton[groupPosition="first"] {
    border-top-left-radius: ${radius_control}px;
    border-bottom-left-radius: ${radius_control}px;
}
QWidget[cciRole="buttonGroup"] QToolButton[groupPosition="middle"] {
    border-left-width: 0;
}
QWidget[cciRole="buttonGroup"] QToolButton[groupPosition="last"] {
    border-left-width: 0;
    border-top-right-radius: ${radius_control}px;
    border-bottom-right-radius: ${radius_control}px;
}
"""
)


def set_variant(button: QAbstractButton, variant: str) -> None:
    """Give *button* one of :data:`VARIANTS`; safe to call on a visible button."""
    if variant not in VARIANTS:
        raise ValueError(
            f"Unknown button variant {variant!r}; expected one of {VARIANTS}"
        )
    button.setProperty("variant", None if variant == "secondary" else variant)
    repolish(button)


def _icon_role(variant: str) -> str:
    return {"primary": "on_accent", "destructive": "danger", "plain": "accent"}.get(
        variant, "secondary"
    )


def make_button(
    text: str = "",
    *,
    variant: str = "secondary",
    icon_name: Optional[str] = None,
    parent: Optional[QWidget] = None,
) -> QPushButton:
    """A push button in *variant*, with an optional icon colored to match."""
    button = QPushButton(text, parent)
    if icon_name:
        button.setIcon(icon(icon_name, _icon_role(variant)))
    set_variant(button, variant)
    return button


def icon_button(
    icon_name: str,
    tooltip: str,
    *,
    variant: str = "ghost",
    parent: Optional[QWidget] = None,
) -> QToolButton:
    """A square icon-only button; *tooltip* is also its accessible name."""
    button = QToolButton(parent)
    button.setIcon(icon(icon_name, _icon_role(variant)))
    button.setToolTip(tooltip)
    button.setAccessibleName(tooltip)
    button.setProperty("iconOnly", True)
    set_variant(button, variant)
    return button


def button_group(*buttons: QAbstractButton) -> QWidget:
    """Join two or more icon *buttons* side by side into one group (e.g. + and −)."""
    if len(buttons) < 2:
        raise ValueError("A button group needs at least two buttons")
    group = QWidget()
    group.setProperty("cciRole", "buttonGroup")
    layout = QHBoxLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    last = len(buttons) - 1
    for index, button in enumerate(buttons):
        position = "first" if index == 0 else "last" if index == last else "middle"
        button.setProperty("groupPosition", position)
        layout.addWidget(button)
    return group


__all__ = ["VARIANTS", "button_group", "icon_button", "make_button", "set_variant"]
