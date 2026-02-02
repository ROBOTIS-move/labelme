# -*- coding: utf-8 -*-
"""
Discard Dialog for Cloud-Native Labelme.
작업 폐기 사유를 입력받는 다이얼로그.
"""

from qtpy import QtWidgets


class DiscardDialog(QtWidgets.QDialog):
    """
    작업 폐기 사유 입력 다이얼로그.
    작업자가 직접 사유를 기입.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.discard_reason = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("작업 폐기")
        self.setFixedSize(400, 250)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Warning icon and message
        warning_layout = QtWidgets.QHBoxLayout()
        warning_icon = QtWidgets.QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 24px;")
        warning_label = QtWidgets.QLabel("이 작업을 폐기하시겠습니까?")
        warning_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #d32f2f;")
        warning_layout.addWidget(warning_icon)
        warning_layout.addWidget(warning_label)
        warning_layout.addStretch()
        layout.addLayout(warning_layout)

        # Instruction
        instruction_label = QtWidgets.QLabel("폐기 사유를 입력해주세요:")
        layout.addWidget(instruction_label)

        # Reason input (TextEdit for multi-line input)
        self.reason_input = QtWidgets.QTextEdit(self)
        self.reason_input.setPlaceholderText(
            "예: 이미지가 너무 어두워서 라벨링이 불가능합니다.\n"
            "예: 렌즈가 가려져 있습니다.\n"
            "예: 이미지 품질이 낮아 객체 식별이 어렵습니다."
        )
        self.reason_input.setMinimumHeight(80)
        layout.addWidget(self.reason_input)

        # Button layout
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(12)

        # Cancel button
        self.cancel_button = QtWidgets.QPushButton("취소", self)
        self.cancel_button.setMinimumHeight(36)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        # Confirm button
        self.confirm_button = QtWidgets.QPushButton("폐기 확인", self)
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
        """폐기 확인 버튼 클릭."""
        reason = self.reason_input.toPlainText().strip()

        if not reason:
            QtWidgets.QMessageBox.warning(
                self,
                "입력 필요",
                "폐기 사유를 입력해주세요."
            )
            return

        self.discard_reason = reason
        self.accept()

    def get_discard_reason(self) -> str:
        """입력된 폐기 사유 반환."""
        return self.discard_reason
