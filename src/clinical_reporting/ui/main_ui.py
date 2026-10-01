"""The Clinical Reporting window's widgets, built in code.

:class:`ClinicalReportingUi` builds the pages (:mod:`ui.pages`) in step
order, puts them in an :class:`~cci_ui.widgets.shell.AppShell` (sidebar,
header, status bar), and exposes each page's ``EXPORTS`` as its own
attributes. The behavior mixins reach widgets through it as
``self.ui.<name>``.

To add or reorder a step, change :data:`PAGE_CLASSES` (and
:data:`clinical_reporting.steps.STEP_KEYS`, which the pages' keys come from).
"""

from __future__ import annotations

from functools import partial
from typing import List, Optional

from PySide6.QtWidgets import QMainWindow

from cci_ui.theme.manager import ThemeManager
from cci_ui.widgets.page import Page
from cci_ui.widgets.shell import AppShell

from .pages.additional_input import AdditionalInputPage
from .pages.order_rename import OrderRenamePage
from .pages.preview_export import PreviewExportPage
from .pages.rules import ComparisonsPage, FiltersPage, JoinsPage
from .pages.selection import CommonItemsPage, FormItemsPage, FormsPage
from .pages.source_data import SourceDataPage

#: The tool's name, as the sidebar and the window title show it.
APP_NAME = "Clinical Reporting"
#: The steps, in order.
PAGE_CLASSES = (
    SourceDataPage,
    AdditionalInputPage,
    FormsPage,
    CommonItemsPage,
    FormItemsPage,
    FiltersPage,
    JoinsPage,
    ComparisonsPage,
    OrderRenamePage,
    PreviewExportPage,
)
#: Names the mixins use that belong to the window rather than a page.
WINDOW_NAMES = frozenset({"shell"})


class ClinicalReportingUi:
    """Builds the pages into *host* and holds the widgets the mixins use."""

    def setup(self, host: QMainWindow, theme: Optional[ThemeManager] = None) -> None:
        """Build the window's contents; *theme* adds the header's Display button."""
        #: The pages in step order.
        self.pages: List[Page] = [page_class() for page_class in PAGE_CLASSES]
        self.shell = AppShell(theme, title=APP_NAME)
        for page in self.pages:
            self.shell.add_page(
                page.KEY,
                page,
                title=page.title(),
                icon_name=page.ICON,
                section=page.SECTION,
            )
            for name in page.EXPORTS:
                setattr(self, name, getattr(page, name))
        for page, next_page in zip(self.pages, self.pages[1:]):
            page.set_next(
                next_page.title(), partial(self.shell.set_current, next_page.KEY)
            )
        host.setCentralWidget(self.shell)


__all__ = ["APP_NAME", "PAGE_CLASSES", "WINDOW_NAMES", "ClinicalReportingUi"]
