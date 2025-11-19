"""UI composition package for the Clinical Reporting tool.

This package breaks the monolithic widget implementation into focused
modules.  Each module provides a mixin that encapsulates the logic for a
particular area of the user interface (settings, forms, filters, etc.).
The :mod:`ui.main_widget` module composes these mixins to build the final
:class:`~PySide6.QtWidgets.QWidget` used by the application.
"""
