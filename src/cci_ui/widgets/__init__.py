"""Reusable components that give every CCI tool the same look and behavior.

Import components from their modules, for example
``from cci_ui.widgets.section import Section``.

Each component module registers its stylesheet rules when imported, and
:func:`cci_ui.app.create_app` imports this package before applying the
theme, so every component is styled from the start. Add new component
modules to the import list below.
"""

from cci_ui.widgets import (  # noqa: F401  (imported for their stylesheet rules)
    busy,
    buttons,
    display,
    dual_list,
    labels,
    page,
    path_picker,
    responsive,
    search,
    section,
    segmented,
    shell,
    sidebar,
    status,
    tables,
    toggle,
    views,
)
