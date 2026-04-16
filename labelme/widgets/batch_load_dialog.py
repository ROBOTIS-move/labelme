# -*- coding: utf-8 -*-

from qtpy import QtWidgets
from qtpy import QtCore
from qtpy.QtCore import Qt


class BatchLoadDialog(QtWidgets.QDialog):

    def __init__(self, available_count, parent=None):
        super().__init__(parent)
        self.available_count = available_count
        self._requested_count = 0
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Batch Final Review")
        self.setFixedSize(340, 200)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        # Available count display
        info_label = QtWidgets.QLabel(
            f"Available tasks: <b>{self.available_count}</b>"
        )
        info_label.setStyleSheet("font-size: 14px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        # Spin box row
        spin_layout = QtWidgets.QHBoxLayout()
        spin_label = QtWidgets.QLabel("Download count:")
        spin_label.setStyleSheet("font-size: 13px;")
        spin_layout.addWidget(spin_label)

        max_val = self.available_count
        self.spin_box = QtWidgets.QSpinBox()
        self.spin_box.setMinimum(1)
        self.spin_box.setMaximum(max(max_val, 1))
        self.spin_box.setValue(min(10, max_val))
        self.spin_box.setMinimumHeight(28)
        spin_layout.addWidget(self.spin_box)
        layout.addLayout(spin_layout)

        layout.addStretch()

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QtWidgets.QPushButton("Download")
        ok_btn.setMinimumHeight(36)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

        if self.available_count == 0:
            ok_btn.setEnabled(False)
            self.spin_box.setEnabled(False)

    def _on_ok(self):
        self._requested_count = self.spin_box.value()
        self.accept()

    def get_requested_count(self):
        return self._requested_count
