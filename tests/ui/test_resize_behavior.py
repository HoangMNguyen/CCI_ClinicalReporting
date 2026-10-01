"""The Clinical Reporting window keeps controls at their natural size.

The old window scaled every widget with the window (a maximized window had
265×83 px buttons). Now layouts give extra space to lists and tables only.
At each target size and density, on every page: no button or input is
stretched or squashed from the height it wants, text buttons are wide
enough for their text and not stretched (except the panel's full-width
ones), the Source data page stays a centered column, the sidebar is an
icon strip on narrow windows, and the Preview panel sits beside the grid
when there is room and below it (with most of the height left to the
grid) when there isn't.
"""

import pytest
import shiboken6
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDateEdit,
    QLineEdit,
    QPushButton,
    QWidget,
)

from cci_ui.theme.manager import current
from cci_ui.theme.tokens import LAYOUT, Density
from clinical_reporting.ui.preview import build_preview_window

#: 1080p at 100%, a laptop at 150% and 125%, maximized 1080p, 1440p.
SIZES = [(960, 600), (1280, 641), (1536, 785), (1920, 1001), (2560, 1377)]
CONTROLS = (QAbstractButton, QLineEdit, QComboBox, QDateEdit)
#: Controls inside these (a date field's text box, a table's corner button)
#: belong to them, which size them.
OWNERS = (QAbstractSpinBox, QComboBox, QAbstractItemView)


@pytest.fixture
def window(make_manager, settle):
    theme = make_manager()
    theme.apply()
    built = build_preview_window(theme=theme)
    built.show()
    yield built, theme
    built.close()
    settle(built.task_runner)
    shiboken6.delete(built)


def _stretched_controls(page, wide_by_design=()):
    problems = []
    for control in page.findChildren(QWidget):
        if not isinstance(control, CONTROLS) or not control.isVisible():
            continue
        if isinstance(control.parentWidget(), OWNERS):
            continue
        hint = control.sizeHint()
        name = control.accessibleName() or getattr(control, "text", lambda: "")()
        height, width = control.height(), control.width()
        if not hint.height() - 1 <= height <= hint.height() * 1.2 + 1:
            problems.append(f"{name!r} is {height}px tall (wants {hint.height()})")
        if isinstance(control, QPushButton):
            if width < hint.width() - 1:
                problems.append(f"{name!r} is {width}px wide (needs {hint.width()})")
            elif width > hint.width() * 1.5 and control not in wide_by_design:
                problems.append(f"{name!r} is {width}px wide (wants {hint.width()})")
    return problems


@pytest.mark.parametrize("density", list(Density), ids=lambda d: d.value)
@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_controls_keep_their_natural_size(window, settle, size, density):
    built, theme = window
    theme.set_density(density)
    built.resize(*size)
    shell = built.ui.shell
    wide = (built.ui.pushButton_run, built.ui.pushButton_save_setting)
    problems = []

    for page in built.ui.pages:
        shell.set_current(page.KEY)
        settle(built.task_runner)
        QApplication.processEvents()
        problems += [f"{page.title()}: {p}" for p in _stretched_controls(page, wide)]
    problems += [f"header: {p}" for p in _stretched_controls(shell.header)]

    assert problems == []


def test_source_data_stays_a_centered_column(window):
    built, _theme = window
    built.resize(2560, 1377)
    built.ui.shell.set_current("source")
    QApplication.processEvents()
    page = built.ui.shell.page("source")
    column = page._column
    margin = current().metrics.page_margin

    assert column.width() <= LAYOUT.form_max_w + 2 * margin
    left = column.mapTo(page, column.rect().topLeft()).x()
    right = page.width() - left - column.width()
    assert abs(left - right) <= 20  # Centered (a scroll bar may take a little).


@pytest.mark.parametrize(
    ("width", "collapsed"), [(960, True), (1080, True), (1120, False), (1920, False)]
)
def test_the_sidebar_is_an_icon_strip_on_narrow_windows(window, width, collapsed):
    built, _theme = window
    built.resize(width, 700)
    QApplication.processEvents()
    shell = built.ui.shell

    assert shell.is_sidebar_collapsed() is collapsed
    expected = LAYOUT.sidebar_collapsed_w if collapsed else shell.sidebar_width()
    assert shell.sidebar.width() == expected


@pytest.mark.parametrize(
    ("width", "stacked"), [(960, True), (1120, True), (1280, False), (1920, False)]
)
def test_the_export_panel_moves_below_the_grid_when_narrow(window, width, stacked):
    built, _theme = window
    built.resize(width, 700)
    built.ui.shell.set_current("preview")
    QApplication.processEvents()

    # Content width, not window width: at 1120 the full sidebar leaves too little.
    assert built.ui.shell.page("preview").split.is_stacked() is stacked


@pytest.mark.parametrize("density", list(Density), ids=lambda d: d.value)
def test_below_the_grid_the_panel_leaves_the_grid_most_of_the_height(
    window, settle, density
):
    built, theme = window
    theme.set_density(density)
    built.resize(960, 600)  # The smallest window.
    built.ui.shell.set_current("preview")
    settle(built.task_runner)
    QApplication.processEvents()
    split = built.ui.shell.page("preview").split

    assert split.is_stacked()
    assert split.side.height() <= 0.4 * split.height() + 1  # It scrolls instead.
    assert split.main.height() >= 200  # Still room for a screenful of rows.
