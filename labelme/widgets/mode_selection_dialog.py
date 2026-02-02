# -*- coding: utf-8 -*-
"""
Mode Selection Dialog for Cloud-Native Labelme.
작업 모드(Labeling, Review, Final Review)를 선택하는 다이얼로그.
"""

from qtpy import QtWidgets
from qtpy import QtCore


class ModeSelectionDialog(QtWidgets.QDialog):
    """
    작업 모드 선택 다이얼로그.
    Labeling, Review, Final Review 중 선택.
    """

    # 작업 모드 상수
    MODE_LABELING = "labeling"
    MODE_REVIEW = "review"
    MODE_FINAL_REVIEW = "final_review"

    # 관리자 코드 (추후 Firebase에서 가져올 예정)
    ADMIN_CODE = "admin123"

    def __init__(self, user_id: str, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.selected_mode = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("작업 모드 선택")
        self.setFixedSize(400, 280)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        # Welcome message
        welcome_label = QtWidgets.QLabel(f"환영합니다, {self.user_id}님!")
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        welcome_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(welcome_label)

        # Instruction
        instruction_label = QtWidgets.QLabel("작업 모드를 선택해주세요:")
        instruction_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(instruction_label)

        layout.addSpacing(8)

        # Button container
        button_layout = QtWidgets.QVBoxLayout()
        button_layout.setSpacing(12)

        # Labeling button
        self.labeling_btn = QtWidgets.QPushButton("Labeling (일반 작업)")
        self.labeling_btn.setMinimumHeight(40)
        self.labeling_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.labeling_btn.clicked.connect(self._on_labeling)
        button_layout.addWidget(self.labeling_btn)

        # Review button
        self.review_btn = QtWidgets.QPushButton("Review (1차 검토)")
        self.review_btn.setMinimumHeight(40)
        self.review_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.review_btn.clicked.connect(self._on_review)
        button_layout.addWidget(self.review_btn)

        # Final Review button
        self.final_review_btn = QtWidgets.QPushButton("Final Review (최종 검토)")
        self.final_review_btn.setMinimumHeight(40)
        self.final_review_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.final_review_btn.clicked.connect(self._on_final_review)
        button_layout.addWidget(self.final_review_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

    def _on_labeling(self):
        """Labeling 모드 선택."""
        self.selected_mode = self.MODE_LABELING
        self.accept()

    def _on_review(self):
        """Review 모드 선택."""
        self.selected_mode = self.MODE_REVIEW
        self.accept()

    def _on_final_review(self):
        """Final Review 모드 선택 (관리자 코드 필요)."""
        admin_code, ok = QtWidgets.QInputDialog.getText(
            self,
            "관리자 인증",
            "관리자 코드를 입력해주세요:",
            QtWidgets.QLineEdit.Password
        )

        if ok and admin_code:
            # Mock 관리자 코드 검증 (추후 Firebase 연동으로 대체)
            if self._validate_admin_code(admin_code):
                self.selected_mode = self.MODE_FINAL_REVIEW
                self.accept()
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "인증 실패",
                    "관리자 코드가 올바르지 않습니다."
                )

    def _validate_admin_code(self, code: str) -> bool:
        """
        관리자 코드 검증 (Mock 구현).
        추후 Firebase system_config에서 가져올 예정.
        """
        # TODO: Firebase 연동 시 실제 검증 로직으로 교체
        return code == self.ADMIN_CODE

    def get_selected_mode(self) -> str:
        """선택된 모드 반환."""
        return self.selected_mode
