"""Feature-oriented PySide6 interface for the Clinical Reporting tool.

Behavior lives in one mixin per area: shared helpers (:mod:`ui.base`), one
module per step (:mod:`ui.settings_tab`, :mod:`ui.additional_input_tab`,
:mod:`ui.selection_tabs`, :mod:`ui.filters_tab`, :mod:`ui.join_config`,
:mod:`ui.ordering_tab`, :mod:`ui.run_save_tab`), and cross-cutting pieces
(:mod:`ui.dialogs`, :mod:`ui.table_actions`, :mod:`ui.preview_model`,
:mod:`ui.navigation`). The widgets are built in code: one module per page
in :mod:`ui.pages`, assembled by :mod:`ui.main_ui`, with the names the
mixins use listed in :mod:`ui.contract`. :mod:`ui.window` composes the
behaviors onto the window, :mod:`ui.app` is the entry point, and
:mod:`ui.preview` shows the pages on sample data (:mod:`ui.sample_data`).
"""
