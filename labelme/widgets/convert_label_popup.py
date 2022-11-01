#!/usr/bin/env python3
# Copyright 2022 ROBOTIS CO., LTD.
# Authors: Eungi Cho

from qtpy import QtTest
from qtpy import QtWidgets
from qtpy.QtCore import Qt


class ConvertLabelPopup(QtWidgets.QProgressBar):

    def __init__(self, parent=None):
        super(ConvertLabelPopup, self).__init__(parent)

        self.popup = QtWidgets.QLabel()
        self.popup.setWindowTitle('Convert labels')
        self.popup.setMinimumHeight(50)
        self.popup.setMinimumWidth(300)
        self.popup.setText('Please wait for a moment...')
        self.popup.setAlignment(Qt.AlignHCenter)

        self.prograss_bar = QtWidgets.QProgressBar(self.popup)
        self.prograss_bar.setWindowTitle('Convert labels')
        self.prograss_bar.setGeometry(50, 20, 200, 25)
        self.prograss_bar.setValue(0)

    def show(self):
        self.popup.show()
        QtTest.QTest.qWait(100)

    def close(self):
        self.popup.close()

    def set_prograss(self, value):
        self.prograss_bar.setValue(value)
