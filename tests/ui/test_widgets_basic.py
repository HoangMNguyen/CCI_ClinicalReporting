"""Tests for the first batch of components (step 1.3)."""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import (
    QContextMenuEvent,
    QKeySequence,
    QMouseEvent,
    QStandardItemModel,
)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QMenu,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.theme import manager as theme_manager
from cci_ui.theme.manager import Theme, ThemeMode, current
from cci_ui.theme.tokens import COMPACT, LAYOUT, LIGHT, Density, Scheme
from cci_ui.widgets.buttons import icon_button, make_button, set_variant
from cci_ui.widgets.display import DisplayPopover
from cci_ui.widgets.labels import (
    BREAK_CHANCE,
    ElidedLabel,
    WrappingLabel,
    add_break_chances,
    text_label,
)
from cci_ui.widgets.page import Page, PageKind
from cci_ui.widgets.path_picker import PathPicker, downloads_folder
from cci_ui.widgets.responsive import Breakpoint, ResponsiveSplit
from cci_ui.widgets.search import SearchField
from cci_ui.widgets.section import Section
from cci_ui.widgets.segmented import Segment, SegmentedControl
from cci_ui.widgets.side_panel import SidePanel, full_width, labeled_field
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import TableToolbar, style_table, table_card
from cci_ui.widgets.toggle import ToggleSwitch
from cci_ui.widgets.views import (
    COLUMN_MAX_W,
    EmptyState,
    PlaceholderTableWidget,
    PreviewTableView,
)

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


def _fits(characters):
    """A stand-in for a label's width: words of up to *characters* fit."""
    return lambda word: len(word) <= characters


def test_a_path_too_wide_for_a_line_breaks_after_its_separators():
    windows = r"Saved to C:\Users\analyst\Reports\DEMO01_DSMB 261001_120000.xlsx"
    mixed = r"Saved to C:/Users/analyst/Reports\DEMO01-DSMB.xlsx"

    broken = add_break_chances(windows, _fits(12))

    assert broken.replace(BREAK_CHANCE, "") == windows
    assert broken.split(BREAK_CHANCE) == [
        "Saved to C:\\",
        "Users\\",
        "analyst\\",
        "Reports\\",
        "DEMO01_",
        "DSMB 261001_",
        "120000.",
        "xlsx",
    ]
    assert add_break_chances(mixed, _fits(12)).split(BREAK_CHANCE) == [
        "Saved to C:/",
        "Users/",
        "analyst/",
        "Reports\\",
        "DEMO01-",
        "DSMB.",
        "xlsx",
    ]


def test_words_that_fit_get_no_break_chances():
    text = "Joined on SubjectIdentifierNumber,  SiteCode\tand C:\\Reports\\x.xlsx."

    assert add_break_chances(text, _fits(30)) == text
    assert add_break_chances("", _fits(0)) == ""


def test_separator_runs_dates_and_punctuation_stay_together():
    def pieces(word, characters):
        return add_break_chances(word, _fits(characters)).split(BREAK_CHANCE)

    assert pieces(r"\\server\share\folder", 8) == [
        r"\\",
        "server\\",
        "share\\",
        "folder",
    ]
    assert pieces("Listing_2026-09-29.xlsx", 11) == ["Listing_", "2026-09-29.", "xlsx"]
    # Then where a camelCase name's words meet; quotes and commas stay on.
    assert pieces("'PatientEnrollmentDateOfBirth',", 12) == [
        "'Patient",
        "Enrollment",
        "Date",
        "Of",
        "Birth',",
    ]


def test_no_break_spaces_join_a_word():
    nbsp = "\N{NO-BREAK SPACE}"
    name = f"Final{nbsp}DSMB{nbsp}Listings"  # Word wrap won't break here.

    broken = add_break_chances(f"Saved as {name}", _fits(8))

    assert broken.startswith("Saved as ") and BREAK_CHANCE in broken
    assert broken.replace(BREAK_CHANCE, "") == f"Saved as {name}"
    assert add_break_chances(name, _fits(30)) == name


def test_a_piece_with_no_boundaries_breaks_anywhere_but_keeps_accents():
    accent = "\N{COMBINING ACUTE ACCENT}"
    resume = f"Re{accent}sume{accent}"  # Résumé, as macOS writes file names.

    assert add_break_chances("ABCDEF,", _fits(3)).split(BREAK_CHANCE) == [
        *"ABCDE",
        "F,",
    ]
    assert add_break_chances(resume, _fits(1)).split(BREAK_CHANCE) == [
        "R",
        f"e{accent}",
        *"sum",
        f"e{accent}",
    ]


def test_wrapping_label_breaks_only_words_too_wide_for_it(qapp):
    text = f"Saved to {LONG_PATH}"
    label = _shown(WrappingLabel(text), 160, 120)

    assert label.text() == text and label.accessibleName() == text
    assert label.wordWrap() and label.textFormat() == Qt.TextFormat.PlainText
    assert BREAK_CHANCE in QLabel.text(label)
    assert label.minimumSizeHint().width() == 0  # Never widens its layout.

    label.resize(2000, 120)  # Now the whole path fits on a line.
    QApplication.processEvents()
    assert QLabel.text(label) == text

    label.clear()
    assert label.text() == "" and QLabel.text(label) == ""


def _menu_for(label):
    pos = QPoint(5, 5)
    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, pos, label.mapToGlobal(pos)
    )
    QApplication.sendEvent(label, event)
    # A closed menu deletes itself later; take the one that is open.
    menus = [menu for menu in label.findChildren(QMenu) if menu.isVisible()]
    return event, (menus[0] if menus else None)


def test_wrapping_label_copies_the_text_without_break_chances(qapp):
    text = f"{LONG_PATH} \N{GRINNING FACE}"  # Qt counts the emoji as 2.
    label = _shown(WrappingLabel(text), 160, 120)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    QApplication.clipboard().clear()

    event, menu = _menu_for(label)
    copy, select_all = menu.actions()
    assert event.isAccepted() and menu.isVisible()
    assert not copy.isEnabled()  # Nothing selected yet.
    select_all.trigger()
    menu.close()
    assert label.selectedText() == QLabel.text(label)  # Break chances included.

    QTest.keySequence(label, QKeySequence.StandardKey.Copy)
    assert QApplication.clipboard().text() == text

    QApplication.clipboard().clear()
    _event, menu = _menu_for(label)
    menu.actions()[0].trigger()
    menu.close()
    assert QApplication.clipboard().text() == text


def test_pressing_on_a_selection_starts_a_new_one(qapp):
    label = _shown(WrappingLabel(LONG_PATH), 160, 120)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setSelection(0, len(QLabel.text(label)))

    # Shift extends the selection; a plain press can't drag it out.
    QTest.mousePress(
        label, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier
    )
    QTest.mouseRelease(
        label, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier
    )
    assert label.hasSelectedText()
    QTest.mousePress(label, Qt.MouseButton.LeftButton)
    assert not label.hasSelectedText()
    QTest.mouseRelease(label, Qt.MouseButton.LeftButton)


def test_text_that_cant_be_selected_has_no_menu(qapp):
    label = _shown(WrappingLabel(LONG_PATH), 160, 120)

    event, menu = _menu_for(label)

    assert not event.isAccepted() and menu is None


def test_text_label_can_break_long_words(qapp):
    caption = text_label(
        LONG_PATH, style="caption", tone="secondary", break_long_words=True
    )

    assert isinstance(caption, WrappingLabel) and caption.wordWrap()
    assert caption.property("textStyle") == "caption"
    assert caption.property("tone") == "secondary"
    assert type(text_label("Folder")) is QLabel


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


def test_a_next_link_shows_an_ampersand_as_written(qapp):
    page = Page("Order & rename")
    button = page.set_next("Preview & export", lambda: None)

    assert button.text() == "Next: Preview && export"  # "&&" draws one "&".


def test_pages_without_a_footer_keep_a_bottom_margin(qapp):
    page = Page("Preview & export", kind=PageKind.SPLIT)
    margin = current().metrics.page_margin

    assert page._body_margins.contentsMargins().bottom() == margin
    page.set_next("Done", lambda: None)
    assert page._body_margins.contentsMargins().bottom() == 0  # The footer spaces it.


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


def test_file_picker_remembers_the_folder(qapp, monkeypatch, tmp_path, ini_settings):
    chosen = tmp_path / "exports" / "data.zip"
    chosen.parent.mkdir()
    starts = []

    def get_open_file_name(_parent, _title, start, _filter):
        starts.append(start)
        return str(chosen), ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", get_open_file_name)
    picker = PathPicker("file", settings_key="zip", settings=ini_settings)
    picker.button.click()
    second = PathPicker("file", settings_key="zip", settings=ini_settings)
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


def test_empty_texts_stay_hidden_and_given_texts_show(qapp):
    empty = [
        (page := Page("Joins")).subtitle_label,
        (section := Section()).title_label,
        section.footnote_label,
        (toolbar := TableToolbar()).caption_label,
        (state := EmptyState(IconName.INFO, "Nothing here")).message_label,
        (fixed_banner := StatusBanner(dismissible=False)).dismiss_button,
    ]
    given = [
        (full_page := Page("Joins", "How forms combine")).subtitle_label,
        (full_section := Section("Cut-off", "Rows on or before")).title_label,
        full_section.footnote_label,
        (full_toolbar := TableToolbar(caption="Select a row")).caption_label,
        (full_state := EmptyState(IconName.INFO, "None", "Add one")).message_label,
        (banner := StatusBanner()).dismiss_button,
    ]
    owners = [page, section, section, toolbar, state, fixed_banner]
    owners += [full_page, full_section, full_section, full_toolbar, full_state, banner]

    visible = [child.isVisibleTo(owner) for child, owner in zip(empty + given, owners)]

    assert visible == [False] * len(empty) + [True] * len(given)


# ---------------------------------------------------------------------------
# Page states and shortcuts, the side panel, small additions


def test_a_page_can_change_its_subtitle(qapp):
    page = _shown(Page("Preview & export", "Check the rows."), 600, 400)

    page.set_subtitle("1,284 rows · 42 columns")
    shown = page.subtitle_label.isVisible(), page.subtitle_label.text()
    page.set_subtitle("")

    assert shown == (True, "1,284 rows · 42 columns")
    assert not page.subtitle_label.isVisible()


def test_an_empty_state_replaces_the_body_and_actions_only(qapp):
    page = Page("Forms", "Choose forms.")
    content = QLabel("the lists")
    page.body.addWidget(content)
    refresh = make_button("Refresh")
    page.add_action(refresh)
    next_button = page.set_next("Common items", lambda: None)
    state = EmptyState(IconName.ZIP_FILE, "No data loaded")
    page.set_empty_state(state)
    _shown(page, 700, 500)
    before = page.is_showing_empty_state(), state.isVisible()

    page.show_empty_state(True)
    QApplication.processEvents()

    assert before == (False, False)
    assert page.empty_state is state
    assert page.is_showing_empty_state() and state.isVisible()
    assert not content.isVisible() and not refresh.isVisible()
    assert page.title_label.isVisible() and next_button.isVisible()
    page.show_empty_state(False)
    assert content.isVisible() and refresh.isVisible() and not state.isVisible()
    with pytest.raises(ValueError):
        page.set_empty_state(EmptyState(IconName.ZIP_FILE, "Again"))
    with pytest.raises(ValueError):
        Page("No state").show_empty_state(True)


def test_page_shortcuts_work_only_on_the_page_shown(qapp):
    window = QWidget()
    field = QLineEdit()
    stack = QStackedWidget()
    layout = QVBoxLayout(window)
    layout.addWidget(field)
    layout.addWidget(stack)
    pressed = []
    for name in ("first", "second"):
        page = Page(name)
        page.add_shortcut("F5", lambda name=name: pressed.append(name))
        stack.addWidget(page)
    second = stack.widget(1)
    second.set_empty_state(EmptyState(IconName.ZIP_FILE, "No data loaded"))
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    field.setFocus()

    QTest.keyClick(field, Qt.Key.Key_F5)
    stack.setCurrentIndex(1)
    QTest.keyClick(field, Qt.Key.Key_F5)
    second.show_empty_state(True)  # Nothing to act on: the key does nothing.
    QTest.keyClick(field, Qt.Key.Key_F5)
    window.close()

    assert pressed == ["first", "second"]


def test_a_shortcut_to_a_disabled_button_does_nothing(qapp):
    page = Page("Preview")
    button = make_button("Export")
    page.add_action(button)
    clicked = []
    button.clicked.connect(lambda: clicked.append(True))
    page.add_shortcut("Ctrl+E", button.click)
    page.show()
    page.activateWindow()
    QApplication.processEvents()

    QTest.keyClick(page, Qt.Key.Key_E, Qt.KeyboardModifier.ControlModifier)
    button.setEnabled(False)
    QTest.keyClick(page, Qt.Key.Key_E, Qt.KeyboardModifier.ControlModifier)
    page.close()

    assert clicked == [True]


def test_side_panel_sections_stack_or_sit_side_by_side(qapp):
    panel = SidePanel()
    export = panel.add_section("Export")
    export.addLayout(labeled_field("Folder", QLineEdit()))
    export.addWidget(full_width(make_button("Export to Excel")))
    save = panel.add_section("Save setting")
    save.addWidget(full_width(make_button("Save setting")))
    split = ResponsiveSplit(QLabel("grid"), panel)
    panel.follow(split)
    _shown(split, 1200, 600)
    (separator,) = [
        frame
        for frame in panel.findChildren(QFrame)
        if frame.property("cciRole") in ("separator", "separatorVertical")
    ]
    first, second = (layout.parentWidget() for layout in (export, save))
    beside = (second.y() > first.y(), separator.property("cciRole"))

    split.resize(600, 600)  # Narrow: the panel moves below the main area.
    QApplication.processEvents()

    assert beside == (True, "separator")
    assert panel.is_stacked()
    assert second.x() > first.x() and second.y() == first.y()
    assert separator.property("cciRole") == "separatorVertical"


def test_a_path_picker_names_what_its_remove_button_removes(qapp):
    picker = PathPicker(removable=True, remove_text="Remove file")

    assert picker.clear_button.toolTip() == "Remove file"
    assert PathPicker(removable=True).clear_button.toolTip() == "Remove"


def test_dialogs_start_in_the_downloads_folder_in_the_home_folder(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows reads this one.

    assert downloads_folder() == str(tmp_path / "Downloads")


def test_a_search_field_can_be_focused_ready_to_type_over(qapp):
    window = QWidget()
    field = SearchField()
    QVBoxLayout(window).addWidget(field)
    field.setText("adverse")
    window.show()
    window.activateWindow()
    QApplication.processEvents()

    field.activate()

    assert field.hasFocus() and field.selectedText() == "adverse"
    window.close()


def test_result_columns_fit_their_contents_up_to_a_limit(qapp):
    model = QStandardItemModel(3, 2)
    model.setHorizontalHeaderLabels(["Id", "Comment"])
    for row in range(3):
        model.setData(model.index(row, 0), str(row))
        model.setData(model.index(row, 1), "a long free-text comment " * 20)
    view = PreviewTableView()
    view.setModel(model)
    _shown(view, 900, 300)

    view.fit_columns()

    assert view.columnWidth(0) < 80
    assert view.columnWidth(1) == COLUMN_MAX_W


def test_an_empty_state_shows_all_of_a_wrapped_message(qapp):
    message = "Choose a Corelisting ZIP on Source data to start a report. " * 3
    state = _shown(EmptyState(IconName.ZIP_FILE, "No data loaded", message), 700, 500)
    label = state.message_label

    assert label.height() >= label.heightForWidth(label.width())
    assert label.height() > label.fontMetrics().height()  # It wraps.


def test_banners_announce_unless_told_not_to(qapp):
    assert StatusBanner().announce
    assert not StatusBanner(announce=False).announce


def test_no_line_runs_down_the_row_numbers_below_the_last_row(make_manager):
    make_manager().apply()  # The line came from the stylesheet.
    table = PlaceholderTableWidget()
    table.setColumnCount(2)
    style_table(table, row_numbers=True)
    table.setRowCount(1)
    card = _shown(table_card(table), 400, 300)
    header = table.verticalHeader()
    edge = header.mapTo(card, header.rect().topRight()).x()
    image = card.grab().toImage()
    below_rows = card.height() - 20

    colors = {image.pixelColor(x, below_rows).name() for x in range(edge - 2, edge + 3)}

    assert len(colors) == 1, colors
