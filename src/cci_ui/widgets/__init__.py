"""Reusable components that give every CCI tool the same look and behavior.

Import components from their modules, for example
``from cci_ui.widgets.section import Section``.

Each component module registers its stylesheet rules when imported, and
:func:`cci_ui.app.create_app` imports this package before applying the
theme, so every component is styled from the start. Add new component
modules to the import list below.

Show or hide a child widget only once it has a parent: after it is added
to a layout installed on a widget (``QVBoxLayout(widget)``), directly or
through nested layouts. A layout not yet installed doesn't give its widgets
a parent. Before that, only ever ``hide()`` it, and ``hide()`` a widget
before taking it out of its parent: ``setVisible(True)`` (or a show Qt has
already queued) on a parentless widget opens it as its own window, which
on Windows flashes on screen and costs about 50 ms (19 of these made
Clinical Reporting flicker at start-up). ``tests/ui/test_no_stray_windows.py``
builds the gallery and checks this, so add new components to the gallery.
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
