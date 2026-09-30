"""The Clinical Reporting window's widgets, built in code.

:class:`ClinicalReportingUi` builds the pages (:mod:`ui.pages`) in step
order, puts them in a tab widget, and exposes each page's ``EXPORTS`` as its
own attributes. The behavior mixins reach widgets through it as
``self.ui.<name>``.

To add or reorder a step, change :data:`PAGE_CLASSES`.
"""

from __future__ import annotations

from functools import partial
from typing import List

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from cci_ui.widgets.labels import escape_ampersands
from cci_ui.widgets.page import Page

from .pages.additional_input import AdditionalInputPage
from .pages.order_rename import OrderRenamePage
from .pages.preview_export import PreviewExportPage
from .pages.rules import ComparisonsPage, FiltersPage, JoinsPage
from .pages.selection import CommonItemsPage, FormItemsPage, FormsPage
from .pages.source_data import SourceDataPage

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
WINDOW_NAMES = frozenset({"tabWidget", "page_preview"})


class ClinicalReportingUi:
    """Builds the pages into *host* and holds the widgets the mixins use."""

    def setup(self, host: QWidget) -> None:
        #: The pages in step order.
        self.pages: List[Page] = [page_class() for page_class in PAGE_CLASSES]
        by_class = {type(page): page for page in self.pages}
        self.page_source = by_class[SourceDataPage]
        self.page_preview = by_class[PreviewExportPage]

        self.tabWidget = QTabWidget()
        self.tabWidget.setDocumentMode(True)
        for page in self.pages:
            self.tabWidget.addTab(page, escape_ampersands(page.title()))
            for name in page.EXPORTS:
                setattr(self, name, getattr(page, name))
        for page, next_page in zip(self.pages, self.pages[1:]):
            page.set_next(
                next_page.title(), partial(self.tabWidget.setCurrentWidget, next_page)
            )

        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabWidget)


__all__ = ["PAGE_CLASSES", "WINDOW_NAMES", "ClinicalReportingUi"]
