from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QDialog


class InvalidVersionWindow(QDialog):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        print(self.mode)
        self.alarm_text = {
            0: [
                'Internet Checker',
                '인터넷을 상태를 확인해주세요.'],
            1: [
                'Version Checker',
                '버전 정보가 맞지 않습니다. 새로운 버전을 다운로드 해주세요']}
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.alarm_text[self.mode][0])
        self.setGeometry(300, 300, 500, 500)

        layout = QVBoxLayout()

        label = QLabel(self.alarm_text[self.mode][1])
        confirm_button = QPushButton('확인', self)
        confirm_button.clicked.connect(self.onConfirm)

        layout.addWidget(label)
        layout.addWidget(confirm_button)

        self.setLayout(layout)

    def onConfirm(self):
        exit(0)
