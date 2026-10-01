"""A window showing every design-system component, for checking the look.

Run it with::

    python -m cci_ui.gallery                      # interactive
    python -m cci_ui.gallery --theme dark --density compact --size 1000x620
    python -m cci_ui.gallery --screenshot shots   # every page, light and dark

The gallery never changes the appearance saved for the real tools. With
``--screenshot`` it runs off screen and writes ``<page>-<scheme>-<density>.png``
files, then quits; that is how to review a change to the tokens or a
component without clicking through the apps.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import fields
from pathlib import Path
from typing import Callable, List, NamedTuple, Optional, Sequence, Tuple

from PySide6.QtCore import QDate, QSettings, QTemporaryDir, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QTableWidgetItem,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.theme.manager import (
    ThemeManager,
    ThemeMode,
    current,
    set_invalid,
    theme_events,
)
from cci_ui.theme.palette import qcolor
from cci_ui.theme.tokens import TYPE_SCALE, Color, ColorTokens, Density
from cci_ui.widgets.buttons import VARIANTS, icon_button, make_button
from cci_ui.widgets.dual_list import DualListPicker
from cci_ui.widgets.labels import IconLabel, text_label
from cci_ui.widgets.page import Page, PageKind
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.search import SearchField
from cci_ui.widgets.section import Section
from cci_ui.widgets.segmented import Segment, SegmentedControl
from cci_ui.widgets.shell import AppShell
from cci_ui.widgets.sidebar import StepState
from cci_ui.widgets.status import StatusBanner, show_error, show_toast
from cci_ui.widgets.tables import (
    ColumnSpec,
    TableToolbar,
    configure_columns,
    style_table,
    table_card,
)
from cci_ui.widgets.toggle import ToggleSwitch
from cci_ui.widgets.views import EmptyState, PlaceholderTableWidget

SAMPLE_PATH = r"C:\Users\analyst\Downloads\Core_Listings_DEMO01_2026-09-29.zip"


# ----------------------------------------------------------------------
# Colors


def _luminance(color: Color) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * channel(color.r)
        + 0.7152 * channel(color.g)
        + 0.0722 * channel(color.b)
    )


def contrast_ratio(foreground: Color, background: Color) -> float:
    """WCAG contrast ratio of two opaque colors (4.5 is the AA minimum for text)."""
    lighter, darker = sorted(
        (_luminance(foreground), _luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


class _Swatch(QWidget):
    """A square of one color token, repainted in the current scheme."""

    def __init__(self, token: str):
        super().__init__()
        self._token = token
        self.setFixedSize(28, 28)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(qcolor(current().colors.border_card))
        painter.setBrush(qcolor(getattr(current().colors, self._token)))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)
        painter.end()


class _ColorTable(QWidget):
    """Every color token with its value (and contrast for text colors)."""

    def __init__(self) -> None:
        super().__init__()
        grid = QGridLayout(self)
        grid.setHorizontalSpacing(14)
        self._values: List[Tuple[str, QLabel]] = []
        for row, field in enumerate(fields(ColorTokens)):
            grid.addWidget(_Swatch(field.name), row, 0)
            grid.addWidget(text_label(field.name, style="headline"), row, 1)
            value = text_label("", tone="secondary")
            grid.addWidget(value, row, 2)
            self._values.append((field.name, value))
        # A bound method, so Qt drops the connection when the table is deleted.
        theme_events().changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        colors = current().colors
        for name, label in self._values:
            color = getattr(colors, name)
            text = color.css
            if name.startswith("text_") or name in ("link", "accent", "on_accent"):
                background = colors.accent if name == "on_accent" else colors.bg_surface
                text += f"   contrast {contrast_ratio(color, background):.1f}"
            label.setText(text)


def _colors_page(_shell: AppShell) -> Page:
    page = Page(
        "Colors",
        "Every color token in the current scheme. Text colors show their "
        "contrast against a card (4.5 or more reads well).",
        kind=PageKind.FORM,
    )
    page.body.addWidget(_ColorTable())
    return page


# ----------------------------------------------------------------------
# Type, buttons, inputs, toggles


def _type_page(_shell: AppShell) -> Page:
    page = Page(
        "Typography", "The type scale; body text is 13 px Inter.", kind=PageKind.FORM
    )
    for name, style in TYPE_SCALE.items():
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        spec = text_label(f"{name} · {style.size}/{style.weight}", style="caption")
        spec.setFixedWidth(150)
        layout.addWidget(spec)
        layout.addWidget(text_label("Clinical Reporting DEMO01", style=name), 1)
        page.body.addWidget(row)
    return page


def _row(*widgets: QWidget) -> QWidget:
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch(1)
    return holder


def _buttons_page(_shell: AppShell) -> Page:
    page = Page(
        "Buttons",
        "One primary action per view; the rest secondary.",
        kind=PageKind.FORM,
    )
    for variant in VARIANTS:
        enabled = make_button(
            variant.capitalize(), variant=variant, icon_name=IconName.SAVE
        )
        disabled = make_button("Disabled", variant=variant)
        disabled.setEnabled(False)
        page.body.addWidget(_row(enabled, disabled))
    icons = [
        icon_button(name, tip)
        for name, tip in (
            (IconName.MOVE_TOP, "Move to top"),
            (IconName.MOVE_UP, "Move up"),
            (IconName.MOVE_DOWN, "Move down"),
            (IconName.MOVE_BOTTOM, "Move to bottom"),
        )
    ]
    page.body.addWidget(_row(*icons))
    return page


def _inputs_page(_shell: AppShell) -> Page:
    page = Page("Inputs", "Text, choices, dates, and files.", kind=PageKind.FORM)
    section = Section("Fields", "Invalid combos turn red; disabled fields dim.")
    filled = QLineEdit("DEMO01_DSMB")
    placeholder = QLineEdit()
    placeholder.setPlaceholderText("Setting name")
    disabled = QLineEdit("Disabled")
    disabled.setEnabled(False)
    combo = QComboBox()
    combo.addItems(["Left join", "Inner join", "Outer join"])
    invalid = QComboBox()
    invalid.addItems(["2"])
    set_invalid(invalid, True)
    date = QDateEdit(QDate(2026, 6, 30))
    date.setCalendarPopup(True)
    date.setFixedWidth(150)
    section.add_row("File name", filled)
    section.add_row("Placeholder", placeholder)
    section.add_row("Disabled", disabled)
    section.add_row("Search", SearchField("Search columns"))
    section.add_row("Join type", combo)
    section.add_row("Invalid", invalid)
    section.add_row("Cut-off", date, end_aligned=True)
    page.body.addWidget(section)

    files = Section("Files")
    chosen = PathPicker(button_text="Choose ZIP…", removable=True)
    chosen.set_path(SAMPLE_PATH)
    files.add_row("Chosen", chosen)
    files.add_row("Empty", PathPicker(button_text="Choose ZIP…"))
    page.body.addWidget(files)
    return page


def _toggles_page(_shell: AppShell) -> Page:
    page = Page("Toggles & segmented", kind=PageKind.FORM)
    section = Section("Switches")
    on = ToggleSwitch()
    on.setChecked(True)
    off_disabled = ToggleSwitch()
    off_disabled.setEnabled(False)
    section.add_row("Apply cut-off date", on, label_width=None)
    section.add_row("Start from a saved setting", ToggleSwitch(), label_width=None)
    section.add_row("Disabled", off_disabled, label_width=None)
    page.body.addWidget(section)
    page.body.addWidget(
        _row(
            SegmentedControl(
                [
                    Segment("system", "System", IconName.APPEARANCE_SYSTEM),
                    Segment("light", "Light", IconName.APPEARANCE_LIGHT),
                    Segment("dark", "Dark", IconName.APPEARANCE_DARK),
                ]
            ),
            SegmentedControl([Segment("a", "Comfortable"), Segment("b", "Compact")]),
        )
    )
    return page


# ----------------------------------------------------------------------
# Sections, lists, tables


def _sections_page(_shell: AppShell) -> Page:
    page = Page(
        "Sections",
        "Titled cards of rows, as on the Source data step.",
        kind=PageKind.FORM,
    )
    zip_section = Section("Corelisting ZIP", "18 forms · 2,431 rows")
    picker = PathPicker(button_text="Choose ZIP…", removable=True)
    picker.set_path(SAMPLE_PATH)
    zip_section.add_row("File", picker)
    cut_off = Section("Cut-off date", "Only rows on or before this date are loaded.")
    switch = ToggleSwitch()
    switch.setChecked(True)
    cut_off.add_row("Apply cut-off date", switch, label_width=None)
    date = QDateEdit(QDate(2026, 6, 30))
    date.setCalendarPopup(True)
    date.setFixedWidth(150)
    cut_off.add_row("Cut-off", date, end_aligned=True)
    page.body.addWidget(zip_section)
    page.body.addWidget(cut_off)
    page.set_next("Two-list picker", lambda: None)
    return page


def _lists_page(_shell: AppShell) -> Page:
    page = Page("Two-list picker", "The Forms, Common items, and Form items steps.")
    picker = DualListPicker(
        available_title="Available forms",
        selected_title="Selected forms",
        search_placeholder="Search forms",
    )
    picker.available.addItems(
        [
            "AE  Adverse Events",
            "CM  Concomitant Medications",
            "EX  Exposure",
            "MH  Medical History",
        ]
    )
    picker.selected.addItems(["DM  Demographics", "VS  Vital Signs", "LB  Laboratory"])
    page.body.addWidget(picker, 1)
    return page


def _tables_page(_shell: AppShell) -> Page:
    page = Page("Tables", "Column rules, row lines, combos in cells, and +/− buttons.")
    table = PlaceholderTableWidget("Select forms first.")
    table.setColumnCount(5)
    table.setHorizontalHeaderLabels(["Form", "Item 1", "Item 2", "Order", "Type"])
    rows = [
        ("DM", "Subject", "—", "1"),
        ("AE", "Subject", "—", "2"),
        ("VS", "Subject", "InstanceName", "2"),
    ]
    table.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(value))
        how = QComboBox()
        how.addItems(["Left join", "Inner join"])
        table.setCellWidget(row, 4, how)
    style_table(table)
    configure_columns(
        table,
        [
            ColumnSpec("contents"),
            ColumnSpec(),
            ColumnSpec(),
            ColumnSpec("fixed", 84),
            ColumnSpec("fixed", 140),
        ],
    )
    page.body.addWidget(table_card(table), 1)
    page.body.addWidget(
        TableToolbar(add_tooltip="Add join", caption="Forms are joined in Order.")
    )
    empty = PlaceholderTableWidget("No filters. Press + to add one.")
    empty.setColumnCount(3)
    empty.setHorizontalHeaderLabels(["Item", "Operator", "Value"])
    style_table(empty)
    configure_columns(empty, [ColumnSpec(), ColumnSpec("fixed", 120), ColumnSpec()])
    card = table_card(empty)
    card.setFixedHeight(140)
    page.body.addWidget(card)
    return page


# ----------------------------------------------------------------------
# Feedback and the rest


def _status_page(shell: AppShell) -> Page:
    page = Page(
        "Status & feedback", "Banners on the page; toasts, busy, and errors on demand."
    )
    for kind, text in (
        ("info", "Generating preview..."),
        (
            "success",
            "Report saved to C:\\Users\\analyst\\Reports\\DEMO01_DSMB 260930_101500.xlsx",
        ),
        ("warning", '2 items in "DSMB monthly" aren\'t in this data and were skipped.'),
        ("error", "Couldn't read Core_Listings_DEMO01.zip. The file may be damaged."),
    ):
        banner = StatusBanner()
        details = (
            "Traceback (most recent call last):\n  ...\nBadZipFile"
            if kind == "error"
            else None
        )
        banner.show_message(text, kind, details)
        if kind == "warning":
            banner.set_action("Go to Source data", lambda: None)
        page.body.addWidget(banner)

    toast = make_button("Show a toast")
    toast.clicked.connect(lambda: show_toast(shell, "Settings saved"))
    status = make_button("Status bar message")
    status.clicked.connect(
        lambda: shell.status_bar.show_message("Settings saved", "success")
    )
    busy = make_button("Busy for 2 seconds")

    def run_busy() -> None:
        shell.busy.start("Reading Corelisting ZIP…")
        QTimer.singleShot(2000, shell.busy.stop)

    busy.clicked.connect(run_busy)
    error = make_button("Show an error", variant="destructive")
    error.clicked.connect(
        lambda: show_error(
            shell, "Export failed", "Couldn't write the file.", "Traceback …"
        )
    )
    page.body.addWidget(_row(toast, status, busy, error))
    page.body.addStretch(1)
    return page


def _empty_page(_shell: AppShell) -> Page:
    page = Page("Empty state", "What a step shows before data is loaded.")
    page.body.addWidget(
        EmptyState(
            IconName.ZIP_FILE,
            "No data loaded",
            "Choose a Corelisting ZIP on Source data to start a report.",
            action_text="Choose ZIP…",
        ),
        1,
    )
    return page


def _icons_page(_shell: AppShell) -> Page:
    page = Page(
        "Icons",
        "Every bundled icon (Lucide), in the secondary color.",
        kind=PageKind.FORM,
    )
    holder = QWidget()
    grid = QGridLayout(holder)
    grid.setHorizontalSpacing(18)
    grid.setVerticalSpacing(10)
    for index, name in enumerate(IconName.all()):
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(IconLabel(name, "secondary", 20))
        layout.addWidget(text_label(name, style="caption"), 1)
        grid.addWidget(cell, index // 3, index % 3)
    page.body.addWidget(holder)
    return page


class GalleryPage(NamedTuple):
    """One gallery page: its key, sidebar section and title, icon, and builder."""

    key: str
    section: str
    title: str
    icon_name: str
    build: Callable[[AppShell], Page]


PAGES: Sequence[GalleryPage] = (
    GalleryPage("colors", "Foundations", "Colors", IconName.DISPLAY, _colors_page),
    GalleryPage("type", "Foundations", "Typography", IconName.INFO, _type_page),
    GalleryPage("icons", "Foundations", "Icons", IconName.SUCCESS, _icons_page),
    GalleryPage("buttons", "Controls", "Buttons", IconName.RUN, _buttons_page),
    GalleryPage("inputs", "Controls", "Inputs", IconName.SEARCH, _inputs_page),
    GalleryPage(
        "toggles",
        "Controls",
        "Toggles & segmented",
        IconName.APPEARANCE_SYSTEM,
        _toggles_page,
    ),
    GalleryPage("sections", "Layout", "Sections", IconName.FORMS, _sections_page),
    GalleryPage(
        "lists", "Layout", "Two-list picker", IconName.COMMON_ITEMS, _lists_page
    ),
    GalleryPage("tables", "Layout", "Tables", IconName.PREVIEW_EXPORT, _tables_page),
    GalleryPage(
        "status", "Feedback", "Status & feedback", IconName.WARNING, _status_page
    ),
    GalleryPage("empty", "Feedback", "Empty state", IconName.ZIP_FILE, _empty_page),
)


def build_gallery(theme: ThemeManager) -> Tuple[QMainWindow, AppShell]:
    """The gallery window with one page per component group."""
    window = QMainWindow()
    window.setWindowTitle("CCI design system")
    shell = AppShell(theme, title="Design system")
    shell.set_context("Gallery")
    shell.status_bar.set_summary(
        f"{len(PAGES)} pages · {len(IconName.all())} icons · {len(VARIANTS)} buttons"
    )
    window.setCentralWidget(shell)
    for page in PAGES:
        shell.add_page(
            page.key,
            page.build(shell),
            title=page.title,
            icon_name=page.icon_name,
            section=page.section,
        )
    # Show every kind of sidebar badge.
    shell.sidebar.set_status("colors", StepState.DONE)
    shell.sidebar.set_status("icons", count=len(IconName.all()))
    shell.sidebar.set_status("buttons", count=len(VARIANTS))
    shell.sidebar.set_status("status", StepState.WARNING, tip="example warning")
    shell.sidebar.set_status("tables", StepState.ERROR, tip="example error")
    shell.sidebar.set_status("empty", StepState.OPTIONAL)
    return window, shell


# ----------------------------------------------------------------------
# Command line


def _size(text: str) -> Tuple[int, int]:
    width, _, height = text.lower().partition("x")
    try:
        return int(width), int(height)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected WIDTHxHEIGHT, got {text!r}"
        ) from None


def _parse(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m cci_ui.gallery", description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "--theme", choices=[m.value for m in ThemeMode], help="appearance"
    )
    parser.add_argument("--density", choices=[d.value for d in Density], help="density")
    parser.add_argument(
        "--size", type=_size, default=(1280, 800), help="window size, e.g. 1000x620"
    )
    parser.add_argument(
        "--page",
        choices=[page.key for page in PAGES],
        help="page to open on (with --screenshot: the only page saved)",
    )
    parser.add_argument(
        "--screenshot", metavar="DIR", type=Path, help="save every page as PNG and quit"
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse(argv)
    if args.screenshot is not None:
        # Never show a window while taking screenshots.
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from cci_ui.app import create_app

    # Throwaway settings: nothing the gallery does changes the tools' choices.
    scratch = QTemporaryDir()
    settings = QSettings(scratch.filePath("gallery.ini"), QSettings.Format.IniFormat)
    app, theme = create_app(
        app_id="gallery", name="CCI design system", settings=settings, persist=False
    )
    if args.theme:
        theme.set_mode(ThemeMode(args.theme))
    if args.density:
        theme.set_density(Density(args.density))

    window, shell = build_gallery(theme)
    window.resize(*args.size)
    if args.page:
        shell.set_current(args.page)

    if args.screenshot is None:
        window.show()
        return app.exec()

    args.screenshot.mkdir(parents=True, exist_ok=True)
    modes = [ThemeMode(args.theme)] if args.theme else [ThemeMode.LIGHT, ThemeMode.DARK]
    window.show()
    keys = [args.page] if args.page else [page.key for page in PAGES]
    for mode in modes:
        theme.set_mode(mode)
        for key in keys:
            shell.set_current(key)
            app.processEvents()
            name = f"{key}-{theme.scheme.value}-{theme.density.value}.png"
            window.grab().save(str(args.screenshot / name))
    window.close()
    print(f"Saved {len(modes) * len(keys)} screenshots to {args.screenshot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
