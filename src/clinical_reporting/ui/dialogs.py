"""Dialog workflows shared by more than one tab.

Keeping these here avoids tab-to-tab imports: both the settings tab and the
output tab open the same settings-folder dialog, so the workflow lives in
this neutral module instead of either tab's own.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog


def choose_settings_directory(widget) -> None:
    """Run the shared settings-folder selection workflow on *widget*.

    The settings-folder buttons on the settings and output tabs share this
    workflow: open the directory dialog, remember the choice, confirm it, and
    refresh the saved-settings list. Each click handler performs only its
    tab-specific precondition before delegating here.
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
    widget._set_label_text(
        widget.label_save_confirmation,
        f"Settings folder set to {settings_dir}",
    )
    if widget.ui.checkBox_saved_setting.isChecked():
        widget._refresh_saved_settings()
