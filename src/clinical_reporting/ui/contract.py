"""The widgets the Clinical Reporting behaviors use, by name.

The behavior mixins (``ui/*_tab.py``, ``join_config``, ``navigation``, ...)
reach widgets as ``self.ui.<name>``. :data:`UI_CONTRACT` is every name they
may use: the window's own (:data:`~ui.main_ui.WINDOW_NAMES`) and each page's
``EXPORTS``. ``tests/ui/test_ui_contract.py`` checks that the mixins use
only these names and use all of them.

Legacy names are kept for the mixins: ``label_setting``,
``label_run_confirmation``, and ``label_save_confirmation`` are status
banners (``cci_ui.widgets.status.StatusBanner``), like ``banner_input_file``.
"""

from __future__ import annotations

from .main_ui import PAGE_CLASSES, WINDOW_NAMES

UI_CONTRACT = WINDOW_NAMES.union(*(page.EXPORTS for page in PAGE_CLASSES))

__all__ = ["UI_CONTRACT"]
