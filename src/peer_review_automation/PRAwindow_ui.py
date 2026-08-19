# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'PRAwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.4.2
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QLabel, QMainWindow,
    QMenuBar, QPushButton, QSizePolicy, QStatusBar,
    QTabWidget, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(651, 395)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setGeometry(QRect(10, 0, 631, 351))
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.pushButton = QPushButton(self.tab)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setGeometry(QRect(10, 30, 151, 21))
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.pushButton.setFont(font)
        self.pushButton_4 = QPushButton(self.tab)
        self.pushButton_4.setObjectName(u"pushButton_4")
        self.pushButton_4.setGeometry(QRect(10, 250, 241, 51))
        self.label = QLabel(self.tab)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(170, 30, 451, 61))
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.label.setWordWrap(True)
        self.pushButton_2 = QPushButton(self.tab)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setGeometry(QRect(10, 100, 151, 21))
        self.pushButton_2.setFont(font)
        self.label_2 = QLabel(self.tab)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(170, 100, 451, 61))
        self.label_2.setFont(font)
        self.label_2.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.pushButton_3 = QPushButton(self.tab)
        self.pushButton_3.setObjectName(u"pushButton_3")
        self.pushButton_3.setGeometry(QRect(10, 170, 151, 21))
        self.pushButton_3.setFont(font)
        self.label_3 = QLabel(self.tab)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(170, 170, 451, 61))
        self.label_3.setFont(font)
        self.label_3.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.checkBox = QCheckBox(self.tab)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setGeometry(QRect(10, 0, 141, 31))
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(10)
        self.checkBox.setFont(font1)
        self.label_confirm1 = QLabel(self.tab)
        self.label_confirm1.setObjectName(u"label_confirm1")
        self.label_confirm1.setGeometry(QRect(280, 250, 241, 51))
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.label_4 = QLabel(self.tab_2)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(90, 10, 341, 61))
        font2 = QFont()
        font2.setFamilies([u"Comic Sans MS"])
        font2.setPointSize(18)
        font2.setUnderline(True)
        self.label_4.setFont(font2)
        self.label_4.setAlignment(Qt.AlignCenter)
        self.label_5 = QLabel(self.tab_2)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(40, 70, 411, 41))
        font3 = QFont()
        font3.setFamilies([u"Comic Sans MS"])
        font3.setPointSize(11)
        self.label_5.setFont(font3)
        self.tabWidget.addTab(self.tab_2, "")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 651, 25))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"SDS File", None))
        self.pushButton_4.setText(QCoreApplication.translate("MainWindow", u"Run Peer Review Automation", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"SDS Input:", None))
        self.pushButton_2.setText(QCoreApplication.translate("MainWindow", u"Validation File", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Validation Input:", None))
        self.pushButton_3.setText(QCoreApplication.translate("MainWindow", u"Output Location", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Output:", None))
        self.checkBox.setText(QCoreApplication.translate("MainWindow", u"Check naming", None))
        self.label_confirm1.setText(QCoreApplication.translate("MainWindow", u"Confirmation: ", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"Peer Review Automation", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Future Project", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"What should I put here?", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("MainWindow", u"Future Project", None))
    # retranslateUi

