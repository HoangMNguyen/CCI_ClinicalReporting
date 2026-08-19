# This Python file uses the following encoding: utf-8
import sys
import traceback

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from peer_review_automation.PRAwindow_ui import Ui_MainWindow
from peer_review_automation.sds import SDSData


class Widget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.file_path = ""
        self.file_path_out = ""
        self.SDS_file_path = None
        self.val_file_path = None
        self.checkName = False

        # Click and select the SDS file
        self.ui.pushButton.clicked.connect(self.clicker)
        # Click and select the Validation file
        self.ui.pushButton_2.clicked.connect(self.clicker2)
        # Click and select the output directory
        self.ui.pushButton_3.clicked.connect(self.clicker3)
        # Click and run the Peer Review Automation
        self.ui.pushButton_4.clicked.connect(self.runPRA)
        # Check box that toggles the naming-convention checks
        self.ui.checkBox.stateChanged.connect(self.checkedBox)

    def checkedBox(self):
        self.checkName = self.ui.checkBox.isChecked()

    def clicker(self):
        fname = QFileDialog.getOpenFileName(
            self, "Open SDS File", "", " Excel Files (*.xlsx);; CSV Files (*.csv)"
        )

        # output filename to screen
        if fname:
            self.ui.label.setText("SDS input: " + fname[0])
            self.SDS_file_path = fname[0]

    def clicker2(self):
        fname = QFileDialog.getOpenFileName(
            self, "Open Validation File", "", " CSV Files (*.csv);; Excel Files (*.xlsx)"
        )

        # output filename to screen
        if fname:
            self.ui.label_2.setText("Validation input: " + fname[0])
            self.val_file_path = fname[0]

    def clicker3(self):
        fname_out = QFileDialog.getExistingDirectory(self, "Select Directory for Output")

        # output filename to screen
        if fname_out:
            self.ui.label_3.setText("Output: " + fname_out)
            self.file_path_out = fname_out

    def runPRA(self):
        try:
            self.checkedBox()
            if self.SDS_file_path == "":
                QMessageBox.warning(self, "Warning", "Please select a SDS file")
            SDS = SDSData(self.checkName, self.SDS_file_path, self.val_file_path)
            SDS.output(self.file_path_out)
            self.ui.label_confirm1.setText("Confirmed: it works")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e) + traceback.format_exc())


def main():
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
