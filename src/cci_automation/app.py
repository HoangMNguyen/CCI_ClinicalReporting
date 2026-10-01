# This Python file uses the following encoding: utf-8
import os
import sys
import traceback
import warnings
from datetime import date, datetime

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from cci_automation.ui_form import Ui_Widget


class Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.load_ui()

    def load_ui(self):
        self.setWindowTitle("CCI Automation")
        # Combo Box
        comboBox_options = [
            "",
            "Enrollment Log",
            "DSMB Report",
            "Format for lab range issue and no leading 0 date",
        ]
        self.ui.comboBox.addItems(comboBox_options)

        # Combo Box2
        comboBox2_options = [""]
        self.ui.comboBox_2.addItems(comboBox2_options)

        # Date edit check box
        self.ui.checkBox.stateChanged.connect(self.toggle_dateEdit)
        self.ui.checkBox.setVisible(False)

        # QDateEdit creation
        self.ui.dateEdit.setVisible(False)  # Date picker hidden by default

        # Choose input Directory
        self.ui.pushButton.clicked.connect(self.clicker)

        # Choose output Directory
        self.ui.pushButton_2.clicked.connect(self.clicker_output_folder)

        # Input text

        # Run
        self.ui.pushButton_3.clicked.connect(self.run)

        ###link interaction afterdeclare variables
        # Combo box 1
        self.onComboBoxChanged()
        self.ui.comboBox.currentIndexChanged.connect(self.onComboBoxChanged)

        # Combo box 2
        self.onComboBoxChanged2()
        self.ui.comboBox_2.currentIndexChanged.connect(self.onComboBoxChanged2)
        # Line edit for Input
        self.on_lineEdit_changed()
        self.ui.lineEdit.textChanged.connect(self.on_lineEdit_changed)
        self.input_file_path = None

    def clicker(self):
        """Open a file dialog when the user clicks the button.
        Options: DSMB Report, Enrollment Log, Format for lab range issue
        """
        if self.selected_option == "DSMB Report" or self.selected_option == "Enrollment Log":
            # point to the default download directory
            default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select the Corelisting ZIP",
                default_dir,
                "Zip files (*.zip)",
            )
            # output filename to screen
            if file_path:
                self.ui.label_2.setText(file_path)
                self.input_file_path = file_path

        elif self.selected_option == "Format for lab range issue and no leading 0 date":
            default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select the raw .csv or .xlsx file",
                default_dir,
                "All files (*.csv *.xlsx)",
            )
            # output filename to screen
            if file_path:
                self.ui.label_2.setText(file_path)
                self.input_file_path = file_path

            # update the changed line edit to the new file name
            self.ui.lineEdit.setText(os.path.basename(file_path).split(".")[0] + "_formatted")
            # make it editable
            self.ui.lineEdit.setEnabled(True)

    def toggle_dateEdit(self, state):
        """Change the state of the date picker based on the checkbox state.
            If checkbox is checked (state == 2), show the date picker. Otherwise, hide it.
        Args:
            state (_type_): _description_
        """

        self.ui.dateEdit.setVisible(state == 2)

    def clicker_output_folder(self):
        # self.ui.label.setText("You Clicked")
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        output_folder_name = QFileDialog.getExistingDirectory(self, "Select Output Folder", default_dir)
        # output filename to screen
        if output_folder_name:
            self.ui.label_3.setText(output_folder_name)
            self.output_folder_name = output_folder_name

    def onComboBoxChanged(self):
        """Handle changes in comboBox and update comboBox_2 and other UI elements."""
        self.selected_option = self.ui.comboBox.currentText()

        # Clear comboBox_2 and update based on the selected option
        self.ui.comboBox_2.clear()
        if self.selected_option == "Enrollment Log":
            self.ui.comboBox_2.addItems(
                ["03325", "03821", "11823", "10325", "12423", "15122", "15420", "16321", "30425", "50425"]
            )
            self.ui.comboBox_2.setVisible(True)
        elif self.selected_option == "DSMB Report":
            self.ui.comboBox_2.addItems(["15420", "11823", "12423", "15122", "03821", "16321", "03325", "10325"])
            self.ui.comboBox_2.setVisible(True)
        elif self.selected_option == "Format for lab range issue and no leading 0 date":
            # Hide comboBox_2
            self.ui.comboBox_2.setVisible(False)

        # Update other UI elements based on the selected option
        if self.selected_option == "Enrollment Log":
            self.ui.checkBox.setVisible(True)
            self.ui.lineEdit.setText(
                datetime.now().strftime("%y%m%d") + "-" + self.selected_option2 + " Enrollment Log"
            )
            self.ui.lineEdit.setEnabled(True)
            self.ui.lineEdit.show()
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton_2.setEnabled(True)
        elif self.selected_option == "DSMB Report":
            self.ui.checkBox.setVisible(True)
            self.ui.lineEdit.setText(datetime.now().strftime("%y%m%d") + "-" + self.selected_option2 + " DSMB Report")
            self.ui.lineEdit.setEnabled(True)
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton_2.setEnabled(True)
        elif self.selected_option == "Format for lab range issue and no leading 0 date":
            self.ui.checkBox.setVisible(False)
            self.ui.dateEdit.setVisible(False)
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton_2.setEnabled(True)
            self.ui.lineEdit.setText("")
            self.ui.lineEdit.setEnabled(True)

    def onComboBoxChanged2(self):
        """_summary_"""
        # Get the selected item text
        self.selected_option2 = self.ui.comboBox_2.currentText()
        if self.selected_option == "Enrollment Log":
            self.ui.lineEdit.setText(date.today().strftime("%y%m%d") + "-" + self.selected_option2 + " Enrollment Log")
        elif self.selected_option == "DSMB Report":
            self.ui.lineEdit.setText(datetime.now().strftime("%y%m%d") + "-" + self.selected_option2 + " DSMB Report")
            self.ui.lineEdit.setEnabled(True)

    def on_lineEdit_changed(self, text=None):
        # update the changed line edit
        self.output_file_name = text

    def run(self):
        cut_off_date = None
        if self.ui.checkBox.isChecked():
            cut_off_date = self.ui.dateEdit.date().toPython()
        if self.selected_option == "Enrollment Log":
            from cci_automation.enrollment_log.EnrollmentLog import EnrollmentLog

            # option for enrollment log
            if (
                not self.selected_option2
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
                    EnrollmentLog(
                        self.selected_option2,
                        self.input_file_path,
                        self.output_folder_name,
                        self.output_file_name,
                        cut_off_date,
                    )
                    self.ui.label_5.setText(
                        "Confirmed: Enrollment Log "
                        + self.selected_option2
                        + " study selected. Output file name is "
                        + self.output_file_name
                        + ".xlsx"
                    )
                except Exception as e:
                    self.ui.label_5.setText("Error encountered.")
                    QMessageBox.warning(self, "Error", str(e) + traceback.format_exc())
        elif self.selected_option == "DSMB Report":
            from cci_automation.dsmb.DSMB import DSMB

            # option for enrollment log
            if not self.selected_option2 or not self.input_file_path or not self.output_folder_name:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Please make sure all those selections are entered correctly.",
                )
            else:
                try:
                    DSMB(
                        self.selected_option2,
                        self.input_file_path,
                        self.output_folder_name,
                        self.ui.lineEdit.text(),
                        cut_off_date,
                    )
                    self.ui.label_5.setText(
                        "Confirmed: DSMB Report "
                        + self.selected_option2
                        + " study selected. Output file name is "
                        + self.ui.lineEdit.text()
                        + ".xlsx"
                    )
                except Exception as e:
                    self.ui.label_5.setText("Error encountered.")
                    QMessageBox.warning(self, "Error", str(e) + traceback.format_exc())
        elif self.selected_option == "Format for lab range issue and no leading 0 date":
            from cci_automation.format_tools.change_type import change_type

            if not self.input_file_path or not self.output_folder_name or not self.output_file_name:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Please make sure all those selections are entered correctly.",
                )
            else:
                try:
                    change_type(
                        self.input_file_path,
                        self.output_folder_name,
                        self.output_file_name,
                    )
                    self.ui.label_5.setText(
                        "Confirmed: File has been formatted and saved as " + self.output_file_name + ".xlsx"
                    )
                except Exception as e:
                    self.ui.label_5.setText("Error encountered.")
                    QMessageBox.warning(self, "Error", str(e) + traceback.format_exc())


def main():
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    app = QApplication(sys.argv)

    widget = Widget()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
