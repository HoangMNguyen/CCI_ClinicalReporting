"""The Clinical Reporting window as a whole (beyond its background tasks).

Most tests use the DEMO01 sample data the preview tool shows, under the real
cci_ui theme.
"""

import sys

import pytest
import shiboken6
from PySide6.QtCore import SIGNAL
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from cci_ui.theme.manager import ThemeMode, current, theme_events
from clinical_reporting import feedback
from clinical_reporting.models import JoinHow
from clinical_reporting.ui.preview import PAGE_KEYS, build_preview_window
from clinical_reporting.ui.window import Widget


@pytest.fixture
def theme(make_manager):
    manager = make_manager()
    manager.apply()
    return manager


@pytest.fixture
def sample_window(theme, settle):
    """The window holding the configured sample report, shown and themed."""
    window = build_preview_window()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    yield window
    window.close()
    settle(window.task_runner)
    shiboken6.delete(window)


def _theme_listeners() -> int:
    return theme_events().receivers(SIGNAL("changed()"))


def test_the_window_follows_theme_changes_until_it_is_deleted(qapp, monkeypatch):
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: raised.append(args[1]))
    # A first window lets any module-wide theme listeners connect for good.
    shiboken6.delete(Widget())
    before = _theme_listeners()

    window = Widget()
    assert _theme_listeners() > before
    shiboken6.delete(window)
    theme_events().changed.emit()

    assert _theme_listeners() == before
    assert raised == []


def test_a_theme_change_only_recolors(qapp):
    window = Widget()
    shown = feedback.warning("Cannot run:\n- Static filter 1 must have an item.")
    window.label_run_confirmation.setText(shown)
    try:
        theme_events().changed.emit()

        assert window.label_run_confirmation.text() == shown
    finally:
        shiboken6.delete(window)


@pytest.mark.parametrize("mode", [ThemeMode.LIGHT, ThemeMode.DARK])
def test_every_page_shows_and_the_preview_builds(sample_window, theme, settle, mode):
    theme.set_mode(mode)
    shell = sample_window.ui.shell

    for key in PAGE_KEYS:
        shell.set_current(key)
        settle(sample_window.task_runner)
        assert shell.page(key).isVisible()

    assert shell.current() == "preview"
    assert sample_window.ui.tableView_preview.model().rowCount() > 0
    assert sample_window.ui.label_run_confirmation.kind() == "success"


def test_the_sample_report_exports(sample_window, settle, tmp_path):
    sample_window.output_folder_name = str(tmp_path)
    sample_window.ui.lineEdit_file_name.setText("DEMO01 sample")

    sample_window.click_run()
    settle(sample_window.task_runner)

    assert [path.suffix for path in tmp_path.iterdir()] == [".xlsx"]
    assert sample_window.ui.label_run_confirmation.kind() == "success"


def test_duplicate_join_orders_draw_in_the_danger_color(sample_window):
    sample_window.report.update_join_items("VS", ["Subject"], 2, JoinHow.LEFT)
    sample_window.update_all_ui()  # AE and VS now share join order 2.
    sample_window.ui.shell.set_current("joins")
    QApplication.processEvents()
    table = sample_window.ui.tableWidget_join
    rows = {table.item(row, 0).text(): row for row in range(table.rowCount())}

    def order_color(form):
        combo = table.cellWidget(rows[form], 4)
        combo.ensurePolished()
        return combo.palette().color(QPalette.ColorRole.ButtonText).name().upper()

    danger = current().colors.danger_text.hex_rgb
    assert order_color("AE") == danger and order_color("VS") == danger
    assert order_color("DM") != danger
