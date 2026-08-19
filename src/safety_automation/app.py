# This Python file uses the following encoding: utf-8
import os
import sys
import traceback

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from safety_automation.ui_form import Ui_Widget


class Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.load_ui()

    def load_ui(self):
        # Combo Box
        comboBox_options = ["Corelisting AE & DLT report"]
        self.ui.optionComboBox.addItems(comboBox_options)

        # Choose input Directory
        self.ui.inputButton.clicked.connect(self.input_clicker)

        # Choose output Directory
        self.ui.outputButton.clicked.connect(self.output_clicker)

        # Run
        self.ui.runButton.clicked.connect(self.run_clicker)

        # Combo box 1
        self.onComboBoxChanged()
        self.ui.optionComboBox.currentIndexChanged.connect(self.onComboBoxChanged)

        # Line edit for Input
        self.on_lineEdit_changed()
        self.ui.lineEdit.textChanged.connect(self.on_lineEdit_changed)
        self.input_file_path = None

    def on_lineEdit_changed(self, text=None):
        # update the changed line edit
        self.output_file_name = text

    def onComboBoxChanged(self):
        """Handle changes in comboBox and update comboBox_2 and other UI elements."""
        self.selected_option = self.ui.optionComboBox.currentText()

    def input_clicker(self):
        """Open a file dialog when the user clicks the button.
        Choose corelisting (zip file) only.
        """
        if self.selected_option == "Corelisting AE & DLT report":
            # point to the default download directory
            default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select the raw file of Clockify Dashboard",
                default_dir,
                "Zip files (*.zip)",
            )
            # output filename to screen
            if file_path:
                self.ui.inputLabel.setText(file_path)
                self.input_file_path = file_path

    def output_clicker(self):
        # self.ui.label.setText("You Clicked")
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        output_folder_name = QFileDialog.getExistingDirectory(self, "Select Output Folder", default_dir)
        # output filename to screen
        if output_folder_name:
            self.ui.outputLabel.setText(output_folder_name)
            self.output_folder_name = output_folder_name

    def run_clicker(self):
        if self.selected_option == "Corelisting AE & DLT report":
            from safety_automation.ae_corelisting.AECoreListing import AECoreListing

            if (
                not self.selected_option
                or not self.input_file_path
                or not self.output_folder_name
                or not self.output_file_name
            ):
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Please make sure all those selections are entered correctly.",
                )
            else:
                try:
                    AECoreListing(self.input_file_path, self.output_folder_name, self.output_file_name)
                    self.ui.confirmLabel.setText(
                        "Confirmed: Corelisting AE & DLT report selected. Output file name is "
                        + self.output_file_name
                        + ".xlsx"
                    )
                except Exception as e:
                    self.ui.confirmLabel.setText("Error: encountered.")
                    QMessageBox.warning(self, "Error", str(e) + traceback.format_exc())


def main():
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
