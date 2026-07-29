"""Feature-oriented PySide6 interface for the Clinical Reporting tool.

Each module owns one functional area: shared helpers (:mod:`ui.base`),
one module per tab (:mod:`ui.settings_tab`, :mod:`ui.additional_input_tab`,
:mod:`ui.selection_tabs`, :mod:`ui.filters_tab`, :mod:`ui.join_config`,
:mod:`ui.ordering_tab`, :mod:`ui.run_save_tab`), and cross-cutting pieces
(:mod:`ui.dialogs`, :mod:`ui.table_actions`, :mod:`ui.preview_model`,
:mod:`ui.navigation`).  :mod:`ui.window` composes them into the main
widget and :mod:`ui.app` hosts the entry point.  Generated Qt bindings
live separately under :mod:`ui._generated`.
"""
