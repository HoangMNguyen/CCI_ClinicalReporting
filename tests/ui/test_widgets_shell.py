"""Tests for the second batch of components (step 1.4)."""

import gc

import pytest
import shiboken6
from PySide6.QtCore import (
    QByteArray,
    QElapsedTimer,
    QPoint,
    QPointF,
    QRect,
    QSettings,
    Qt,
    qInstallMessageHandler,
)
from PySide6.QtGui import QInputMethodEvent, QKeySequence, QShortcut
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from cci_ui.theme import manager as theme_manager
from cci_ui.theme.manager import Theme, ThemeMode
from cci_ui.theme.tokens import COMPACT, LAYOUT, LIGHT, Density, Scheme
from cci_ui.widgets import status
from cci_ui.widgets.busy import REVEAL_DELAY_MS, BusyOverlay
from cci_ui.widgets.dual_list import DualListPicker
from cci_ui.widgets.page import Page
from cci_ui.widgets.search import SearchField
from cci_ui.widgets.shell import (
    MESSAGE_SHARE,
    RESTORE_SETTLE_MS,
    SIDEBAR_SHORTCUT,
    AppShell,
    AppStatusBar,
)
from cci_ui.widgets.sidebar import Sidebar, SidebarItem, StepState
from cci_ui.widgets.status import (
    MAX_TOASTS,
    TOAST_MAX_W,
    StatusBanner,
    show_error,
    show_toast,
)
from cci_ui.widgets.tables import (
    ColumnSpec,
    TableToolbar,
    configure_columns,
    style_table,
    table_card,
)
from cci_ui.widgets.views import (
    EmptyState,
    PlaceholderListWidget,
    PlaceholderTableWidget,
    PreviewTableView,
)
from cci_ui.window_state import (
    SIDEBAR_COLLAPSED_KEY,
    SIDEBAR_WIDTH_KEY,
    WindowState,
    first_launch_geometry,
)
from clinical_reporting import feedback


@pytest.fixture
def shown(qapp):
    """Show widgets as real windows on the offscreen platform; close them after."""
    opened = []

    def show(widget, width, height):
        widget.resize(width, height)
        widget.show()
        widget.activateWindow()
        QApplication.processEvents()
        opened.append(widget)
        return widget

    yield show
    for widget in opened:
        if shiboken6.isValid(widget):
            widget.close()
            widget.deleteLater()
    QApplication.processEvents()


@pytest.fixture
def compact(monkeypatch):
    """Switch the current theme to Compact for one test, then back."""
    monkeypatch.setattr(
        theme_manager, "_current", Theme(Scheme.LIGHT, Density.COMPACT, LIGHT, COMPACT)
    )
    theme_manager.theme_events().changed.emit()
    yield
    monkeypatch.undo()
    theme_manager.theme_events().changed.emit()


def _wait_until(condition, timeout_ms=2000):
    timer = QElapsedTimer()
    timer.start()
    while not condition() and timer.elapsed() < timeout_ms:
        QTest.qWait(20)
    return condition()


# ---------------------------------------------------------------------------
# Search field, placeholder views, empty state


def test_search_field_is_a_line_edit_with_a_clear_button(shown):
    field = shown(SearchField("Search forms"), 300, 30)

    assert isinstance(field, QLineEdit)
    assert field.placeholderText() == "Search forms"
    assert field.isClearButtonEnabled()
    field.grab()  # paints its own icon without errors


def test_placeholder_views_stay_standard_qt_views(shown):
    listing = PlaceholderListWidget("No files added")
    table = PlaceholderTableWidget("Select forms first.")
    preview = PreviewTableView("Load data to see a preview.")
    seen = []
    preview.modelChanged.connect(lambda: seen.append(True))

    listing.setPlaceholderText("Nothing yet")
    preview.setModel(None)
    for view in (listing, table, preview):
        shown(view, 300, 200).grab()

    assert isinstance(listing, QListWidget) and isinstance(table, QTableWidget)
    assert listing.placeholderText() == "Nothing yet"
    assert seen == [True]


def test_empty_state_runs_its_action(qapp):
    clicked = []
    state = EmptyState(
        "file-archive",
        "No data loaded",
        "Choose a Corelisting ZIP on Source data.",
        action_text="Choose ZIP…",
        on_action=lambda: clicked.append(True),
    )

    state.action_button.click()

    assert clicked == [True]
    assert state.title_label.text() == "No data loaded"


# ---------------------------------------------------------------------------
# Status banner, toasts, error dialog


def _placed_banner():
    container = QWidget()
    banner = StatusBanner()
    QVBoxLayout(container).addWidget(banner)
    return container, banner


def test_banner_takes_its_kind_from_a_message(qapp):
    container, banner = _placed_banner()
    message = feedback.error("Error saving report: disk full", details="Traceback …")

    banner.setText(message)

    assert banner.is_showing() and not banner.isHidden()
    assert banner.kind() == "error" and banner.property("kind") == "error"
    assert banner.text() == message and banner.text().startswith("Error saving")
    assert banner._details_button.isVisibleTo(banner)


def test_banner_clears_like_a_label(qapp):
    container, banner = _placed_banner()
    banner.setText("Generating preview...")
    assert banner.kind() == "info" and not banner.isHidden()

    banner.setText("")

    assert banner.text() == "" and banner.isHidden() and not banner.is_showing()


def test_banner_without_a_parent_never_becomes_a_window(qapp):
    banner = StatusBanner()
    banner.setText("Report saved")

    assert banner.is_showing() and banner.isHidden()  # no top-level flash
    container = QWidget()
    QVBoxLayout(container).addWidget(banner)
    assert not banner.isHidden()


def test_banner_details_copy_and_action(shown):
    container, banner = _placed_banner()
    shown(container, 500, 120)
    ran = []
    banner.show_message("Fix the join problems.", "warning", details="line 1\nline 2")
    banner.set_action("Go to Joins", lambda: ran.append(True))

    banner._details_button.click()
    banner._copy_button.click()
    banner.action_button.click()

    assert banner._details_box.isVisible()
    assert QApplication.clipboard().text() == "line 1\nline 2"
    assert banner._copy_button.text() == "Copied" and banner._copy_reset.isActive()
    assert ran == [True]
    with pytest.raises(ValueError):
        banner.show_message("x", "loud")


def test_banner_says_whenever_its_message_changes(qapp):
    banner = StatusBanner()
    changes = []
    banner.messageChanged.connect(lambda: changes.append(banner.text()))

    banner.setText(feedback.success("Saved"))
    banner.setText(feedback.success("Saved"))  # The same result again.
    banner.clear()

    assert changes == ["Saved", "Saved", ""]


def test_banner_dismiss_hides_it(qapp):
    container, banner = _placed_banner()
    dismissed = []
    banner.dismissed.connect(lambda: dismissed.append(True))
    banner.setText("Settings saved")

    banner.dismiss_button.click()

    assert banner.isHidden() and dismissed == [True]


def test_a_banner_with_a_long_path_stays_inside_its_width(shown):
    container, banner = _placed_banner()
    shown(container, 320, 200)
    path = "C:\\Users\\analyst\\" + "Folder\\" * 20 + "DSMB_report_261001_120000.xlsx"

    banner.setText(feedback.success(f"Report saved to {path}"))
    QApplication.processEvents()

    assert banner.minimumSizeHint().width() <= 320
    assert banner.width() <= 320 and banner._label.width() < 320
    assert banner.text() == f"Report saved to {path}"
    assert banner.dismiss_button.geometry().right() <= banner.width()


def test_a_long_toast_stays_inside_the_window(shown):
    window = shown(QWidget(), 600, 400)
    text = "Settings saved to C:\\Users\\analyst\\" + "Folder\\" * 40 + "DSMB.json"

    toast = show_toast(window, text)
    QApplication.processEvents()

    assert toast.width() <= min(TOAST_MAX_W, 600 - 48)
    assert toast.accessibleName() == text and toast.label.text() == text
    shown_text = super(type(toast.label), toast.label).text()
    assert shown_text != text and shown_text.endswith("DSMB.json")


def test_a_toast_keeps_its_fade_and_shadow(shown):
    window = shown(QWidget(), 600, 400)

    toast = show_toast(window, "Saved", duration_ms=60)
    QApplication.processEvents()
    # PySide keeps no reference to an installed effect, so the toast must:
    # collect any effect that only a local held.
    gc.collect()
    pill = toast.findChild(QFrame, options=Qt.FindChildOption.FindDirectChildrenOnly)
    shadow = pill.graphicsEffect()

    assert isinstance(toast.graphicsEffect(), QGraphicsOpacityEffect)
    assert isinstance(shadow, QGraphicsDropShadowEffect)
    assert shadow.blurRadius() == 24 and shadow.offset() == QPointF(0, 6)


def test_a_shown_toast_redraws_without_qt_warnings(shown):
    window = shown(QWidget(), 600, 400)
    toast = show_toast(window, "Saved", duration_ms=5000)
    QTest.qWait(400)  # Faded in.
    warnings = []
    previous = qInstallMessageHandler(lambda kind, context, text: warnings.append(text))
    try:
        toast.repaint()
        QApplication.processEvents()
    finally:
        qInstallMessageHandler(previous)

    # Its fade and its pill's shadow never draw at once: Qt can't nest them.
    assert warnings == []


def test_toasts_stack_up_to_a_limit_and_go_away(shown, shown_windows):
    window = shown(QWidget(), 600, 400)
    for number in range(MAX_TOASTS + 2):
        show_toast(window, f"Saved {number}", duration_ms=60)
    QApplication.processEvents()
    host = window.findChild(status.ToastHost)

    assert len(host.toasts()) == MAX_TOASTS
    # Evicted toasts don't flash as windows of their own.
    assert [label for widget, label in shown_windows if widget is not window] == []
    assert _wait_until(lambda: host.toasts() == [])


def test_a_toast_of_an_unknown_kind_is_refused(shown):
    window = shown(QWidget(), 600, 400)

    with pytest.raises(ValueError, match="Unknown message kind 'done'"):
        show_toast(window, "Saved", "done")


def test_show_error_puts_details_behind_the_button(qapp, monkeypatch):
    shown_box = {}

    def fake_exec(box):
        shown_box["text"], shown_box["details"] = box.text(), box.detailedText()
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    show_error(None, "Export failed", "Couldn't write the file.", "Traceback …")

    assert shown_box == {"text": "Couldn't write the file.", "details": "Traceback …"}


def test_show_error_can_add_an_informative_sentence(qapp, monkeypatch):
    shown_box = {}

    def fake_exec(box):
        shown_box["text"], shown_box["informative"] = box.text(), box.informativeText()
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    show_error(
        None, "Export failed", "Couldn't write the file.", informative="Try again."
    )

    assert shown_box == {
        "text": "Couldn't write the file.",
        "informative": "Try again.",
    }


# ---------------------------------------------------------------------------
# Busy overlay


def test_busy_overlay_blocks_clicks_keys_and_shortcuts(shown):
    target = shown(QWidget(), 400, 300)
    field = QLineEdit(target)
    field.setGeometry(20, 20, 200, 28)
    field.show()
    field.setFocus()
    fired = []
    shortcut = QShortcut(QKeySequence("Ctrl+S"), target)
    shortcut.activated.connect(lambda: fired.append(True))
    overlay = BusyOverlay(target)
    changes = []
    overlay.busyChanged.connect(changes.append)

    overlay.start("Reading Corelisting ZIP…")
    # Focus stays put, so starting work never makes a field commit its edit.
    assert QApplication.focusWidget() is field
    assert target.childAt(field.geometry().center()) is overlay
    assert not overlay.is_revealed()
    QTest.keyClicks(field, "typed")
    QTest.keyClick(field, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(field, Qt.Key.Key_Tab)
    QTest.mouseClick(field, Qt.MouseButton.LeftButton)
    assert _wait_until(overlay.is_revealed, REVEAL_DELAY_MS + 500)
    overlay.stop()

    assert field.text() == "" and fired == []
    assert QApplication.focusWidget() is field
    assert not overlay.isVisible() and changes == [True, False]
    assert overlay.message() == "Reading Corelisting ZIP…"
    QTest.keyClicks(field, "ok")
    assert field.text() == "ok"


def test_a_click_whose_press_starts_the_work_is_dropped(shown):
    target = shown(QWidget(), 400, 300)
    field = QLineEdit(target)
    field.setGeometry(20, 20, 200, 28)
    button = QPushButton("Remove input", target)
    button.setGeometry(20, 60, 120, 28)
    for widget in (field, button):
        widget.show()
    field.setFocus()
    QTest.keyClicks(field, "2024-06-01")
    overlay = BusyOverlay(target)
    # Like the cut-off date field: committing the edit starts work.
    field.editingFinished.connect(overlay.start)
    clicked = []
    button.clicked.connect(lambda: clicked.append(True))

    # The press moves focus to the button, the field commits, work starts,
    # and only then does Qt deliver the press to the (now covered) button.
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert overlay.busy
    overlay.stop()

    assert clicked == []
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert clicked == [True]


def test_busy_overlay_blocks_typing_anywhere_in_its_window(shown):
    # Like an AppShell: the overlay covers the central widget of a main window.
    window = shown(QMainWindow(), 400, 300)
    central = QWidget()
    window.setCentralWidget(central)
    field = QLineEdit(central)
    field.show()
    fired = []
    shortcut = QShortcut(QKeySequence("Ctrl+S"), window)
    shortcut.activated.connect(lambda: fired.append(True))
    overlay = BusyOverlay(central)
    window.setFocus()  # Nothing inside the overlay has focus.
    QApplication.processEvents()

    overlay.start()
    QTest.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    typed = QInputMethodEvent()
    typed.setCommitString("typed with an input method")
    QApplication.sendEvent(field, typed)
    overlay.stop()

    assert fired == [] and field.text() == ""
    QTest.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    assert fired == [True]


def test_toasts_stay_above_the_busy_overlay(shown):
    window = shown(QWidget(), 600, 400)
    show_toast(window, "Settings saved", duration_ms=5000)
    overlay = BusyOverlay(window)

    overlay.start()
    stacking = [child for child in window.children() if isinstance(child, QWidget)]
    overlay.stop()

    assert stacking.index(window.findChild(status.ToastHost)) > stacking.index(overlay)


# ---------------------------------------------------------------------------
# Tables


def test_column_rules_and_density_rows(qapp, compact):
    table = QTableWidget(2, 3)
    style_table(table)
    configure_columns(
        table, [ColumnSpec("contents"), ColumnSpec(), ColumnSpec("fixed", 84)]
    )
    header = table.horizontalHeader()

    assert header.sectionResizeMode(0).name == "ResizeToContents"
    assert header.sectionResizeMode(1).name == "Stretch"
    assert header.sectionSize(2) == 84
    assert not table.showGrid() and not table.verticalHeader().isVisible()
    assert table.verticalHeader().defaultSectionSize() == COMPACT.row_h


def test_column_rules_need_the_columns_first(qapp):
    with pytest.raises(ValueError):
        configure_columns(QTableWidget(), [ColumnSpec()])


def test_a_deleted_table_does_not_stop_density_updates(qapp, compact):
    gone, kept = QTableWidget(), QTableWidget()
    style_table(gone)
    style_table(kept)
    shiboken6.delete(gone)

    theme_manager.theme_events().changed.emit()

    assert kept.verticalHeader().defaultSectionSize() == COMPACT.row_h


def test_gliding_past_a_cell_dropdown_neither_focuses_nor_selects(make_manager, shown):
    # The theme's hover rule turns on mouse tracking, and its cell padding
    # leaves a margin beside a cell widget.
    make_manager().apply()
    table = QTableWidget(2, 1)
    style_table(table)
    combo = QComboBox()
    combo.addItems(["Left join", "Inner join"])
    table.setCellWidget(1, 0, combo)
    shown(table, 300, 200)
    table.selectRow(0)
    table.setFocus()  # Showing the window focused the combo.
    cell = table.visualRect(table.model().index(1, 0))
    assert table.hasFocus() and combo.x() > cell.left()

    for x in range(cell.left(), combo.x(), 2):
        point = table.viewport().mapTo(table, QPoint(x, cell.center().y()))
        QTest.mouseMove(table.windowHandle(), point)

    assert not combo.hasFocus()
    assert [index.row() for index in table.selectionModel().selectedRows()] == [0]


def test_column_specs_are_validated():
    with pytest.raises(ValueError):
        ColumnSpec("wide")
    with pytest.raises(ValueError):
        ColumnSpec("fixed")


def test_table_card_and_toolbar(qapp):
    table = QTableWidget()
    card = table_card(table)
    toolbar = TableToolbar(
        add_tooltip="Add filter", caption="Select a row, then press −."
    )

    assert card.property("cciRole") == "card"
    assert table.property("cciRole") == "embedded"
    assert toolbar.add_button.accessibleName() == "Add filter"
    assert toolbar.caption_label.text().startswith("Select a row")


# ---------------------------------------------------------------------------
# Dual list picker


def test_dual_list_counts_follow_the_lists(qapp):
    picker = DualListPicker(available_title="Available forms")
    picker.available.addItems(["AE", "CM", "DM"])
    picker.selected.addItem("VS")
    picker.available.takeItem(0)

    assert (picker.available_count(), picker.selected_count()) == (2, 1)
    picker.selected.clear()
    assert picker.selected_count() == 0
    assert picker.add_button.accessibleName() == "Add selected"


# ---------------------------------------------------------------------------
# Sidebar


def _sidebar():
    sidebar = Sidebar("Clinical Reporting")
    sidebar.add_section("Data")
    sidebar.add_item("source", "Source data", "database")
    sidebar.add_section("Rules")
    sidebar.add_item("joins", "Joins", "merge")
    return sidebar


def test_sidebar_statuses_become_tooltips(qapp):
    sidebar = _sidebar()
    sidebar.set_status("joins", StepState.ERROR, tip="1 problem")
    sidebar.set_status("source", count=18)

    assert sidebar.item("joins").toolTip() == "Joins — 1 problem"
    assert sidebar.item("source").count() == 18
    with pytest.raises(ValueError):
        sidebar.add_item("joins", "Joins again", "merge")


def test_sidebar_selection_by_code_and_by_click(shown):
    sidebar = shown(_sidebar(), 240, 300)
    picked = []
    sidebar.currentChanged.connect(picked.append)

    sidebar.set_current("source")
    sidebar.item("joins").click()

    assert picked == ["joins"] and sidebar.current() == "joins"


def test_sidebar_arrow_keys_pick_the_next_item(shown):
    sidebar = shown(_sidebar(), 240, 300)
    sidebar.set_current("source")
    picked = []
    sidebar.currentChanged.connect(picked.append)
    sidebar.item("source").setFocus()

    QTest.keyClick(sidebar.item("source"), Qt.Key.Key_Down)

    assert sidebar.current() == "joins" and picked == ["joins"]


def test_sidebar_titles_make_no_keyboard_shortcut(qapp):
    item = SidebarItem("order", "Order & rename", "list")

    assert item.title() == "Order & rename" and item.text() == "Order && rename"


def test_clicking_the_sidebar_leaves_the_focus_where_it_was(shown):
    window = QWidget()
    field = QLineEdit()
    sidebar = _sidebar()
    layout = QVBoxLayout(window)
    layout.addWidget(field)
    layout.addWidget(sidebar)
    shown(window, 300, 400)
    field.setFocus()

    QTest.mouseClick(sidebar.item("joins"), Qt.MouseButton.LeftButton)

    # A field losing focus commits its edit, which may start work.
    assert sidebar.current() == "joins" and QApplication.focusWidget() is field


def test_collapsed_sidebar_hides_titles_and_shows_rules(qapp):
    sidebar = _sidebar()
    sidebar.set_collapsed(True)

    assert not sidebar.title_label.isVisibleTo(sidebar)
    rules = [rule.isVisibleTo(sidebar) for rule in sidebar._section_rules]
    assert rules == [False, True]
    assert sidebar.toggle_button.toolTip().startswith("Show sidebar")


# ---------------------------------------------------------------------------
# App shell


def _shell(make_manager, **flags):
    shell = AppShell(make_manager(), title="Clinical Reporting", **flags)
    shell.add_page("source", Page("Source data"), title="Source data", section="Data")
    shell.add_page("joins", Page("Joins"), title="Joins", section="Rules")
    return shell


def _comfortable(make_manager):
    """A theme manager in Comfortable (not Automatic: the test screen is small)."""
    manager = make_manager()
    manager.set_density(Density.COMFORTABLE)
    manager.apply()
    return manager


def test_shell_switches_pages_and_shows_where_you_are(make_manager):
    shell = _shell(make_manager)
    shell.set_context("DEMO01")
    seen = []
    shell.currentPageChanged.connect(seen.append)

    shell.set_current("joins")
    shell.set_current("joins")

    assert shell.stack.currentWidget() is shell.page("joins")
    assert shell.sidebar.current() == "joins"
    assert shell.header.context_label.text() == "DEMO01"
    assert shell.header.page_label.text() == "Joins"
    assert seen == ["joins"]


def test_shell_collapses_the_sidebar_on_narrow_windows(make_manager, shown):
    shell = shown(_shell(make_manager), 1300, 700)
    wide = shell.is_sidebar_collapsed()
    shell.resize(1000, 700)
    QApplication.processEvents()

    assert not wide and shell.is_sidebar_collapsed()
    assert shell.sidebar.width() == LAYOUT.sidebar_collapsed_w
    # The pages move over; no gap is left where the sidebar was.
    assert shell.splitter.widget(1).x() < LAYOUT.sidebar_collapsed_w + 10


def test_a_restored_sidebar_state_holds_while_the_window_opens(make_manager, shown):
    shell = _shell(make_manager)
    shell.restore_sidebar(260, collapsed=True)

    # As a window reopening maximized: laid out at its normal size first.
    shown(shell, 1000, 700)
    shell.resize(1900, 700)
    QApplication.processEvents()
    held = shell.is_sidebar_collapsed()
    QTest.qWait(RESTORE_SETTLE_MS + 100)
    shell.resize(1000, 700)
    shell.resize(1900, 700)

    assert held
    assert not shell.is_sidebar_collapsed()  # Settled: crossing works again.


def test_a_state_restored_on_a_shown_shell_also_settles(make_manager, shown):
    shell = shown(_shell(make_manager), 1300, 700)

    shell.restore_sidebar(260, collapsed=False)
    QTest.qWait(RESTORE_SETTLE_MS + 100)
    shell.resize(900, 700)

    assert shell.is_sidebar_collapsed()


def test_restored_sidebar_state_survives_the_first_show(make_manager, shown):
    collapsed_wide = _shell(make_manager)
    collapsed_wide.restore_sidebar(260, collapsed=True)
    expanded_narrow = _shell(make_manager)
    expanded_narrow.restore_sidebar(260, collapsed=False)

    shown(collapsed_wide, 1300, 700)
    shown(expanded_narrow, 1000, 700)

    assert collapsed_wide.is_sidebar_collapsed()
    assert not expanded_narrow.is_sidebar_collapsed()
    assert expanded_narrow.sidebar.width() == 260


def test_dragging_the_sidebar_reports_its_width(make_manager, shown):
    shell = shown(_shell(make_manager), 1300, 700)
    widths = []
    shell.sidebarWidthChanged.connect(widths.append)

    shell.splitter.setSizes([280, 1020])
    shell.splitter.splitterMoved.emit(280, 1)

    assert widths == [280] and shell.sidebar_width() == 280


def test_sidebar_shortcut_toggles_at_any_width(make_manager, shown):
    shell = shown(_shell(make_manager), 1300, 700)
    shell.sidebar.item("source").setFocus()

    QTest.keySequence(shell.sidebar.item("source"), QKeySequence(SIDEBAR_SHORTCUT))

    assert shell.is_sidebar_collapsed()


def test_an_opted_in_shell_starts_as_a_strip_in_compact(make_manager, shown, compact):
    shell = shown(_shell(make_manager, collapse_in_compact=True), 1300, 700)
    started_collapsed = shell.is_sidebar_collapsed()
    shell.sidebar.item("source").setFocus()

    QTest.keySequence(shell.sidebar.item("source"), QKeySequence(SIDEBAR_SHORTCUT))

    assert started_collapsed and not shell.is_sidebar_collapsed()


def test_each_density_gets_its_own_sidebar_state_back(make_manager, shown):
    manager = _comfortable(make_manager)
    shell = shown(_shell(make_manager, collapse_in_compact=True), 1300, 700)
    started_open = not shell.is_sidebar_collapsed()
    shell.toggle_sidebar()  # Hidden in Comfortable.
    manager.set_density(Density.COMPACT)
    compact_default = shell.is_sidebar_collapsed()
    shell.toggle_sidebar()  # Opened in Compact.
    manager.set_mode(ThemeMode.DARK)  # Not a density change.
    compact_after_dark = shell.is_sidebar_collapsed()
    manager.set_density(Density.COMFORTABLE)
    comfortable_again = shell.is_sidebar_collapsed()
    manager.set_density(Density.COMPACT)
    compact_again = shell.is_sidebar_collapsed()
    manager.set_density(Density.COMFORTABLE)

    assert started_open and compact_default
    assert not compact_after_dark
    assert comfortable_again and not compact_again


def test_a_shell_without_the_flags_ignores_density_changes(make_manager, shown):
    manager = _comfortable(make_manager)
    shell = shown(_shell(make_manager), 1300, 700)
    shell.toggle_sidebar()  # Hidden in Comfortable.
    manager.set_density(Density.COMPACT)
    in_compact = shell.is_sidebar_collapsed()
    shell.toggle_sidebar()  # Opened in Compact.
    manager.set_density(Density.COMFORTABLE)

    assert in_compact and not shell.is_sidebar_collapsed()


def test_the_badge_strip_is_wider_than_the_plain_strip(make_manager, shown):
    plain = shown(_shell(make_manager), 1000, 700)
    badged = shown(_shell(make_manager, strip_badges=True), 1000, 700)
    badged.sidebar.set_status("source", count=999)
    badged.sidebar.set_status("joins", StepState.WARNING)

    assert plain.is_sidebar_collapsed() and badged.is_sidebar_collapsed()
    assert (plain.sidebar.width(), badged.sidebar.width()) == (56, 72)
    badged.grab()  # Paints the badges beside the icons without errors.


def test_shell_shows_the_current_page_and_a_display_button_with_a_theme(
    make_manager,
):
    shell = _shell(make_manager)
    shell.set_current("joins")
    bare = AppShell(None, title="Test tool")

    assert shell.current_page() is shell.page("joins")
    assert shell.display_button is not None and bare.display_button is None
    assert bare.current_page() is None


def _help(key):
    return f"## {key} help\n\n1. **First** step."


def test_the_help_button_shows_the_open_pages_help_beside_it(make_manager, shown):
    shell = shown(_shell(make_manager, help_text=_help), 1300, 700)
    before = shell.is_help_visible()

    QTest.mouseClick(shell.help_button, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    opened = (
        shell.is_help_visible(),
        shell.help_panel.title.text(),
        shell.help_panel.body.toMarkdown().startswith("## source help"),
        shell.help_panel.x() > shell.stack.x() + shell.stack.width() - 1,
    )
    shell.set_current("joins")
    followed = shell.help_panel.title.text(), shell.help_panel.body.toPlainText()
    QTest.mouseClick(shell.help_button, Qt.MouseButton.LeftButton)

    assert not before
    assert opened == (True, "Help: Source data", True, True)
    assert followed == ("Help: Joins", "joins help\nFirst step.")
    assert not shell.is_help_visible() and not shell.help_button.isChecked()


def test_closing_the_help_unchecks_its_button(make_manager, shown):
    shell = shown(_shell(make_manager, help_text=_help), 1300, 700)
    shell.help_button.click()

    shell.help_panel.close_button.click()

    assert not shell.is_help_visible() and not shell.help_button.isChecked()


def test_the_help_keeps_the_width_it_was_dragged_to(make_manager, shown):
    shell = shown(_shell(make_manager, help_text=_help), 1300, 700)
    shell.help_button.click()
    QApplication.processEvents()
    splitter = shell.help_panel.parentWidget()
    total = sum(splitter.sizes())
    splitter.setSizes([total - 420, 420])
    splitter.splitterMoved.emit(total - 420, 1)  # As a drag of the edge.

    shell.help_button.click()
    shell.help_button.click()
    QApplication.processEvents()

    assert shell.help_panel.width() == 420


def test_a_shell_without_help_text_has_no_help_button(make_manager):
    shell = _shell(make_manager)

    assert shell.help_button is None and shell.help_panel is None


def test_status_bar_shows_a_summary_and_the_latest_message(qapp):
    status_bar = AppStatusBar()

    status_bar.set_summary("DEMO01 · 3 forms")
    status_bar.show_message("Cannot run:\n  Join order 2 is used twice.", "warning")
    shown = status_bar.message(), status_bar.message_kind()
    icon_shown = status_bar.kind_icon.isVisibleTo(status_bar)
    status_bar.clear_message()

    assert status_bar.summary() == "DEMO01 · 3 forms"
    assert shown == ("Cannot run: Join order 2 is used twice.", "warning")
    assert icon_shown and not status_bar.kind_icon.isVisibleTo(status_bar)
    assert (status_bar.message(), status_bar.message_kind()) == ("", "")
    with pytest.raises(ValueError):
        status_bar.show_message("Saved", "done")


def test_long_messages_leave_room_for_the_summary(make_manager, shown):
    shell = shown(_shell(make_manager), 1300, 700)
    status_bar = shell.status_bar
    status_bar.set_summary("DEMO01 · 3 forms · 12 items")

    status_bar.show_message("Report saved successfully to " + "C:\\folder" * 40)
    QApplication.processEvents()

    assert status_bar.message_label.width() <= MESSAGE_SHARE * status_bar.width() + 1
    assert status_bar.summary_label.width() > 100
    assert status_bar.height() == theme_manager.current().metrics.status_h


def test_step_shortcuts_go_to_the_next_and_previous_page(make_manager, shown):
    shell = shown(_shell(make_manager), 1300, 700)
    shell.add_page("preview", Page("Preview"), title="Preview", section="Output")
    focus = shell.sidebar.item("source")
    focus.setFocus()
    ctrl = Qt.KeyboardModifier.ControlModifier
    ctrl_shift = ctrl | Qt.KeyboardModifier.ShiftModifier
    seen = []

    for key, modifiers in [
        (Qt.Key.Key_PageDown, ctrl),
        (Qt.Key.Key_Tab, ctrl),
        (Qt.Key.Key_Tab, ctrl),  # Already on the last page.
        (Qt.Key.Key_PageUp, ctrl),
        # Ctrl+Shift+Tab, as the Windows and Linux keyboard maps offer it for
        # shortcuts, then as the key event itself has it.
        (Qt.Key.Key_Tab, ctrl_shift),
        (Qt.Key.Key_PageDown, ctrl),
        (Qt.Key.Key_Backtab, ctrl_shift),
    ]:
        QTest.keyClick(focus, key, modifiers)
        seen.append(shell.current())

    assert seen == ["joins", "preview", "preview", "joins", "source", "joins", "source"]


def test_small_tool_shell_has_no_sidebar(make_manager):
    shell = AppShell(make_manager(), title="Safety Automation", with_sidebar=False)
    shell.add_page("run", Page("AE & DLT listing"), title="AE & DLT listing")

    assert shell.sidebar is None
    assert shell.header.context_label.text() == "Safety Automation"


def test_shell_busy_overlay_covers_everything(make_manager, shown):
    shell = shown(_shell(make_manager), 1300, 700)
    shell.busy.start("Building preview…")

    assert shell.busy.geometry() == shell.rect()
    shell.busy.stop()


# ---------------------------------------------------------------------------
# Window state


def test_first_launch_fits_and_centres_on_the_screen(qapp):
    screen = QApplication.primaryScreen()
    area = screen.availableGeometry()

    rect = first_launch_geometry((10_000, 10_000), screen)

    assert rect.width() <= area.width() * 0.9
    assert rect.height() <= area.height() * 0.9
    assert abs(rect.center().x() - area.center().x()) <= 1
    assert abs(rect.center().y() - area.center().y()) <= 1


def test_first_launch_on_a_screen_smaller_than_the_minimum(qapp):
    screen = QApplication.primaryScreen()
    area = screen.availableGeometry()
    too_big = (area.width() + 500, area.height() + 500)

    rect = first_launch_geometry((800, 600), screen, min_size=too_big)

    assert area.contains(rect)
    assert rect.size() == area.size()


def test_window_geometry_survives_a_restart(qapp, ini_settings):
    state = WindowState("clinical-reporting", ini_settings)
    window = QWidget()

    used_saved = state.restore(window, first_size=(800, 600), min_size=(400, 300))
    window.setGeometry(QRect(50, 60, 700, 500))
    state.save(window)
    reopened = QWidget()
    used_saved_again = WindowState("clinical-reporting", ini_settings).restore(
        reopened, first_size=(800, 600), min_size=(400, 300)
    )

    assert not used_saved and used_saved_again
    assert reopened.size() == window.size()
    assert reopened.minimumSize().width() == 400
    saved = ini_settings.value("windows/clinical-reporting/geometry")
    assert isinstance(saved, QByteArray)


def test_window_state_keeps_other_values(qapp, ini_settings):
    state = WindowState("safety", ini_settings)

    state.set_value("sidebar_width", 260)

    assert int(state.value("sidebar_width")) == 260
    assert state.value("missing", "default") == "default"


def test_remember_restores_the_window_and_sidebar_after_a_restart(
    make_manager, qapp, ini_settings
):
    window = QMainWindow()
    shell = _shell(make_manager)
    window.setCentralWidget(shell)
    WindowState("clinical-reporting", ini_settings).remember(
        window, first_size=(1300, 700), min_size=(900, 500), shell=shell
    )
    window.show()
    shell.set_sidebar_width(280)
    shell.set_sidebar_collapsed(True)
    size = window.size()
    window.close()  # Saves.

    reopened = QMainWindow()
    reopened_shell = _shell(make_manager)
    reopened.setCentralWidget(reopened_shell)
    WindowState("clinical-reporting", ini_settings).remember(
        reopened, first_size=(800, 600), min_size=(900, 500), shell=reopened_shell
    )
    reopened.show()
    QApplication.processEvents()
    try:
        assert reopened.size() == size
        assert reopened_shell.is_sidebar_collapsed()
        assert reopened_shell.sidebar_width() == 280
    finally:
        reopened.close()
        shiboken6.delete(window)
        shiboken6.delete(reopened)


def test_window_state_keeps_each_densitys_sidebar_state(make_manager, ini_settings):
    manager = _comfortable(make_manager)
    shell = _shell(make_manager, collapse_in_compact=True)
    shell.set_sidebar_collapsed(True)  # Hidden in Comfortable.
    manager.set_density(Density.COMPACT)
    shell.set_sidebar_collapsed(False)  # Opened in Compact.
    WindowState("clinical-reporting", ini_settings).save_sidebar(shell)

    reopened = _shell(make_manager, collapse_in_compact=True)  # Opens in Compact.
    WindowState("clinical-reporting", ini_settings).restore_sidebar(reopened)
    in_compact = reopened.is_sidebar_collapsed()
    manager.set_density(Density.COMFORTABLE)

    assert not in_compact and reopened.is_sidebar_collapsed()


def test_window_state_reads_numbers_and_flags_stored_as_text(qapp, ini_settings):
    state = WindowState("safety", ini_settings)
    state.set_value(SIDEBAR_WIDTH_KEY, 260)
    state.set_value(SIDEBAR_COLLAPSED_KEY, False)
    ini_settings.sync()
    reread = WindowState(
        "safety", QSettings(ini_settings.fileName(), ini_settings.format())
    )

    assert reread.value(SIDEBAR_WIDTH_KEY, 0, int) == 260
    assert reread.value(SIDEBAR_COLLAPSED_KEY, True, bool) is False
