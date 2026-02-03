from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class InvalidVersionWindow(QDialog):
    def __init__(self, mode, local_version, github_version):
        super().__init__()
        self.mode = mode
        print(self.mode)
        self.alarm_text = {
            0: [
                'Internet Checker',
                (
                    '!!! Cannot verify version information !!!\n'
                    'Please check your network connection !!!'
                )],
            1: [
                'Version Checker',
                (
                    f'!!! Version mismatch !!!\n'
                    'Please download the latest version.\n'
                    f'Current version: {local_version}, Latest version: {github_version}'
                )]}
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.alarm_text[self.mode][0])
        self.setGeometry(300, 300, 500, 500)

        layout = QVBoxLayout()

        label = QLabel(self.alarm_text[self.mode][1])
        font = QFont()
        font.setPointSize(20)  # 원하는 폰트 크기로 설정
        label.setFont(font)
        label.setAlignment(Qt.AlignCenter)  # 중앙 정렬
        label.setStyleSheet("color: red;")

        confirm_button = QPushButton('OK', self)
        confirm_button.clicked.connect(self.onConfirm)

        layout.addWidget(label)
        layout.addWidget(confirm_button)

        self.setLayout(layout)

    def onConfirm(self):
        exit(0)
