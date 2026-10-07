"""The application stylesheet, generated from the design tokens.

The base rules below cover standard Qt widgets. Custom components add their
own rules with :func:`register_qss`, at import time, so each component's
styling lives next to its code; rules registered after the theme was applied
only take effect at the next ``ThemeManager.apply()``. Placeholders use
``string.Template`` syntax (``${accent}``) because QSS itself is full of
braces; every color token, size token, and the derived values in
:func:`_values` can be used.

Text colors come from the palette, not from a blanket ``QWidget`` rule, so
disabled widgets keep the palette's disabled color.

Variants are chosen with dynamic properties instead of class names, for
example ``button.setProperty("variant", "primary")``; call
:func:`cci_ui.theme.manager.repolish` after changing one on a visible widget.
This module is pure Python so the rules can be built and checked without Qt.
"""

from __future__ import annotations

import string
from dataclasses import fields
from typing import Dict, List, Mapping, Optional

from cci_ui.theme.tokens import TYPE_SCALE, ColorTokens, Metrics

_fragments: List[str] = []

_BASE = """
QMainWindow, QDialog {
    background: ${bg_window};
}
QToolTip {
    background: ${bg_surface};
    color: ${text_primary};
    border: 1px solid ${border_card};
    border-radius: 6px;
    padding: 4px 8px;
}
QLabel {
    background: transparent;
}

/* ---- Buttons: secondary by default; one primary per view ---- */
QPushButton, QToolButton {
    min-height: ${control_inner}px;
    padding: 0 12px;
    border: 1px solid ${border_control};
    border-radius: ${radius_control}px;
    background: ${bg_control};
    color: ${text_primary};
    font-weight: 500;
}
QToolButton {
    padding: 0 6px;
}
QPushButton:hover, QToolButton:hover {
    background: ${bg_control_hover};
}
QPushButton:pressed, QToolButton:pressed, QToolButton:checked {
    background: ${bg_control_pressed};
}
QPushButton:focus, QToolButton:focus {
    border-color: ${accent};
}
QPushButton:disabled, QToolButton:disabled {
    color: ${text_disabled};
    background: ${bg_control};
    border-color: ${separator};
}
QPushButton[variant="primary"] {
    background: ${accent};
    border-color: ${accent};
    color: ${on_accent};
}
QPushButton[variant="primary"]:hover {
    background: ${accent_hover};
    border-color: ${accent_hover};
}
QPushButton[variant="primary"]:pressed {
    background: ${accent_pressed};
    border-color: ${accent_pressed};
}
QPushButton[variant="primary"]:focus {
    border-color: ${focus_ring};
}
QPushButton[variant="primary"]:disabled {
    background: ${accent_disabled};
    border-color: transparent;
    color: ${on_accent};
}
QPushButton[variant="destructive"] {
    color: ${danger_text};
}
QPushButton[variant="plain"] {
    background: transparent;
    border-color: transparent;
    color: ${link};
    padding: 0 6px;
}
QPushButton[variant="plain"]:hover, QPushButton[variant="plain"]:pressed {
    background: ${bg_hover};
}
QPushButton[variant="ghost"], QToolButton[variant="ghost"] {
    background: transparent;
    border-color: transparent;
    color: ${text_secondary};
}
QPushButton[variant="ghost"]:hover, QToolButton[variant="ghost"]:hover {
    background: ${bg_hover};
    color: ${text_primary};
}

/* ---- Text inputs, combos, dates ---- */
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
    min-height: ${control_inner}px;
    padding: 0 8px;
    border: 1px solid ${border_control};
    border-radius: ${radius_control}px;
    background: ${bg_control};
    selection-background-color: ${accent};
    selection-color: ${on_accent};
}
QPlainTextEdit, QTextEdit {
    padding: 6px 8px;
    border: 1px solid ${border_control};
    border-radius: ${radius_control}px;
    background: ${bg_control};
    selection-background-color: ${accent};
    selection-color: ${on_accent};
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border-color: ${accent};
}
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {
    color: ${text_disabled};
    background: ${bg_surface_alt};
    border-color: ${separator};
}
QComboBox[invalid="true"] {
    color: ${danger_text};
    font-weight: 600;
    border-color: ${danger};
}
QComboBox QAbstractItemView {
    background: ${bg_surface};
    border: 1px solid ${border_card};
    border-radius: 0;
    selection-background-color: ${selection};
    selection-color: ${text_primary};
    outline: 0;
}

/* ---- Lists and tables ----
   Views can't show rounded corners (their viewport paints square ones), so a
   view that should look like a card sits inside a QFrame[cciRole="card"] and
   is marked cciRole="embedded" to drop its own border. */
QAbstractItemView {
    background: ${bg_surface};
    alternate-background-color: ${bg_surface_alt};
    border: 1px solid ${border_card};
    border-radius: 0;
    selection-background-color: ${selection};
    selection-color: ${text_primary};
    outline: 0;
}
QListView::item {
    min-height: ${row_h}px;
    padding: 0 8px;
    border-radius: 6px;
}
/* Cell text lines up with the header text; cell widgets (combos) sit 8px in. */
QTableView::item {
    padding: 0 8px;
}
QAbstractItemView::item:hover {
    background: ${bg_hover};
}
QAbstractItemView::item:selected:active {
    background: ${selection};
    color: ${text_primary};
}
QAbstractItemView::item:selected:!active {
    background: ${selection_inactive};
    color: ${text_primary};
}
QTableView {
    gridline-color: ${separator};
}
/* Headers don't take the item views' border: beside the row numbers it
   drew a line down past the last row. */
QHeaderView {
    background: transparent;
    border: none;
}
QHeaderView::section {
    background: ${bg_surface};
    color: ${text_secondary};
    font-size: 12px;
    font-weight: 600;
    padding: 0 10px;
    min-height: ${row_h}px;
    border: none;
    border-bottom: 1px solid ${separator};
}
QTableCornerButton::section {
    background: ${bg_surface};
    border: none;
    border-bottom: 1px solid ${separator};
}

/* ---- Thin scroll bars without arrows ---- */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: ${scrollbar};
    border-radius: 3px;
    min-height: 28px;
}
QScrollBar::handle:horizontal {
    background: ${scrollbar};
    border-radius: 3px;
    min-width: 28px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}

/* ---- Menus, tabs, status bar, splitters ---- */
QMenu {
    background: ${bg_surface};
    border: 1px solid ${border_card};
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 4px 20px 4px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: ${accent};
    color: ${on_accent};
}
QMenu::separator {
    height: 1px;
    background: ${separator};
    margin: 4px 8px;
}
/* A 1px line inside a 5px handle, so it's still easy to grab. */
QSplitter::handle {
    background: transparent;
}
QSplitter::handle:horizontal {
    width: 5px;
    border-left: 1px solid ${separator};
}
QSplitter::handle:vertical {
    height: 5px;
    border-top: 1px solid ${separator};
}

/* ---- Calendar popup (needs explicit colors in dark mode) ---- */
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background: ${bg_surface};
}
QCalendarWidget QToolButton {
    background: transparent;
    border: none;
    color: ${text_primary};
    min-height: 0;
    padding: 4px 8px;
}
QCalendarWidget QAbstractItemView {
    border: none;
    border-radius: 0;
    selection-background-color: ${accent};
    selection-color: ${on_accent};
}

/* ---- Roles and text styles set with dynamic properties ---- */
QFrame[cciRole="card"] {
    background: ${bg_surface};
    border: 1px solid ${border_card};
    border-radius: ${radius_card}px;
}
QFrame[cciRole="separator"] {
    background: ${separator};
    border: none;
    min-height: 1px;
    max-height: 1px;
}
QFrame[cciRole="separatorVertical"] {
    background: ${separator};
    border: none;
    min-width: 1px;
    max-width: 1px;
}
QAbstractItemView[cciRole="embedded"] {
    border: none;
}
"""

# Rules that need images (see cci_ui.theme.glyphs). They are only added when
# the images could be written, so a failure falls back to Qt's own arrows and
# checkboxes instead of empty boxes.
_GLYPH_RULES = """
QComboBox, QDateEdit[calendarPopup="true"] {
    padding-right: 26px;
}
QComboBox::drop-down, QDateEdit[calendarPopup="true"]::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 24px;
    border: none;
    background: transparent;
}
QComboBox::down-arrow, QDateEdit[calendarPopup="true"]::down-arrow {
    image: url("${glyph_chevron_down}");
    width: 14px;
    height: 14px;
}
QComboBox::down-arrow:disabled,
QDateEdit[calendarPopup="true"]::down-arrow:disabled {
    image: url("${glyph_chevron_down_disabled}");
}
QCheckBox::indicator, QAbstractItemView::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid ${border_control};
    border-radius: 4px;
    background: ${bg_control};
}
QCheckBox::indicator:hover, QAbstractItemView::indicator:hover {
    border-color: ${accent};
}
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {
    background: ${accent};
    border-color: ${accent};
    image: url("${glyph_check}");
}
QCheckBox::indicator:disabled, QAbstractItemView::indicator:disabled {
    background: ${bg_surface_alt};
    border-color: ${separator};
}
QCheckBox::indicator:checked:disabled,
QAbstractItemView::indicator:checked:disabled {
    background: ${accent_disabled};
    border-color: transparent;
}
QCalendarWidget QToolButton#qt_calendar_prevmonth {
    qproperty-icon: url("${glyph_calendar_prev}");
}
QCalendarWidget QToolButton#qt_calendar_nextmonth {
    qproperty-icon: url("${glyph_calendar_next}");
}
"""

# Tone rules come after the type scale so ``tone`` can recolor any text style.
_TONES = """
QLabel[tone="secondary"] {
    color: ${text_secondary};
}
QLabel[tone="tertiary"] {
    color: ${text_tertiary};
}
"""


def register_qss(fragment: str) -> None:
    """Add component rules to every stylesheet built after this call."""
    if fragment not in _fragments:
        _fragments.append(fragment)


def _values(colors: ColorTokens, metrics: Metrics) -> Dict[str, object]:
    values: Dict[str, object] = {
        f.name: getattr(colors, f.name).qss for f in fields(colors)
    }
    values.update({f.name: getattr(metrics, f.name) for f in fields(metrics)})
    # Qt's min-height excludes the 1px top and bottom border.
    values["control_inner"] = metrics.control_h - 2
    # Segments sit inside a 2px track, so they are 4px shorter than controls.
    values["segment_h"] = metrics.control_h - 4
    values["accent_disabled"] = colors.accent.with_alpha(0.45).qss
    return values


def _type_scale_rules() -> str:
    """One rule per text style; colors stay placeholders like the base rules."""
    rules = []
    for name, style in TYPE_SCALE.items():
        rules.append(
            f'QLabel[textStyle="{name}"] {{ font-size: {style.size}px; '
            f"font-weight: {style.weight}; color: ${{{style.tone}}}; }}"
        )
    return "\n".join(rules)


def build_stylesheet(
    colors: ColorTokens,
    metrics: Metrics,
    glyphs: Optional[Mapping[str, str]] = None,
) -> str:
    """Return the full application stylesheet for one scheme and density.

    *glyphs* maps the ``glyph_*`` placeholders to image files, as returned by
    :func:`cci_ui.theme.glyphs.export_glyphs`; without it the image rules are
    left out. Raises ``KeyError`` if a rule uses a placeholder that isn't a
    token.
    """
    # Later rules win over earlier ones of equal specificity: base rules,
    # then images, text styles, tones, and finally component rules.
    image_rules = [_GLYPH_RULES] if glyphs else []
    parts = [_BASE, *image_rules, _type_scale_rules(), _TONES, *_fragments]
    values = {**_values(colors, metrics), **(glyphs or {})}
    return string.Template("\n".join(parts)).substitute(values)


__all__ = ["build_stylesheet", "register_qss"]
