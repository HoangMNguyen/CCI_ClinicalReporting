"""The stylesheet and palette as Qt actually applies them to widgets."""

import pytest
import shiboken6
from PySide6.QtCore import QDate, QPoint, Qt
from PySide6.QtGui import QFontMetrics, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QLabel,
    QLineEdit,
    QStyle,
    QStyleOptionViewItem,
    QTableView,
    QToolButton,
)

from cci_ui.theme.manager import set_invalid
from cci_ui.theme.palette import to_qpalette
from cci_ui.theme.qss import build_stylesheet
from cci_ui.theme.tokens import COMFORTABLE, COMPACT, LIGHT


def _apply_light(app, metrics=COMFORTABLE):
    app.setPalette(to_qpalette(LIGHT))
    app.setStyleSheet(build_stylesheet(LIGHT, metrics))


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


def _cut_off_cells(view):
    """The calendar cells whose text is wider than the room the style gives it."""
    model = view.model()
    cut = []
    for row in range(model.rowCount()):
        for column in range(model.columnCount()):
            index = model.index(row, column)
            text = str(index.data() or "")  # Day numbers are ints.
            if view.isColumnHidden(column) or not text:
                continue
            option = QStyleOptionViewItem()
            option.initFrom(view)
            option.rect = view.visualRect(index)
            option.text = text
            option.font = index.data(Qt.ItemDataRole.FontRole) or view.font()
            option.features |= QStyleOptionViewItem.ViewItemFeature.HasDisplay
            room = view.style().subElementRect(
                QStyle.SubElement.SE_ItemViewItemText, option, view
            )
            if QFontMetrics(option.font).horizontalAdvance(text) > room.width():
                cut.append(text)
    return cut


def _short_buttons(calendar):
    """The month and year buttons too short to show their text."""
    return [
        button.text()
        for button in calendar.findChildren(QToolButton)
        if button.text() and button.height() < button.fontMetrics().height()
    ]


@pytest.mark.parametrize("metrics", [COMFORTABLE, COMPACT])
def test_the_date_calendar_shows_whole_day_names_numbers_and_month(
    themed_app, metrics
):
    _apply_light(themed_app, metrics)
    date = QDateEdit(QDate(2026, 6, 30))
    date.setCalendarPopup(True)
    date.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    date.setFixedWidth(150)
    date.show()
    arrow = QPoint(date.width() - 8, date.height() // 2)
    QTest.mouseClick(date, Qt.MouseButton.LeftButton, pos=arrow)
    QApplication.processEvents()
    calendar = date.calendarWidget()
    shown = calendar.isVisible()
    cut = _cut_off_cells(calendar.findChild(QTableView))
    short = _short_buttons(calendar)
    shiboken6.delete(date)

    assert shown
    assert (cut, short) == ([], [])
