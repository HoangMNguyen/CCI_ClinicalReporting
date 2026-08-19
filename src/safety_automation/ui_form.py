# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.5.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(447, 286)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Widget.sizePolicy().hasHeightForWidth())
        Widget.setSizePolicy(sizePolicy)
        self.label = QLabel(Widget)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(10, 10, 311, 21))
        font = QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.optionComboBox = QComboBox(Widget)
        self.optionComboBox.setObjectName(u"optionComboBox")
        self.optionComboBox.setGeometry(QRect(10, 30, 281, 24))
        self.optionComboBox.setFont(font)
        self.inputButton = QPushButton(Widget)
        self.inputButton.setObjectName(u"inputButton")
        self.inputButton.setGeometry(QRect(10, 60, 151, 24))
        font1 = QFont()
        font1.setPointSize(10)
        font1.setBold(False)
        self.inputButton.setFont(font1)
        self.outputButton = QPushButton(Widget)
        self.outputButton.setObjectName(u"outputButton")
        self.outputButton.setGeometry(QRect(10, 110, 151, 24))
        self.outputButton.setFont(font1)
        self.inputLabel = QLabel(Widget)
        self.inputLabel.setObjectName(u"inputLabel")
        self.inputLabel.setGeometry(QRect(170, 60, 271, 51))
        self.inputLabel.setFont(font)
        self.inputLabel.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.inputLabel.setWordWrap(True)
        self.outputLabel = QLabel(Widget)
        self.outputLabel.setObjectName(u"outputLabel")
        self.outputLabel.setGeometry(QRect(170, 110, 271, 51))
        self.outputLabel.setFont(font)
        self.outputLabel.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.outputLabel.setWordWrap(True)
        self.label_4 = QLabel(Widget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(10, 160, 311, 21))
        font2 = QFont()
        font2.setPointSize(10)
        font2.setItalic(False)
        self.label_4.setFont(font2)
        self.lineEdit = QLineEdit(Widget)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setGeometry(QRect(10, 180, 421, 24))
        self.lineEdit.setFont(font)
        self.runButton = QPushButton(Widget)
        self.runButton.setObjectName(u"runButton")
        self.runButton.setGeometry(QRect(10, 220, 101, 41))
        font3 = QFont()
        font3.setPointSize(10)
        font3.setBold(True)
        self.runButton.setFont(font3)
        self.confirmLabel = QLabel(Widget)
        self.confirmLabel.setObjectName(u"confirmLabel")
        self.confirmLabel.setGeometry(QRect(120, 210, 311, 61))
        self.confirmLabel.setFont(font)
        self.confirmLabel.setWordWrap(True)

        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Safety Automations", None))
        self.label.setText(QCoreApplication.translate("Widget", u"Please select the automation you need below:", None))
        self.inputButton.setText(QCoreApplication.translate("Widget", u"Choose Input File", None))
        self.outputButton.setText(QCoreApplication.translate("Widget", u"Choose Output Location", None))
        self.inputLabel.setText(QCoreApplication.translate("Widget", u"No input file selected", None))
        self.outputLabel.setText(QCoreApplication.translate("Widget", u"No output location selected", None))
        self.label_4.setText(QCoreApplication.translate("Widget", u"Please type the output file name in the box below:", None))
        self.runButton.setText(QCoreApplication.translate("Widget", u"Run", None))
        self.confirmLabel.setText(QCoreApplication.translate("Widget", u"Confirmation:", None))
    # retranslateUi

