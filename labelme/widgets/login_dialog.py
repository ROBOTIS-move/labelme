# -*- coding: utf-8 -*-
"""
Login Dialog for Cloud-Native Labelme.
사용자 ID를 입력받아 인증하는 다이얼로그.
"""

from qtpy import QtWidgets


class LoginDialog(QtWidgets.QDialog):
    """
    사용자 ID 입력 다이얼로그.
    Firebase 연동 전까지는 Mock 인증 사용.
    """

    # 임시 허용 ID 목록 (추후 Firebase 연동으로 대체)
    ALLOWED_IDS = ["jsh@robotis.com", ""]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_id = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("로그인")
        self.setFixedSize(350, 180)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title label
        title_label = QtWidgets.QLabel("작업자 ID를 입력해주세요:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)

        # ID Input field
        self.id_input = QtWidgets.QLineEdit(self)
        self.id_input.setPlaceholderText("ID 입력")
        self.id_input.setMinimumHeight(32)
        self.id_input.returnPressed.connect(self._on_confirm)
        layout.addWidget(self.id_input)

        # Error message label (initially hidden)
        self.error_label = QtWidgets.QLabel("승인되지 않은 ID입니다. 다시 확인해주세요.")
        self.error_label.setStyleSheet("color: red; font-size: 12px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Confirm button
        self.confirm_button = QtWidgets.QPushButton("확인", self)
        self.confirm_button.setMinimumHeight(36)
        self.confirm_button.clicked.connect(self._on_confirm)
        layout.addWidget(self.confirm_button)

        layout.addStretch()

    def _on_confirm(self):
        """확인 버튼 클릭 시 ID 검증."""
        entered_id = self.id_input.text().strip()

        if not entered_id:
            self.error_label.setText("ID를 입력해주세요.")
            self.error_label.setVisible(True)
            return

        # Mock 인증: 허용된 ID인지 확인 (추후 Firebase 연동으로 대체)
        if self._validate_id(entered_id):
            self.user_id = entered_id
            self.error_label.setVisible(False)
            self.accept()
        else:
            self.error_label.setText("승인되지 않은 ID입니다. 다시 확인해주세요.")
            self.error_label.setVisible(True)

    def _validate_id(self, user_id: str) -> bool:
        """
        ID 유효성 검사 (Mock 구현).
        추후 Firebase Auth 또는 Firestore 연동으로 대체 예정.
        """
        # TODO: Firebase 연동 시 실제 인증 로직으로 교체
        return user_id.lower() in [aid.lower() for aid in self.ALLOWED_IDS]

    def get_user_id(self) -> str:
        """인증된 사용자 ID 반환."""
        return self.user_id
