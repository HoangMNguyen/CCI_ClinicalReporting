"""The Clinical Reporting window's pages, one module per step.

Each module holds a step's page class (or a few related ones: Filters and
Comparisons in ``filters``; Forms, Common items and Form items in
``selection``), built in code on :class:`cci_ui.widgets.page.Page`, their
``EXPORTS``, and the behavior mixin(s) that drive them. The widgets a mixin
uses are page attributes named in the page's ``EXPORTS``;
:class:`clinical_reporting.ui.main_ui.ClinicalReportingUi` copies them onto
``window.ui``. To give a mixin a new widget, add it to its page and to that
page's ``EXPORTS``, in the same module.

Each page class also names its step: ``KEY`` (one of
:data:`clinical_reporting.steps.STEP_KEYS`, which keys the sidebar and its
badges and the preview tool's page names), ``SECTION`` (the sidebar group),
and ``ICON``.
"""
