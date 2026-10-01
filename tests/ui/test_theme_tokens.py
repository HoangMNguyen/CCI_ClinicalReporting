"""Tests for the design tokens and the stylesheet built from them."""

import re
from dataclasses import fields
from pathlib import Path

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

MOCKUP = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "design"
    / "clinical-reporting-mockup.html"
)
# Variables the mockup uses only to draw its fake window and stage, plus its
# font stacks (they add browser-only fallbacks; test_css_export checks fonts).
MOCKUP_ONLY = re.compile(
    r"--(titlebar|close|on-close|window|shadow-window|tint|mock|stage|font)"
)


def _mockup_block(selector: str) -> dict:
    """The custom properties declared in the mockup's CSS block for *selector*."""
    css = MOCKUP.read_text(encoding="utf-8")
    start = css.index(selector + " {")
    body = css[start : css.index("}", start)]
    declared = dict(re.findall(r"(--[\w-]+):\s*([^;]+);", body))
    return {
        name: re.sub(r"\s+", "", value).upper()
        for name, value in declared.items()
        if not MOCKUP_ONLY.match(name)
    }


def _normalized(variables: dict) -> dict:
    return {
        name: re.sub(r"\s+", "", value).upper() for name, value in variables.items()
    }


def test_tokens_match_the_approved_mockup_exactly():
    light = _mockup_block(':root, .app[data-mode="light"]')
    dark = _mockup_block(':root[data-theme="dark"], .app[data-mode="dark"]')
    comfortable = _mockup_block(":root")
    compact = _mockup_block('.app[data-density="compact"]')

    assert _normalized(css_color_variables(LIGHT)) == light
    assert _normalized(css_color_variables(DARK)) == dark
    assert _normalized(css_metric_variables(COMFORTABLE)) == comfortable
    compact_metrics = _normalized(css_metric_variables(COMPACT))
    assert {name: compact_metrics[name] for name in compact} == compact


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
