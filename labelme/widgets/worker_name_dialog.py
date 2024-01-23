import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout

class PopupWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle('팝업 창')
        self.setGeometry(300, 300, 300, 150)

        layout = QVBoxLayout()

        label = QLabel('텍스트를 입력하세요:')
        self.text_input = QLineEdit(self)
        confirm_button = QPushButton('확인', self)
        confirm_button.clicked.connect(self.onConfirm)

        layout.addWidget(label)
        layout.addWidget(self.text_input)
        layout.addWidget(confirm_button)

        self.setLayout(layout)

    def onConfirm(self):
        entered_text = self.text_input.text()
        print(f'입력된 텍스트: {entered_text}')
        self.close()