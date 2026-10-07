"""The Clinical Reporting window's pages, one module per step.

Each page is a :class:`cci_ui.widgets.page.Page` built in code. The widgets
the behavior mixins use are page attributes named in the page's
``EXPORTS``; :class:`clinical_reporting.ui.main_ui.ClinicalReportingUi`
copies them onto ``window.ui``. To give a mixin a new widget, add it to its
page and to that page's ``EXPORTS``.

Each page class also names its step: ``KEY`` (one of
:data:`clinical_reporting.steps.STEP_KEYS`, which keys the sidebar and its
badges and the preview tool's page names), ``SECTION`` (the sidebar group),
and ``ICON``.
"""
