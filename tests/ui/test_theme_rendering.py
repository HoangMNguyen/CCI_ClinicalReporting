"""The stylesheet and palette as Qt actually applies them to widgets."""

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit

from cci_ui.theme.manager import set_invalid
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


def test_set_invalid_draws_a_combo_in_the_danger_color_and_back(themed_app):
    _apply_light(themed_app)
    combo = QComboBox()
    combo.addItem("2")

    def text_color():
        combo.ensurePolished()
        role = QPalette.ColorRole.ButtonText
        return combo.palette().color(role).name().upper()

    set_invalid(combo, True)
    assert text_color() == LIGHT.danger_text.hex_rgb
    assert combo.font().weight() == 600

    set_invalid(combo, False)
    assert text_color() == LIGHT.text_primary.hex_rgb
    assert combo.font().weight() == 400


def test_set_invalid_draws_a_line_edit_in_the_danger_color_and_back(themed_app):
    _apply_light(themed_app)
    edit = QLineEdit("VI.SITS")

    def text_color():
        edit.ensurePolished()
        return edit.palette().color(QPalette.ColorRole.Text).name().upper()

    set_invalid(edit, True)
    assert text_color() == LIGHT.danger_text.hex_rgb

    set_invalid(edit, False)
    assert text_color() == LIGHT.text_primary.hex_rgb
