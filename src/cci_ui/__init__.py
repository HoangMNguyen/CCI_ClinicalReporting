"""The CCI design system: theme, components, and app startup for all four tools.

Every tool starts with :func:`cci_ui.app.create_app`, which applies the
shared style, fonts, and theme. This package imports Qt, but never imports
the tools' own packages, so each tool can depend on it. Nothing is imported
here so that Qt-free submodules such as ``cci_ui.theme.tokens`` stay
importable without Qt.
"""
