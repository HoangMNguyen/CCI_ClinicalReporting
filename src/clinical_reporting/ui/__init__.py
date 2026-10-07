"""PySide6 desktop front end of the Clinical Reporting tool.

:mod:`ui.window` is the window: a ``QMainWindow`` that inherits every
behavior mixin. The window-level mixins are :mod:`ui.base` (shared state,
the refresh coordinators, small shared helpers) and :mod:`ui.navigation`
(page changes, badges, header, status bar, toasts). :mod:`ui.pages` has one
module per step or group of steps, holding the pages' widgets and the
behavior mixins that drive them; :mod:`ui.main_ui` builds the pages into the
shell, a sidebar of steps with a header and a status bar. The pieces more
than one page uses are :mod:`ui.dialogs`, :mod:`ui.table_actions` and
:mod:`ui.preview_model`.
:mod:`ui.app` is the entry point, and :mod:`ui.preview` shows the pages on
sample data (:mod:`ui.sample_data`).
"""
