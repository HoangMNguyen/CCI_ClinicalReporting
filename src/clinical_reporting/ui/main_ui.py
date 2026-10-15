"""The Clinical Reporting window's widgets, built in code.

:class:`ClinicalReportingUi` builds the pages (:mod:`ui.pages`) in step
order, puts them in an :class:`~cci_ui.widgets.shell.AppShell` (sidebar,
header, status bar), and exposes each page's ``EXPORTS`` as its own
attributes. The behavior mixins reach widgets through it as
``self.ui.<name>``. The pages of :data:`clinical_reporting.steps.NEEDS_DATA`
get a "No data loaded" state, whose button chooses a Corelisting ZIP.

To add or reorder a step, change :data:`PAGE_CLASSES` (and
:data:`clinical_reporting.steps.STEP_KEYS`, which the pages' keys come from).
"""

from __future__ import annotations

from functools import partial
from typing import List, Optional

from PySide6.QtWidgets import QMainWindow

from cci_ui.icons import IconName
from cci_ui.theme.manager import ThemeManager
from cci_ui.widgets.page import Page
from cci_ui.widgets.shell import AppShell
from cci_ui.widgets.views import EmptyState
from clinical_reporting import help_text, steps

from .pages.additional_input import AdditionalInputPage
from .pages.coalesced_items import CoalescedItemsPage
from .pages.filters import ComparisonsPage, FiltersPage
from .pages.joins import JoinsPage
from .pages.order_rename import OrderRenamePage
from .pages.preview_export import PreviewExportPage
from .pages.selection import CommonItemsPage, FormItemsPage, FormsPage
from .pages.source_data import SourceDataPage
from .pages.stacked_forms import StackedFormsPage

#: The tool's name, as the sidebar and the window title show it.
APP_NAME = "Clinical Reporting"
#: The steps, in order.
PAGE_CLASSES = (
    SourceDataPage,
    AdditionalInputPage,
    StackedFormsPage,
    CoalescedItemsPage,
    FormsPage,
    CommonItemsPage,
    FormItemsPage,
    FiltersPage,
    JoinsPage,
    ComparisonsPage,
    OrderRenamePage,
    PreviewExportPage,
)

# Legacy names are kept for the mixins: ``label_setting``,
# ``label_run_confirmation`` and ``label_save_confirmation`` are status
# banners (``cci_ui.widgets.status.StatusBanner``), like ``banner_input_file``.
#: Names the mixins use that belong to the window rather than a page.
WINDOW_NAMES = frozenset({"shell"})


class ClinicalReportingUi:
    """Builds the pages into *host* and holds the widgets the mixins use."""

    def setup(self, host: QMainWindow, theme: Optional[ThemeManager] = None) -> None:
        """Build the window's contents; *theme* adds the header's Display button."""
        #: The pages in step order.
        self.pages: List[Page] = [page_class() for page_class in PAGE_CLASSES]
        # The collapsed sidebar shows each step's badge; Compact starts collapsed.
        # The "?" button shows the open step's help beside it.
        self.shell = AppShell(
            theme,
            title=APP_NAME,
            strip_badges=True,
            collapse_in_compact=True,
            help_text=help_text.help_markdown,
        )
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
        for page in self.pages:
            if page.KEY in steps.NEEDS_DATA:
                page.set_empty_state(self._no_data_state())
        host.setCentralWidget(self.shell)

    def _no_data_state(self) -> EmptyState:
        return EmptyState(
            IconName.ZIP_FILE,
            steps.NO_DATA,
            steps.NO_DATA_HINT,
            action_text="Choose ZIP…",
            # The Source data page's button, so its handler does the rest.
            on_action=self.pushButton_input_file.click,
        )


__all__ = ["APP_NAME", "PAGE_CLASSES", "WINDOW_NAMES", "ClinicalReportingUi"]
