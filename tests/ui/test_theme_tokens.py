"""Tests for the design tokens and the stylesheet built from them."""

import re
from dataclasses import fields

import pytest

from cci_ui.theme import qss
from cci_ui.theme.tokens import (
    COMFORTABLE,
    COMPACT,
    DARK,
    LIGHT,
    TYPE_SCALE,
    Color,
    ColorTokens,
    css_color_variables,
    css_metric_variables,
    to_css,
)

#: The font stacks, which test_css_export_for_a_web_front_end checks.
FONTS = {"--font-ui", "--font-mono"}


def _declared(css: str, selector: str) -> dict:
    """The custom properties *css* declares in its block for *selector*."""
    start = css.index(selector + " {")
    body = css[start : css.index("}", start)]
    return dict(re.findall(r"(--[\w-]+):\s*([^;]+);", body))


def test_css_export_gives_each_scheme_and_density_its_own_tokens():
    css = to_css()
    light = {
        name: value
        for name, value in _declared(css, ":root").items()
        if name not in FONTS
    }
    dark = css_color_variables(DARK)

    assert light == {**css_color_variables(LIGHT), **css_metric_variables(COMFORTABLE)}
    # Dark replaces the colors when the system is dark, or when the page asks.
    assert _declared(css, ':root:not([data-theme="light"])') == dark
    assert _declared(css, ':root[data-theme="dark"]') == dark
    assert _declared(css, '[data-density="compact"]') == css_metric_variables(COMPACT)


def test_both_schemes_define_every_color():
    for colors in (LIGHT, DARK):
        for field in fields(ColorTokens):
            assert isinstance(getattr(colors, field.name), Color), field.name


def test_type_scale_tones_are_color_tokens():
    names = {field.name for field in fields(ColorTokens)}
    assert {style.tone for style in TYPE_SCALE.values()} <= names


def test_color_formats_for_css_and_qt():
    translucent = Color(0, 113, 227, 0.45)

    assert Color.hex("#0071e3").hex_rgb == "#0071E3"
    assert translucent.css == "rgba(0, 113, 227, 0.45)"
    # Qt stylesheets read rgba() opacity from 0 to 255.
    assert translucent.qss == "rgba(0, 113, 227, 115)"
    with pytest.raises(ValueError):
        Color.hex("#FFF")


def test_css_export_for_a_web_front_end():
    css = to_css()

    assert "--bg-window: #F5F5F7;" in css
    assert "--control-h: 28px;" in css
    assert '--font-ui: "Inter", "Segoe UI Variable Text"' in css
    assert "--font-mono:" in css and '"monospace"' not in css
    assert '[data-density="compact"]' in css and "--control-h: 24px;" in css
    assert "@media (prefers-color-scheme: dark)" in css and "#1C1C1E" in css


@pytest.mark.parametrize("colors", [LIGHT, DARK])
@pytest.mark.parametrize("metrics", [COMFORTABLE, COMPACT])
def test_stylesheet_resolves_every_placeholder(colors, metrics):
    sheet = qss.build_stylesheet(colors, metrics)

    assert "${" not in sheet
    assert colors.accent.qss in sheet
    assert f"min-height: {metrics.control_h - 2}px" in sheet
    assert 'QLabel[textStyle="title1"] { font-size: 22px' in sheet


def test_unknown_placeholder_in_a_component_rule_fails_loudly(monkeypatch):
    monkeypatch.setattr(qss, "_fragments", [])
    qss.register_qss("QFrame { color: ${no_such_token}; }")

    with pytest.raises(KeyError):
        qss.build_stylesheet(LIGHT, COMFORTABLE)
