"""The stylesheet and palette as Qt actually applies them to widgets."""

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QCheckBox, QLabel

from cci_ui.theme.palette import to_qpalette
from cci_ui.theme.qss import build_stylesheet
from cci_ui.theme.tokens import COMFORTABLE, LIGHT


def _apply_light(app):
    app.setPalette(to_qpalette(LIGHT))
    app.setStyleSheet(build_stylesheet(LIGHT, COMFORTABLE))


def _text_color(widget, group=QPalette.ColorGroup.Active):
    widget.ensurePolished()
    return widget.palette().color(group, QPalette.ColorRole.WindowText).name().upper()


def test_disabled_widgets_use_the_disabled_text_color(themed_app):
    _apply_light(themed_app)
    checkbox = QCheckBox("Apply cut-off date")
    checkbox.setEnabled(False)

    disabled = _text_color(checkbox, QPalette.ColorGroup.Disabled)

    assert disabled == LIGHT.text_disabled.hex_rgb


def test_tone_recolors_any_text_style(themed_app):
    _apply_light(themed_app)
    label = QLabel("Load a Corelisting export to start a report.")
    label.setProperty("textStyle", "body")
    label.setProperty("tone", "secondary")

    assert _text_color(label) == LIGHT.text_secondary.hex_rgb


def test_text_style_sets_size_and_weight(themed_app):
    _apply_light(themed_app)
    title = QLabel("Source data")
    title.setProperty("textStyle", "title1")
    title.ensurePolished()

    assert title.font().pixelSize() == 22
    assert title.font().weight() == 700
