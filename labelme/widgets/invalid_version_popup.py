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
                '!!! 버전 정보를 확인할 수 없습니다. !!!\n네트워크 상태를 확인해주세요. !!!'],
            1: [
                'Version Checker',
                f'!!! 버전 정보가 맞지 않습니다. !!!\n 최신 버전을 다운로드 해주세요.\n현재 버전 : {local_version}, 최신 버전 : {github_version}']}
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

        confirm_button = QPushButton('확인', self)
        confirm_button.clicked.connect(self.onConfirm)

        layout.addWidget(label)
        layout.addWidget(confirm_button)

        self.setLayout(layout)

    def onConfirm(self):
        exit(0)
