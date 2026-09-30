"""The Clinical Reporting window's pages, one module per step.

Each page is a :class:`cci_ui.widgets.page.Page` built in code. The widgets
the behavior mixins use are page attributes named in the page's
``EXPORTS``; :class:`clinical_reporting.ui.main_ui.ClinicalReportingUi`
copies them onto ``window.ui`` (:mod:`clinical_reporting.ui.contract` is
the set of all of them). To give a mixin a new widget, add it to its page
and to that page's ``EXPORTS``.

Each page class also names its step: ``KEY`` (used by the preview tool and
the sidebar), ``SECTION`` (the sidebar group), and ``ICON``.
"""
