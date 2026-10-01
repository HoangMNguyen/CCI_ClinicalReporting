"""Dialog workflows shared by more than one page.

Keeping these here avoids page-to-page imports: both the Source data page
and the Preview & export page open the same settings-folder dialog, so the
workflow lives in this neutral module instead of either page's own.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog

from clinical_reporting import feedback


def show_settings_folder(widget, folder: str) -> None:
    """Show *folder* as the settings folder on both pages that choose it."""
    for picker in (
        getattr(widget.ui, "pathPicker_settings_folder", None),
        getattr(widget.ui, "pathPicker_output_setting_folder", None),
    ):
        if picker is not None:
            picker.set_path(folder)


def choose_settings_directory(widget) -> None:
    """Run the shared settings-folder selection workflow on *widget*.

    The settings-folder buttons on the Source data and Preview & export
    pages share this workflow: open the directory dialog, remember the
    choice, confirm it, and refresh the saved-settings list. Each click
    handler performs only its page-specific precondition before delegating
    here.
    """
    initial_dir = widget.settings_directory or widget._get_default_settings_directory()
    settings_dir = QFileDialog.getExistingDirectory(
        widget,
        "Select Settings Folder",
        initial_dir,
    )
    if not settings_dir:
        return

    widget.settings_directory = settings_dir
    show_settings_folder(widget, settings_dir)
    widget._set_label_text(
        widget.label_save_confirmation,
        feedback.info(f"Settings folder set to {settings_dir}"),
    )
    if widget.ui.checkBox_saved_setting.isChecked():
        widget._refresh_saved_settings()
