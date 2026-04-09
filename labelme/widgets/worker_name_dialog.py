import os
import sys

from PyQt5.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QDialog
from labelme.utils.measure_working_time import get_worker_name_file_path


class WorkerNameWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('User name input')
        self.setGeometry(300, 300, 300, 150)

        layout = QVBoxLayout()

        label = QLabel('Please enter worker name:')
        self.text_input = QLineEdit(self)
        confirm_button = QPushButton('OK', self)
        confirm_button.clicked.connect(self.onConfirm)

        layout.addWidget(label)
        layout.addWidget(self.text_input)
        layout.addWidget(confirm_button)

        self.setLayout(layout)

    def onConfirm(self):
        entered_text = 'worker_name:' + self.text_input.text()
        self.write_worker_name(entered_text)
        self.accept()

    def write_worker_name(self, worker_name):
        worker_name_file = get_worker_name_file_path()
        with open(worker_name_file, "a") as f:
            f.write(worker_name)
