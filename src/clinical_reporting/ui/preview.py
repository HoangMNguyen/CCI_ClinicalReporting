"""Open the Clinical Reporting window on made-up data, or screenshot its pages.

    python -m clinical_reporting.ui.preview                    # open it
    python -m clinical_reporting.ui.preview joins --theme dark --size 1920x1001
    python -m clinical_reporting.ui.preview --screenshot shots --size 1000x620,1920x1001

The window holds DEMO01 sample data (:mod:`clinical_reporting.ui.sample_data`),
never a real study, and nothing here changes the appearance saved for the
real tool. The sample isn't a real ZIP, so turning the cut-off date on shows
a read error. ``--screenshot`` runs off screen and writes
``<page>-<scheme>-<density>-<width>x<height>.png`` for each page given (all
pages by default), in light and dark unless ``--theme`` picks one.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QSettings, QTemporaryDir

from cci_ui.theme.manager import ThemeManager, ThemeMode
from cci_ui.theme.tokens import LAYOUT, Density
from clinical_reporting.ui.main_ui import PAGE_CLASSES

#: Page names on the command line, in step order.
PAGE_KEYS = tuple(page.KEY for page in PAGE_CLASSES)


def _sizes(text: str) -> List[Tuple[int, int]]:
    sizes = []
    for part in text.split(","):
        width, _, height = part.strip().lower().partition("x")
        try:
            sizes.append((int(width), int(height)))
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"expected WIDTHxHEIGHT[,WIDTHxHEIGHT…], got {text!r}"
            ) from None
    return sizes


def _parse(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m clinical_reporting.ui.preview",
        description=__doc__.split("\n")[0],
    )
    parser.add_argument(
        "pages",
        nargs="*",
        choices=[*PAGE_KEYS, "all"],
        metavar="PAGE",
        help=f"page to open on, or pages to screenshot: {', '.join(PAGE_KEYS)}, all",
    )
    parser.add_argument(
        "--theme", choices=[m.value for m in ThemeMode], help="appearance"
    )
    parser.add_argument("--density", choices=[d.value for d in Density], help="density")
    parser.add_argument(
        "--size",
        type=_sizes,
        default=[LAYOUT.first_launch],
        help="window size(s), e.g. 1000x620 or 1000x620,1920x1001",
    )
    parser.add_argument(
        "--empty", action="store_true", help="start without data (empty states)"
    )
    parser.add_argument(
        "--screenshot", metavar="DIR", type=Path, help="save the pages as PNG and quit"
    )
    return parser.parse_args(argv)


def build_preview_window(
    *, with_data: bool = True, theme: Optional[ThemeManager] = None
):
    """The real window, holding the configured DEMO01 sample report.

    *theme* (the app's ThemeManager) adds the header's Display button.
    """
    from clinical_reporting.ui.sample_data import (
        STUDY,
        configure_sample_report,
        sample_forms,
    )
    from clinical_reporting.ui.window import Widget

    window = Widget(theme=theme)
    if with_data:
        window.open_input_data(
            f"Core_Listings_{STUDY}_sample.zip", None, sample_forms()
        )
        configure_sample_report(window.report)
        window.update_all_ui()
    return window


def _settle(window, app) -> None:
    """Let work started by a page change (the preview) finish and show."""
    while window.task_runner.busy:
        window.task_runner.wait()
        app.processEvents()
    # Text set by the last callback lays out over a few more event rounds;
    # sending posted events first flushes pending layout requests.
    for _ in range(3):
        app.sendPostedEvents()
        app.processEvents()


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse(argv)
    if args.screenshot is not None:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"  # Never show a window.

    from cci_ui.app import create_app

    # Throwaway settings: nothing the preview does changes the tool's choices.
    scratch = QTemporaryDir()
    settings = QSettings(scratch.filePath("preview.ini"), QSettings.Format.IniFormat)
    app, theme = create_app(
        app_id="clinical-reporting-preview",
        name="Clinical Reporting preview",
        settings=settings,
        persist=False,
    )
    if args.theme:
        theme.set_mode(ThemeMode(args.theme))
    if args.density:
        theme.set_density(Density(args.density))

    keys = list(PAGE_KEYS) if "all" in args.pages else args.pages
    window = build_preview_window(with_data=not args.empty, theme=theme)
    shell = window.ui.shell
    window.resize(*args.size[0])
    if keys:
        shell.set_current(keys[0])

    if args.screenshot is None:
        window.show()
        return app.exec()

    args.screenshot.mkdir(parents=True, exist_ok=True)
    modes = [ThemeMode(args.theme)] if args.theme else [ThemeMode.LIGHT, ThemeMode.DARK]
    window.show()
    saved = 0
    for mode in modes:
        theme.set_mode(mode)
        for width, height in args.size:
            window.resize(width, height)
            for key in keys or PAGE_KEYS:
                shell.set_current(key)
                _settle(window, app)
                name = (
                    f"{key}-{theme.scheme.value}-{theme.density.value}"
                    f"-{width}x{height}.png"
                )
                window.grab().save(str(args.screenshot / name))
                saved += 1
    window.close()
    print(f"Saved {saved} screenshots to {args.screenshot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
