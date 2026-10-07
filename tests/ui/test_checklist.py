"""Tests for ChecklistComboBox, the combo box whose popup is a checklist."""

import pytest
import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QListWidget

from cci_ui.widgets import ChecklistComboBox, ChecklistItem
from cci_ui.widgets.search import SearchField

FORMS = [
    ChecklistItem("SV", "SV", "Subject visits · 1,203 rows", checked=True),
    ChecklistItem("DSSVLTFU", "DSSVLTFU", "Long-term follow-up · 311 rows"),
    ChecklistItem("AE", "AE", "Adverse events · 92 rows"),
]


@pytest.fixture
def combo(qapp):
    box = ChecklistComboBox(search_placeholder="Search forms", empty_text="Choose…")
    box.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    box.resize(160, 28)
    box.show()
    QApplication.processEvents()
    yield box
    shiboken6.delete(box)


def _rows(combo):
    return combo.findChild(QListWidget)


def _search(combo):
    return combo.findChild(SearchField)


def _shown(combo):
    """The texts of the rows the search leaves showing."""
    rows = _rows(combo)
    shown = (row for row in range(rows.count()) if not rows.isRowHidden(row))
    return [rows.item(row).text() for row in shown]


def _click(combo, text):
    rows = _rows(combo)
    (item,) = rows.findItems(text, Qt.MatchFlag.MatchExactly)
    center = rows.visualItemRect(item).center()
    QTest.mouseClick(rows.viewport(), Qt.MouseButton.LeftButton, pos=center)


def _record(signal):
    seen = []
    signal.connect(lambda *args: seen.append(args))
    return seen


def test_clicking_a_row_ticks_or_unticks_it_and_the_checklist_stays_open(combo):
    combo.set_items(FORMS)
    toggled = _record(combo.itemToggled)
    combo.showPopup()

    _click(combo, "DSSVLTFU")
    _click(combo, "SV")

    assert toggled == [("DSSVLTFU", True), ("SV", False)]
    assert combo.is_open()


def test_space_ticks_the_keyboards_row(combo):
    combo.set_items(FORMS)
    toggled = _record(combo.itemToggled)
    combo.showPopup()

    QTest.keyClick(_search(combo), Qt.Key.Key_Down)  # on to the first row
    QTest.keyClick(_rows(combo), Qt.Key.Key_Space)

    assert toggled == [("SV", False)]


def test_the_search_finds_rows_by_text_or_detail_in_any_case(combo):
    combo.set_items(FORMS)
    combo.showPopup()

    QTest.keyClicks(_search(combo), "dssv")
    by_text = _shown(combo)
    _search(combo).setText("VISITS")
    by_detail = _shown(combo)

    assert by_text == ["DSSVLTFU"]
    assert by_detail == ["SV"]


def test_new_items_while_open_keep_the_search_and_the_scroll_position(combo):
    many = [ChecklistItem(f"F{n:02}", f"F{n:02}", "Form") for n in range(1, 41)]
    combo.set_items(many)
    combo.showPopup()
    scroll = _rows(combo).verticalScrollBar()
    scroll.setValue(12)

    combo.set_items([*many, ChecklistItem("SV", "SV", "Subject visits")])

    assert scroll.value() == 12
    QTest.keyClicks(_search(combo), "f1")
    combo.set_items([*many[:12], ChecklistItem("F99", "F19 again", "Form")])
    assert _search(combo).text() == "f1"
    assert _shown(combo) == ["F10", "F11", "F12", "F19 again"]


def test_ticking_while_open_keeps_the_search(combo):
    combo.set_items(FORMS)
    combo.itemToggled.connect(
        lambda key, checked: combo.set_items(
            item._replace(checked=checked) if item.key == key else item
            for item in FORMS
        )
    )
    combo.showPopup()
    QTest.keyClicks(_search(combo), "a")

    _click(combo, "AE")

    assert _search(combo).text() == "a"
    assert _shown(combo) == ["AE"]
    assert combo.is_open()


def test_escape_closes_the_checklist(combo):
    combo.set_items(FORMS)
    combo.showPopup()

    QTest.keyClick(_search(combo), Qt.Key.Key_Escape)

    assert not combo.is_open()


def test_the_checklist_reopens_with_a_blank_search(combo):
    combo.set_items(FORMS)
    combo.showPopup()
    QTest.keyClicks(_search(combo), "AE")
    combo.hidePopup()

    combo.showPopup()

    assert _search(combo).text() == ""
    assert _shown(combo) == ["SV", "DSSVLTFU", "AE"]


def test_rows_set_when_the_popup_opens_are_the_ones_shown(combo):
    combo.set_items(FORMS[:1])
    combo.popupOpened.connect(lambda: combo.set_items(FORMS))

    combo.showPopup()

    assert _shown(combo) == ["SV", "DSSVLTFU", "AE"]


def test_the_closed_box_shows_the_summary_or_the_empty_text(combo):
    combo.set_summary("SV, DSSVLTFU")
    summary = combo.currentText()
    combo.set_summary("")

    assert summary == "SV, DSSVLTFU"
    assert combo.currentText() == ""
    assert combo.placeholderText() == "Choose…"


def test_the_checklist_opens_below_the_box(combo):
    combo.set_items(FORMS)
    combo.showPopup()

    box_bottom = combo.mapToGlobal(combo.rect().bottomLeft()).y()
    search_top = _search(combo).mapToGlobal(_search(combo).rect().topLeft()).y()

    assert search_top > box_bottom
