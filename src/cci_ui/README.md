# CCI design system (`cci_ui`)

The shared PySide6 design system of all four tools: the colors, sizes and
type (`theme/`), the components (`widgets/`), the icons, the small tools'
window and workflow page, and the four tools' app icons. Every tool starts
with `cci_ui.app.create_app` and builds its window from these pieces in Python
code (no Qt Designer files), laid out with Qt layouts so the controls follow
the window's size. Appearance (System, Light, or Dark) and density
(Comfortable or Compact) are set in the Display popover and shared by all
four tools.

`cci_ui` never imports the tools' packages (`tests/unit/test_layering.py`),
so every tool can depend on it. Its design values (`theme/tokens.py`,
`theme/qss.py`) and `files.py` don't import Qt at all
(`tests/unit/test_headless_imports.py`).

## Colors, sizes, and type

Edit `src/cci_ui/theme/tokens.py`: the light and dark colors, the
Comfortable and Compact sizes, the type scale. The stylesheet is generated
from it (`theme/qss.py`). The values match the approved mockup in
`docs/design/clinical-reporting-mockup.html`, and
`tests/ui/test_theme_tokens.py` keeps them in step: change both together.
Check the result in the [gallery](#checking-the-look-the-gallery), in both
schemes and densities.

## Components

Each component is a module in `src/cci_ui/widgets/` (buttons, sections,
pages, the sidebar, banners, ...). A new module goes in the import list in
`widgets/__init__.py` (that registers its stylesheet rules) and on a gallery
page (that puts it under `tests/ui/test_no_stray_windows.py`, which fails
if building one opens a stray window). Show or hide a child widget only once
it has a parent; the package docstring explains why.

The small tools are built from two pieces. `cci_ui.tool_window.ToolWindow` is
the window (the shell, a task runner behind the busy overlay; `run_tool`
starts the app and remembers the window's size). `WorkflowPage`
(`widgets/workflow_page.py`) is one workflow's page: the tool's input rows,
the output folder, a file name with the name it will save, a banner, and Run.
The tool hands `WorkflowPage.start` a job that returns the workbook; the page
runs it in the background and saves it (`cci_ui.files.save_output`). The
core side of a workflow uses `clinical_reporting.workflow` (see
[Shared backend](../../README.md#shared-backend)); the page shows the errors
whose types the tool lists in `expected_errors` as warnings.

Every tool's window reopens at the size and position it had when it was
closed (`cci_ui.window_state.WindowState.remember`); the two with a sidebar
(Clinical Reporting and CCI Automation) also keep it as wide (and collapsed
or not) as it was.

Slow work runs off the GUI thread through `cci_ui.tasks` (`run_task`,
`TaskRunner`), behind the busy overlay.

## Icons

A new icon is a Lucide SVG copied into `src/cci_ui/assets/icons/` (from the
version in `assets/icons/VERSION`) and a constant in `IconName`
(`cci_ui/icons.py`); `tests/ui/test_icons.py` checks that every file has a
name and every name a file.

## Checking the look: the gallery

The gallery window shows every component: colors (with contrast), type,
icons, buttons, inputs, toggles and segmented controls, sections, lists,
tables, the side panel, the workflow page of the small tools, banners,
toasts, the status bar, the busy overlay, and empty states.

```bash
python -m cci_ui.gallery                               # open it
python -m cci_ui.gallery --theme dark --density compact --size 1000x620
python -m cci_ui.gallery --screenshot shots            # every page, light and dark
```

`--screenshot` runs without opening a window and saves one PNG per page and
scheme (only the `--page` given, if any), which makes it easy to review a
change to `cci_ui/theme/tokens.py` or a component. The gallery never changes
the appearance saved for the real tools.

After a change, run `python -m pytest -q tests/ui`. Clinical Reporting's own
pages and their checks are described in its
[README](../clinical_reporting/README.md#changing-the-ui).

## App icons

Each tool's icon is a white line icon on a rounded square of the tool's
color: `APP_ICONS` in `src/cci_ui/app_icons.py`. The `.ico` files in
`src/cci_ui/assets/app-icons/` are drawn from it; after changing it, draw
them again and commit them:

```bash
python -m cci_ui.app_icons
```

The builds use them as the executables' icons (`build_support.app_icon`).
`create_app`, which every tool starts with (the small tools through
`run_tool`), uses the tool's icon as the window icon.

## Package layout

```text
src/cci_ui/
  app.py                       # create_app(): style, font, theme, error dialog
  assets.py                    # finds bundled files from source or a built exe
  icons.py                     # icon(IconName.X): icons drawn in theme colors
  theme/tokens.py              # colors, sizes, type scale (no Qt; also exports CSS)
  theme/qss.py                 # stylesheet built from the tokens (no Qt)
  theme/palette.py             # Qt palette built from the tokens
  theme/fonts.py               # loads the bundled Inter font
  theme/glyphs.py              # renders icons; writes the stylesheet's arrow/tick images
  theme/manager.py             # System/Light/Dark and density, shared by all tools
  widgets/buttons.py           # make_button/icon_button: primary, secondary, plain…
  widgets/labels.py            # type-scale labels; ElidedLabel shortens long paths
  widgets/section.py           # Section: titled card of label/field rows
  widgets/page.py              # Page: title, body, footer, empty state; form/workspace/split
  widgets/responsive.py        # breakpoints; panel beside or below the main area
  widgets/path_picker.py       # PathPicker: path + Choose… + Remove
  widgets/side_panel.py        # SidePanel: sections beside a grid, or below it
  widgets/toggle.py            # ToggleSwitch (a QCheckBox drawn as a switch)
  widgets/segmented.py         # SegmentedControl
  widgets/display.py           # Display button + popover (appearance, density)
  widgets/search.py            # SearchField
  widgets/views.py             # lists/tables with placeholder text; EmptyState
  widgets/status.py            # StatusBanner, show_toast, show_error
  widgets/busy.py              # BusyOverlay (blocks input; spinner after 150 ms)
  widgets/tables.py            # column rules, density rows, table_card, TableToolbar
  widgets/dual_list.py         # DualListPicker (available ⇄ selected lists)
  widgets/sidebar.py           # Sidebar with status badges; collapses to icons
  widgets/shell.py             # AppShell: sidebar, header, pages, status bar, busy overlay
  widgets/workflow_page.py     # WorkflowPage: a small tool's inputs, output, and Run
  tool_window.py               # ToolWindow, show_tool, run_tool: a small tool's window
  files.py                     # save_output: a workflow's workbook into the chosen folder
  window_state.py              # remembered window size/position and sidebar per tool
  tasks.py                     # run_task/TaskRunner: slow work off the GUI thread
  gallery.py                   # python -m cci_ui.gallery (every component)
  app_icons.py                 # the tools' app icons (python -m cci_ui.app_icons)
  assets/fonts/                # Inter 4.1 (SIL Open Font License)
  assets/icons/                # Lucide 1.49.0 line icons used by the apps (ISC)
  assets/app-icons/            # each tool's .ico, drawn by app_icons.py
```
