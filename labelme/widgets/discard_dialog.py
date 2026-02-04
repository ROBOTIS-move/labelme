# -*- coding: utf-8 -*-

from qtpy import QtWidgets


class DiscardDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.discard_reason = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Discard Task")
        self.setFixedSize(400, 250)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Warning icon and message
        warning_layout = QtWidgets.QHBoxLayout()
        warning_icon = QtWidgets.QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 24px;")
        warning_label = QtWidgets.QLabel("Do you want to discard this task?")
        warning_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #d32f2f;")
        warning_layout.addWidget(warning_icon)
        warning_layout.addWidget(warning_label)
        warning_layout.addStretch()
        layout.addLayout(warning_layout)

        # Instruction
        instruction_label = QtWidgets.QLabel("Please enter the reason for discarding:")
        layout.addWidget(instruction_label)

        # Reason input (TextEdit for multi-line input)
        self.reason_input = QtWidgets.QTextEdit(self)
        self.reason_input.setPlaceholderText(
            "e.g. Image is too dark for labeling.\n"
            "e.g. Lens is obstructed.\n"
            "e.g. Low image quality, difficult to identify objects."
        )
        self.reason_input.setToolTip("Enter reason for discarding")
        self.reason_input.setMinimumHeight(80)
        layout.addWidget(self.reason_input)

        # Button layout
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(12)

        # Cancel button
        self.cancel_button = QtWidgets.QPushButton("Cancel", self)
        self.cancel_button.setMinimumHeight(36)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        # Confirm button
        self.confirm_button = QtWidgets.QPushButton("Confirm Discard", self)
        self.confirm_button.setToolTip("Confirm discard")
        self.confirm_button.setMinimumHeight(36)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        self.confirm_button.clicked.connect(self._on_confirm)
        button_layout.addWidget(self.confirm_button)

        layout.addLayout(button_layout)

    def _on_confirm(self):
        reason = self.reason_input.toPlainText().strip()

        if not reason:
            QtWidgets.QMessageBox.warning(
                self,
                "Input Required",
                "Please enter the reason for discarding."
            )
            return

        self.discard_reason = reason
        self.accept()

    def get_discard_reason(self) -> str:
        return self.discard_reason
