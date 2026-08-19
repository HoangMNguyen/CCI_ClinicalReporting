# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.4.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName("Widget")
        Widget.setWindowModality(Qt.NonModal)
        Widget.resize(510, 360)
        font = QFont()
        font.setFamilies(["Calibri"])
        font.setPointSize(11)
        Widget.setFont(font)
        Widget.setAutoFillBackground(True)
        self.label = QLabel(Widget)
        self.label.setObjectName("label")
        self.label.setGeometry(QRect(20, 20, 301, 16))
        self.label.setFont(font)
        self.pushButton = QPushButton(Widget)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setGeometry(QRect(20, 130, 141, 24))
        self.pushButton.setFont(font)
        self.label_2 = QLabel(Widget)
        self.label_2.setObjectName("label_2")
        self.label_2.setGeometry(QRect(170, 130, 321, 51))
        font1 = QFont()
        font1.setFamilies(["Calibri"])
        font1.setPointSize(10)
        self.label_2.setFont(font1)
        self.label_2.setScaledContents(False)
        self.label_2.setAlignment(Qt.AlignLeading | Qt.AlignLeft | Qt.AlignTop)
        self.label_2.setWordWrap(True)
        self.pushButton_2 = QPushButton(Widget)
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_2.setGeometry(QRect(20, 180, 141, 24))
        self.pushButton_2.setFont(font)
        self.label_3 = QLabel(Widget)
        self.label_3.setObjectName("label_3")
        self.label_3.setGeometry(QRect(170, 180, 321, 51))
        self.label_3.setFont(font1)
        self.label_3.setScaledContents(False)
        self.label_3.setAlignment(Qt.AlignLeading | Qt.AlignLeft | Qt.AlignTop)
        self.label_3.setWordWrap(True)
        self.pushButton_3 = QPushButton(Widget)
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_3.setGeometry(QRect(40, 300, 101, 41))
        font2 = QFont()
        font2.setFamilies(["Calibri"])
        font2.setPointSize(11)
        font2.setBold(True)
        self.pushButton_3.setFont(font2)
        self.comboBox = QComboBox(Widget)
        self.comboBox.setObjectName("comboBox")
        self.comboBox.setGeometry(QRect(20, 40, 261, 24))
        self.comboBox.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.comboBox_2 = QComboBox(Widget)
        self.comboBox_2.setObjectName("comboBox_2")
        self.comboBox_2.setGeometry(QRect(300, 40, 191, 22))
        self.lineEdit = QLineEdit(Widget)
        self.lineEdit.setObjectName("lineEdit")
        self.lineEdit.setGeometry(QRect(20, 260, 391, 21))
        self.lineEdit.setFont(font1)
        self.label_4 = QLabel(Widget)
        self.label_4.setObjectName("label_4")
        self.label_4.setGeometry(QRect(20, 230, 381, 16))
        self.label_5 = QLabel(Widget)
        self.label_5.setObjectName("label_5")
        self.label_5.setGeometry(QRect(160, 290, 331, 51))
        self.label_5.setWordWrap(True)
        self.dateEdit = QDateEdit(Widget)
        self.dateEdit.setObjectName("dateEdit")
        self.dateEdit.setGeometry(QRect(230, 80, 110, 31))
        self.checkBox = QCheckBox(Widget)
        self.checkBox.setObjectName("checkBox")
        self.checkBox.setGeometry(QRect(20, 80, 201, 31))

        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)

    # setupUi

    def retranslateUi(self, Widget):
        self.label.setText(QCoreApplication.translate("Widget", "Please select what you need below:", None))
        self.pushButton.setText(QCoreApplication.translate("Widget", "Choose File", None))
        self.label_2.setText(QCoreApplication.translate("Widget", "No input file/folder selected.", None))
        self.pushButton_2.setText(QCoreApplication.translate("Widget", "Choose Destination", None))
        self.label_3.setText(QCoreApplication.translate("Widget", "No file destination selected", None))
        self.pushButton_3.setText(QCoreApplication.translate("Widget", "Run", None))
        self.label_4.setText(
            QCoreApplication.translate("Widget", "Please type the output file name in the box below", None)
        )
        self.label_5.setText("")
        self.checkBox.setText(QCoreApplication.translate("Widget", "Cut-off Date (optional)", None))
        pass

    # retranslateUi
