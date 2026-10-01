"""Qt palette built from the color tokens.

The Fusion style draws everything the stylesheet doesn't cover (checkbox
indicators, combo arrows, focus frames, text selection) from the palette, so
it has to agree with the stylesheet in both schemes.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

from cci_ui.theme.tokens import Color, ColorTokens

_Role = QPalette.ColorRole
_Group = QPalette.ColorGroup


def qcolor(color: Color) -> QColor:
    """Convert a token color to a :class:`QColor`."""
    return QColor(color.r, color.g, color.b, round(color.a * 255))


def to_qpalette(colors: ColorTokens) -> QPalette:
    """Build the application palette for one scheme."""
    palette = QPalette()
    roles = {
        _Role.Window: colors.bg_window,
        _Role.WindowText: colors.text_primary,
        _Role.Base: colors.bg_surface,
        _Role.AlternateBase: colors.bg_surface_alt,
        _Role.Text: colors.text_primary,
        _Role.Button: colors.bg_control,
        _Role.ButtonText: colors.text_primary,
        _Role.BrightText: colors.on_accent,
        _Role.Highlight: colors.accent,
        _Role.HighlightedText: colors.on_accent,
        _Role.PlaceholderText: colors.text_tertiary,
        _Role.Link: colors.link,
        _Role.LinkVisited: colors.link,
        _Role.ToolTipBase: colors.bg_surface,
        _Role.ToolTipText: colors.text_primary,
        _Role.Accent: colors.accent,
        # Bevel shades Fusion uses for frames and separators.
        _Role.Light: colors.bg_surface,
        _Role.Midlight: colors.bg_surface_alt,
        _Role.Mid: colors.border_control,
        _Role.Dark: colors.border_control,
        _Role.Shadow: colors.knob_shadow,
    }
    for group in (_Group.Active, _Group.Inactive, _Group.Disabled):
        for role, color in roles.items():
            palette.setColor(group, role, qcolor(color))

    for role in (_Role.WindowText, _Role.Text, _Role.ButtonText, _Role.PlaceholderText):
        palette.setColor(_Group.Disabled, role, qcolor(colors.text_disabled))
    palette.setColor(_Group.Disabled, _Role.Base, qcolor(colors.bg_surface_alt))

    # A background window keeps its selection visible, but grey (as on macOS).
    palette.setColor(
        _Group.Inactive, _Role.Highlight, qcolor(colors.selection_inactive)
    )
    palette.setColor(
        _Group.Inactive, _Role.HighlightedText, qcolor(colors.text_primary)
    )
    return palette


__all__ = ["qcolor", "to_qpalette"]
