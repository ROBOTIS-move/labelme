#!/usr/bin/env python3
# Copyright 2022 ROBOTIS CO., LTD.
# Authors: Dongyun Kim

from qtpy import QT_VERSION
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

class WorkerNameDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()

        # 창의 레이아웃을 설정합니다.
        layout = QtWidgets.QVBoxLayout(self)

        # 텍스트 입력 필드를 추가합니다.
        self.text_edit = QtWidgets.QTextEdit()
        layout.addWidget(self.text_edit)

        # 확인 버튼을 추가합니다.
        button = QtWidgets.QPushButton("확인")
        button.clicked.connect(self.accept)
        layout.addWidget(button)

    def accept(self):
        # 텍스트 입력 필드의 텍스트를 반환합니다.
        return self.text_edit.toPlainText()