"""Design tokens: the colors, sizes, and type scale of every CCI tool.

This module is the single source for how the apps look. The desktop palette
and stylesheet are generated from it, and :func:`to_css` writes the same
values as CSS custom properties, so a future web front end uses identical
values. It is pure Python and must never import Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from types import MappingProxyType
from typing import Dict, Mapping, Tuple


class Scheme(str, Enum):
    """The color scheme actually on screen."""

    LIGHT = "light"
    DARK = "dark"


class Density(str, Enum):
    """How much space controls and rows take."""

    COMFORTABLE = "comfortable"
    COMPACT = "compact"


@dataclass(frozen=True)
class Color:
    """An sRGB color; ``a`` is opacity from 0 to 1."""

    r: int
    g: int
    b: int
    a: float = 1.0

    @classmethod
    def hex(cls, value: str, alpha: float = 1.0) -> Color:
        """Build a color from ``"#RRGGBB"``."""
        digits = value.removeprefix("#")
        if len(digits) != 6:
            raise ValueError(f"Expected a color like '#0071E3', got {value!r}")
        return cls(
            int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16), alpha
        )

    def with_alpha(self, alpha: float) -> Color:
        return Color(self.r, self.g, self.b, alpha)

    @property
    def hex_rgb(self) -> str:
        """``"#RRGGBB"``, ignoring opacity."""
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    @property
    def css(self) -> str:
        """CSS form: opacity is written from 0 to 1."""
        if self.a >= 1:
            return self.hex_rgb
        return f"rgba({self.r}, {self.g}, {self.b}, {self.a:g})"

    @property
    def qss(self) -> str:
        """Qt stylesheet form: Qt reads the opacity of ``rgba()`` from 0 to 255."""
        if self.a >= 1:
            return self.hex_rgb
        return f"rgba({self.r}, {self.g}, {self.b}, {round(self.a * 255)})"


_hex = Color.hex
_rgba = Color


@dataclass(frozen=True)
class ColorTokens:
    """Every color the apps use, for one scheme."""

    # Surfaces
    bg_window: Color
    bg_sidebar: Color
    bg_surface: Color  # cards, lists, tables
    bg_surface_alt: Color  # alternate rows, headers
    bg_control: Color
    bg_control_hover: Color
    bg_control_pressed: Color
    bg_hover: Color  # rows and borderless buttons under the pointer
    fill: Color  # segmented-control track, count pills, pick-only dropdowns
    selection: Color  # soft-tint selection (sidebar, lists, tables)
    selection_inactive: Color  # selection while the window is in the background
    find_bg: Color  # rows matching a search
    # Lines
    border_control: Color
    border_card: Color
    separator: Color
    # Text
    text_primary: Color
    text_secondary: Color
    text_tertiary: Color
    text_disabled: Color
    # Accent
    accent: Color
    accent_hover: Color
    accent_pressed: Color
    on_accent: Color
    focus_ring: Color
    link: Color
    # Status
    success: Color
    success_text: Color
    success_bg: Color
    warning: Color
    warning_text: Color
    warning_bg: Color
    danger: Color
    danger_text: Color
    danger_bg: Color
    info_text: Color
    info_bg: Color
    # Controls and overlays
    switch_off: Color
    switch_knob: Color
    knob_shadow: Color
    seg_selected: Color
    seg_shadow: Color
    scrollbar: Color
    scrim: Color
    shadow_toast: Color


LIGHT = ColorTokens(
    bg_window=_hex("#F5F5F7"),
    bg_sidebar=_hex("#EDEDF0"),
    bg_surface=_hex("#FFFFFF"),
    bg_surface_alt=_hex("#F7F7F9"),
    bg_control=_hex("#FFFFFF"),
    bg_control_hover=_hex("#F2F2F4"),
    bg_control_pressed=_hex("#E8E8ED"),
    bg_hover=_rgba(0, 0, 0, 0.04),
    fill=_rgba(118, 118, 128, 0.12),
    selection=_hex("#E1ECFB"),
    selection_inactive=_hex("#E4E4E8"),
    find_bg=_rgba(255, 204, 0, 0.32),
    border_control=_hex("#D1D1D6"),
    border_card=_hex("#E5E5EA"),
    separator=_hex("#E5E5EA"),
    text_primary=_hex("#1D1D1F"),
    text_secondary=_hex("#6E6E73"),
    text_tertiary=_hex("#8E8E93"),
    text_disabled=_hex("#B0B0B5"),
    accent=_hex("#0071E3"),
    accent_hover=_hex("#0062C4"),
    accent_pressed=_hex("#0055AA"),
    on_accent=_hex("#FFFFFF"),
    focus_ring=_rgba(0, 113, 227, 0.45),
    link=_hex("#0066CC"),
    success=_hex("#34C759"),
    success_text=_hex("#248A3D"),
    success_bg=_hex("#EAF8EE"),
    warning=_hex("#FF9500"),
    warning_text=_hex("#B25000"),
    warning_bg=_hex("#FFF4E5"),
    danger=_hex("#FF3B30"),
    danger_text=_hex("#D70015"),
    danger_bg=_hex("#FFEBEA"),
    info_text=_hex("#0055AA"),
    info_bg=_hex("#E5F1FF"),
    switch_off=_hex("#E3E3E8"),
    switch_knob=_hex("#FFFFFF"),
    knob_shadow=_rgba(0, 0, 0, 0.28),
    seg_selected=_hex("#FFFFFF"),
    seg_shadow=_rgba(0, 0, 0, 0.12),
    scrollbar=_rgba(0, 0, 0, 0.25),
    scrim=_rgba(245, 245, 247, 0.72),
    shadow_toast=_rgba(0, 0, 0, 0.18),
)

DARK = ColorTokens(
    bg_window=_hex("#1C1C1E"),
    bg_sidebar=_hex("#232325"),
    bg_surface=_hex("#2C2C2E"),
    bg_surface_alt=_hex("#313133"),
    bg_control=_hex("#3A3A3C"),
    bg_control_hover=_hex("#444446"),
    bg_control_pressed=_hex("#4C4C4F"),
    bg_hover=_rgba(255, 255, 255, 0.06),
    fill=_rgba(118, 118, 128, 0.24),
    selection=_hex("#1E3A5F"),
    selection_inactive=_hex("#3A3A3C"),
    find_bg=_rgba(255, 214, 10, 0.28),
    border_control=_hex("#545458"),
    border_card=_hex("#3A3A3C"),
    separator=_hex("#38383A"),
    text_primary=_hex("#F5F5F7"),
    text_secondary=_hex("#A1A1A6"),
    text_tertiary=_hex("#7C7C82"),
    text_disabled=_hex("#5A5A5E"),
    accent=_hex("#0A84FF"),
    accent_hover=_hex("#3395FF"),
    accent_pressed=_hex("#0071E0"),
    on_accent=_hex("#FFFFFF"),
    focus_ring=_rgba(10, 132, 255, 0.6),
    link=_hex("#2997FF"),
    success=_hex("#30D158"),
    success_text=_hex("#30D158"),
    success_bg=_hex("#1F3A27"),
    warning=_hex("#FF9F0A"),
    warning_text=_hex("#FFB340"),
    warning_bg=_hex("#3D2E14"),
    danger=_hex("#FF453A"),
    danger_text=_hex("#FF6961"),
    danger_bg=_hex("#3F1D1B"),
    info_text=_hex("#64B0FF"),
    info_bg=_hex("#14283F"),
    switch_off=_hex("#48484A"),
    switch_knob=_hex("#FFFFFF"),
    knob_shadow=_rgba(0, 0, 0, 0.45),
    seg_selected=_hex("#636366"),
    seg_shadow=_rgba(0, 0, 0, 0.3),
    scrollbar=_rgba(255, 255, 255, 0.25),
    scrim=_rgba(28, 28, 30, 0.72),
    shadow_toast=_rgba(0, 0, 0, 0.5),
)


@dataclass(frozen=True)
class Metrics:
    """Sizes in logical pixels for one density; they scale with Windows display scaling."""

    control_h: int  # buttons, inputs, combos
    row_h: int  # read-only table and list rows, and table headers
    editor_row_h: int  # rows of tables whose cells hold dropdowns or fields
    form_row_pad: int  # vertical padding of a row inside a card
    page_margin: int
    section_gap: int
    sidebar_row: int
    header_h: int  # the header bar
    status_h: int  # the status bar
    page_title_px: int  # text size of page titles
    page_header_gap: int  # space between a page's title block and its body
    footer_pad_top: int  # space above a workspace page's footer ("Next: …")
    footer_pad_bottom: int  # space below a workspace page's footer
    panel_pad: int  # space inside each section of a side panel
    panel_gap: int  # space between the parts of a side panel section
    pair_gap: int  # space between and around the lists of a two-list picker
    radius_card: int = 10
    radius_control: int = 6
    radius_pill: int = 8


COMFORTABLE = Metrics(
    control_h=28,
    row_h=32,
    editor_row_h=32,
    form_row_pad=10,
    page_margin=24,
    section_gap=20,
    sidebar_row=30,
    header_h=44,
    status_h=24,
    page_title_px=22,
    page_header_gap=14,
    footer_pad_top=10,
    footer_pad_bottom=12,
    panel_pad=14,
    panel_gap=10,
    pair_gap=12,
)
COMPACT = Metrics(
    control_h=24,
    row_h=24,
    editor_row_h=28,
    form_row_pad=4,
    page_margin=16,
    section_gap=12,
    sidebar_row=26,
    header_h=36,
    status_h=20,
    page_title_px=17,
    page_header_gap=8,
    footer_pad_top=6,
    footer_pad_bottom=8,
    panel_pad=10,
    panel_gap=6,
    pair_gap=8,
)


@dataclass(frozen=True)
class TextStyle:
    """One step of the type scale; ``tone`` names the text color token."""

    size: int
    weight: int
    tone: str = "text_primary"


#: Font families in order of preference. Inter is bundled with the apps.
FONT_FAMILIES: Tuple[str, ...] = (
    "Inter",
    "Segoe UI Variable Text",
    "Segoe UI",
    "Helvetica Neue",
    "Arial",
)
MONO_FAMILIES: Tuple[str, ...] = ("Cascadia Mono", "Consolas", "Menlo", "monospace")
BODY_PX = 13

TYPE_SCALE: Mapping[str, TextStyle] = MappingProxyType(
    {
        "largeTitle": TextStyle(26, 700),
        "title1": TextStyle(22, 700),  # page titles, sized by Metrics.page_title_px
        "title2": TextStyle(17, 600),
        "title3": TextStyle(15, 600),
        "headline": TextStyle(13, 600),
        "body": TextStyle(BODY_PX, 400),
        "callout": TextStyle(12, 400),
        "subheadline": TextStyle(12, 600, "text_secondary"),  # section labels
        "footnote": TextStyle(11, 400, "text_secondary"),
        "caption": TextStyle(11, 400, "text_secondary"),
    }
)


@dataclass(frozen=True)
class Layout:
    """Window sizes and responsive breakpoints (logical pixels)."""

    min_window: Tuple[int, int] = (960, 600)
    first_launch: Tuple[int, int] = (1280, 820)
    small_min_window: Tuple[int, int] = (560, 440)
    small_first_launch: Tuple[int, int] = (680, 540)
    sidebar_w: int = 232
    sidebar_w_min: int = 200
    sidebar_w_max: int = 320
    sidebar_collapsed_w: int = 56
    #: Collapsed sidebar width when its icons carry their step numbers.
    sidebar_badge_strip_w: int = 72
    #: Below this window width the sidebar collapses to icons.
    sidebar_collapse_below: int = 1100
    panel_w: int = 320
    panel_w_min: int = 280
    panel_w_max: int = 400
    #: Below this content width the Preview panel moves under the grid.
    panel_below_content: int = 900
    #: Total width of the dead zone around each breakpoint, so layouts don't flicker.
    breakpoint_buffer: int = 24
    form_max_w: int = 760
    small_form_max_w: int = 640


LAYOUT = Layout()

_COLORS = {Scheme.LIGHT: LIGHT, Scheme.DARK: DARK}
_METRICS = {Density.COMFORTABLE: COMFORTABLE, Density.COMPACT: COMPACT}


def colors_for(scheme: Scheme) -> ColorTokens:
    return _COLORS[Scheme(scheme)]


def metrics_for(density: Density) -> Metrics:
    return _METRICS[Density(density)]


def _css_name(field_name: str) -> str:
    return "--" + field_name.replace("_", "-")


def css_color_variables(colors: ColorTokens) -> Dict[str, str]:
    """Colors as CSS custom properties, e.g. ``{"--bg-window": "#F5F5F7"}``."""
    return {_css_name(f.name): getattr(colors, f.name).css for f in fields(colors)}


def css_metric_variables(metrics: Metrics) -> Dict[str, str]:
    """Sizes as CSS custom properties, e.g. ``{"--control-h": "28px"}``."""
    return {_css_name(f.name): f"{getattr(metrics, f.name)}px" for f in fields(metrics)}


def _css_font_stack(families: Tuple[str, ...], generic: str) -> str:
    """A CSS font-family list: named families quoted, browser fallbacks last."""
    return ", ".join([*(f'"{family}"' for family in families), generic])


def to_css() -> str:
    """CSS for a web front end: light values, dark values, and compact density.

    Light tokens go on ``:root``, dark tokens under
    ``prefers-color-scheme: dark`` and ``[data-theme="dark"]``, and compact
    sizes under ``[data-density="compact"]``.
    """

    def block(selector: str, values: Dict[str, str], indent: str = "") -> str:
        body = "\n".join(
            f"{indent}  {name}: {value};" for name, value in values.items()
        )
        return f"{indent}{selector} {{\n{body}\n{indent}}}"

    light = {
        **css_color_variables(LIGHT),
        **css_metric_variables(COMFORTABLE),
        "--font-ui": _css_font_stack(FONT_FAMILIES, "system-ui, sans-serif"),
        "--font-mono": _css_font_stack(MONO_FAMILIES[:-1], "ui-monospace, monospace"),
        "color-scheme": "light",
    }
    dark = {**css_color_variables(DARK), "color-scheme": "dark"}
    dark_media = block(':root:not([data-theme="light"])', dark, "  ")
    return "\n\n".join(
        [
            block(":root", light),
            "@media (prefers-color-scheme: dark) {\n" + dark_media + "\n}",
            block(':root[data-theme="dark"]', dark),
            block('[data-density="compact"]', css_metric_variables(COMPACT)),
        ]
    )


__all__ = [
    "BODY_PX",
    "COMFORTABLE",
    "COMPACT",
    "DARK",
    "FONT_FAMILIES",
    "LAYOUT",
    "LIGHT",
    "MONO_FAMILIES",
    "TYPE_SCALE",
    "Color",
    "ColorTokens",
    "Density",
    "Layout",
    "Metrics",
    "Scheme",
    "TextStyle",
    "colors_for",
    "css_color_variables",
    "css_metric_variables",
    "metrics_for",
    "to_css",
]
