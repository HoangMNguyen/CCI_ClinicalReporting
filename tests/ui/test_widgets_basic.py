"""Tests for the first batch of components (step 1.3)."""

import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QLineEdit, QWidget

from cci_ui.theme import manager as theme_manager
from cci_ui.theme.manager import Theme, ThemeMode
from cci_ui.theme.tokens import COMPACT, LAYOUT, LIGHT, Density, Scheme
from cci_ui.widgets.buttons import icon_button, make_button, set_variant
from cci_ui.widgets.display import DisplayPopover
from cci_ui.widgets.labels import ElidedLabel, text_label
from cci_ui.widgets.page import Page, PageKind
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.responsive import Breakpoint, ResponsiveSplit
from cci_ui.widgets.section import Section
from cci_ui.widgets.segmented import Segment, SegmentedControl
from cci_ui.widgets.toggle import ToggleSwitch

LONG_PATH = r"C:\Users\analyst\Downloads\Core_Listings_DEMO01_2026-09-29_export.zip"


def _shown(widget, width, height):
    """Show *widget* off screen; Qt only delivers resize events to shown widgets."""
    widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    widget.resize(width, height)
    widget.show()
    QApplication.processEvents()
    return widget


def _click(widget, pos=None):
    pos = pos or widget.rect().center()
    for kind in (
        QMouseEvent.Type.MouseButtonPress,
        QMouseEvent.Type.MouseButtonRelease,
    ):
        event = QMouseEvent(
            kind,
            pos,
            widget.mapToGlobal(pos),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(widget, event)


# ---------------------------------------------------------------------------
# Buttons and labels


def test_buttons_carry_their_variant(qapp):
    primary = make_button("Export to Excel", variant="primary")
    secondary = make_button("Choose ZIP…")
    icon_only = icon_button("x", "Remove")

    assert primary.property("variant") == "primary"
    assert secondary.property("variant") is None
    assert icon_only.accessibleName() == "Remove"
    with pytest.raises(ValueError):
        set_variant(secondary, "loud")


def test_text_label_rejects_unknown_styles(qapp):
    assert text_label("Source data", style="title1").property("textStyle") == "title1"
    with pytest.raises(ValueError):
        text_label("x", style="huge")


def test_elided_label_keeps_the_full_text(qapp):
    label = _shown(ElidedLabel(LONG_PATH, tone="secondary"), 160, 20)

    shown = QLabel.text(label)
    assert label.text() == LONG_PATH
    assert shown != LONG_PATH and "…" in shown
    assert shown.startswith("C:") and shown.endswith(".zip")
    assert label.toolTip() == LONG_PATH
    assert label.property("tone") == "secondary"


def test_elided_label_shows_its_placeholder_when_empty(qapp):
    label = ElidedLabel(placeholder="No file chosen", tone="secondary")

    assert label.text() == ""
    assert QLabel.text(label) == "No file chosen"
    assert label.property("tone") == "tertiary"


# ---------------------------------------------------------------------------
# Sections and pages


def test_section_rows_label_their_fields_and_draw_inset_separators(qapp):
    section = Section("Cut-off date", "Only rows on or before this date are loaded.")
    field = QLineEdit()
    first = section.add_row("File", field)
    second = section.add_row("Apply cut-off date", ToggleSwitch(), label_width=None)

    assert first.label.buddy() is field
    assert not first._separator and second._separator
    assert section.footnote_label.isVisibleTo(section)
    untitled = Section("Title")
    assert not untitled.footnote_label.isVisibleTo(untitled)


def test_rows_follow_the_density(qapp, monkeypatch):
    section = Section()
    row = section.add_row("Cut-off", QLineEdit())
    comfortable = row.minimumHeight()
    monkeypatch.setattr(
        theme_manager, "_current", Theme(Scheme.LIGHT, Density.COMPACT, LIGHT, COMPACT)
    )
    theme_manager.theme_events().changed.emit()

    assert row.minimumHeight() == COMPACT.control_h + 2 * COMPACT.form_row_pad
    assert row.minimumHeight() < comfortable


def test_form_pages_center_a_capped_column(qapp):
    page = Page("Source data", "Load a Corelisting export.", kind=PageKind.FORM)
    page.resize(1600, 800)

    assert page.scroll_area is not None
    margin = theme_manager.current().metrics.page_margin
    assert page._column.maximumWidth() == LAYOUT.form_max_w + 2 * margin


def test_workspace_pages_fill_the_width_and_have_a_next_link(qapp):
    clicked = []
    page = Page("Joins", kind=PageKind.WORKSPACE)
    button = page.set_next("Comparisons", lambda: clicked.append(True))
    button.click()

    assert page.scroll_area is None
    assert button.text() == "Next: Comparisons"
    assert clicked == [True]


# ---------------------------------------------------------------------------
# Breakpoints and the responsive split


def test_breakpoint_has_a_dead_zone():
    point = Breakpoint(900, buffer=24)

    assert point.update(1000) and point.below is False
    assert not point.update(895)  # inside the dead zone: stays wide
    assert point.update(880) and point.below is True
    assert not point.update(905)  # inside the dead zone: stays narrow
    assert point.update(920) and point.below is False


def test_split_moves_the_panel_below_when_narrow(qapp):
    split = ResponsiveSplit(QWidget(), QWidget())
    seen = []
    split.stackedChanged.connect(seen.append)

    _shown(split, 1200, 700)
    wide = split.splitter.orientation()
    split.resize(850, 700)
    QApplication.processEvents()

    assert wide == Qt.Orientation.Horizontal
    assert split.splitter.orientation() == Qt.Orientation.Vertical
    assert split.side.maximumHeight() == int(700 * 0.4)
    assert seen == [False, True]


# ---------------------------------------------------------------------------
# Path picker


def test_external_picker_only_shows_the_path(qapp):
    picker = PathPicker(removable=True)
    changes = []
    picker.pathChanged.connect(changes.append)

    picker.set_path(LONG_PATH)
    shown_remove = picker.clear_button.isVisibleTo(picker)
    picker.clear_button.click()

    assert changes == [LONG_PATH, ""]
    assert shown_remove
    assert picker.path() == "" and not picker.clear_button.isVisibleTo(picker)


def test_file_picker_remembers_the_folder(qapp, monkeypatch, tmp_path):
    settings = QSettings(str(tmp_path / "paths.ini"), QSettings.Format.IniFormat)
    chosen = tmp_path / "exports" / "data.zip"
    chosen.parent.mkdir()
    starts = []

    def get_open_file_name(_parent, _title, start, _filter):
        starts.append(start)
        return str(chosen), ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", get_open_file_name)
    picker = PathPicker("file", settings_key="zip", settings=settings)
    picker.button.click()
    second = PathPicker("file", settings_key="zip", settings=settings)
    second.button.click()

    assert picker.path() == str(chosen)
    assert starts[1] == str(chosen.parent)


def test_files_picker_summarizes_several_files(qapp):
    picker = PathPicker("files")
    picker.set_paths(["a.csv", "b.xlsx"])

    assert picker.path_label.text() == "2 files"
    assert picker.toolTip() == "a.csv\nb.xlsx"


# ---------------------------------------------------------------------------
# Toggle switch, segmented control, display popover


def test_toggle_switch_behaves_like_a_checkbox(qapp):
    switch = ToggleSwitch("Apply cut-off date")
    switch.resize(switch.sizeHint())
    states = []
    switch.stateChanged.connect(states.append)

    _click(switch, QPoint(switch.width() - 2, switch.height() // 2))

    assert switch.isChecked()
    assert states == [Qt.CheckState.Checked.value]
    assert switch.hitButton(QPoint(switch.width() - 1, 1))


def test_toggle_switch_is_smaller_when_compact(qapp, monkeypatch):
    switch = ToggleSwitch()
    comfortable = switch.sizeHint()
    monkeypatch.setattr(
        theme_manager, "_current", Theme(Scheme.LIGHT, Density.COMPACT, LIGHT, COMPACT)
    )

    assert switch.sizeHint().height() < comfortable.height()


def test_segmented_control_picks_one_option(qapp):
    control = SegmentedControl(
        [Segment("a", "Comfortable"), Segment("b", "Compact")], current="a"
    )
    seen = []
    control.currentChanged.connect(seen.append)

    control._group.button(1).click()
    control.set_current("a")

    assert seen == ["b"]
    assert control.current() == "a"


def test_display_popover_changes_the_theme(make_manager):
    manager = make_manager()
    manager.set_mode(ThemeMode.LIGHT)
    popover = DisplayPopover(manager)

    popover.appearance._group.button(2).click()
    popover.density._group.button(1).click()

    assert manager.mode is ThemeMode.DARK
    assert manager.density is Density.COMPACT
    assert popover.appearance.current() == "dark"


# ---------------------------------------------------------------------------
# Sizes inside real layouts (what the step 1.3 review caught)


def test_a_switch_in_a_row_keeps_its_size_and_ignores_clicks_beside_it(qapp):
    section = Section()
    switch = ToggleSwitch()
    section.add_row("Apply cut-off date", switch)
    _shown(section, 700, 80)

    assert switch.width() == switch.sizeHint().width()
    assert not switch.hitButton(QPoint(switch.sizeHint().width() + 5, 5))


def test_end_aligned_fields_keep_their_width_even_without_a_label(qapp):
    section = Section()
    field = QLineEdit()
    field.setFixedWidth(150)
    row = section.add_row(None, field, end_aligned=True)
    _shown(section, 700, 80)

    assert field.width() == 150
    assert field.geometry().right() > row.width() - 40


def test_segmented_control_matches_the_control_height(make_manager):
    make_manager().apply()
    control = SegmentedControl([Segment("a", "Comfortable"), Segment("b", "Compact")])
    section = Section()
    section.add_row("Density", control)
    _shown(section, 700, 80)

    assert control.height() == theme_manager.current().metrics.control_h
    assert control.width() == control.sizeHint().width()


def test_arrow_keys_pick_the_next_segment(qapp):
    control = SegmentedControl([Segment("a", "One"), Segment("b", "Two")], current="a")
    seen = []
    control.currentChanged.connect(seen.append)
    # Tests run on Qt's offscreen platform, so this window never appears; it
    # must be a real, active window for keyboard focus to move.
    control.show()
    control.activateWindow()
    QApplication.processEvents()
    first = control._group.button(0)
    first.setFocus()

    QTest.keyClick(first, Qt.Key.Key_Right)

    assert control.current() == "b"
    assert seen == ["b"]
    control.close()


def test_form_page_column_and_footer_line_up_centred(qapp):
    page = Page("Source data", kind=PageKind.FORM)
    page.body.addWidget(Section("Corelisting ZIP"))
    button = page.set_next("Forms", lambda: None)
    _shown(page, 1600, 700)

    column = page._column
    margin = theme_manager.current().metrics.page_margin
    left_gap = column.x()
    right_gap = column.parentWidget().width() - column.geometry().right() - 1
    assert abs(left_gap - right_gap) <= 1
    assert column.width() == LAYOUT.form_max_w + 2 * margin
    button_right = button.mapTo(column, QPoint(button.width(), 0)).x()
    assert button_right == column.width() - margin


def test_popover_resizes_when_density_changes_while_open(make_manager):
    manager = make_manager()
    manager.set_density(Density.COMFORTABLE)
    anchor = _shown(QWidget(), 40, 40)
    popover = DisplayPopover(manager, anchor)
    popover.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    popover.show_below(anchor)

    manager.set_density(Density.COMPACT)
    QApplication.processEvents()  # the popover re-places itself on the next tick

    assert popover.size() == popover.sizeHint()
    popover.close()
