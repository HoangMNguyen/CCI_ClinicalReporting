# Reporting window: one module per page, behavior mixins kept

Clinical Reporting's window code is grouped by page: each module in `ui/pages/` holds a page's widgets (named in its `EXPORTS`) and the behavior mixin that drives them, and the window inherits every mixin (`class Widget(QMainWindow, *BEHAVIORS)`). Before, each page lived in two files, a layout module and a behavior module, and the window copied its mixins' methods onto itself through a half-finished controller. The split carried no coupling: of 205 widget references in the behavior code, 8 cross a page boundary, so a one-widget change meant editing two files for nothing. Comparable PySide/PyQt projects (Anki, Orange, Spyder, calibre, napari) keep one screen per module. The regroup only moves code once the classes are renamed after their pages, so a fingerprint of every function, the screenshots and a grep of the names reached by `getattr` strings prove that nothing else changed. The mixins stay: their shared `self` state is the real coupling, but replacing it is a redesign, not a cleanup.

## Considered options

- Per-page controller objects and explicit window state instead of mixins (Option C): deferred. It rewrites ~186 method bodies, which the fingerprint can then no longer prove, to make 8 widget references explicit. Revisit only for a second window or front end that must share page logic.
- Also merging `app`, `main_ui` and `navigation` into `window.py`, and `dialogs`, `table_actions` and `pages/_common` into `base.py` (A+): rejected. It edits `__main__.py`, makes `ui.window` pull in the app start-up, gives `base.py` four unrelated jobs and makes the pages import it (a reversed import direction), and saves 6 files without changing any coupling.
- Moving the saved-names feature out of the Additional input page module (A2): rejected. It brings back two files for one page; section comments mark the feature instead.
- Grouping the core modules into sub-packages (Option B): rejected, when the base-report API was added. The automation tools import only `workflow`, `export` and `filenames` (21 import statements in 17 files), so regrouping would move every test and harness import without changing any coupling. The flat core keeps `base_report` beside `session` and `workflow`, which it builds on. No import-linter is added: the AST tests in `tests/unit/test_layering.py` already check the import directions that matter (`cci_ui` imports no tool, and the core never imports `clinical_reporting.ui`).

## Consequences

- To change a page, open its module in `ui/pages/`. A new widget goes into the page and its `EXPORTS` in the same file.
- The largest UI module, `pages/additional_input.py`, is about 1,100 lines; that is accepted.
- The shared window state and the `update_*_ui` refresh protocol in `base.py` stay as they are. A web front end reuses the Qt-free core, not the mixins, so it does not by itself reopen per-page controllers.
- No module of `clinical_reporting` outside `ui/` and `__main__.py` imports `clinical_reporting.ui`; an AST test in `tests/unit/test_layering.py` checks it.
- `cci_ui`, `cci_automation`, `safety_automation` and `peer_review_automation` keep their structure.
