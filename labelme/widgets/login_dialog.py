# -*- coding: utf-8 -*-

from qtpy import QtWidgets

from labelme.firebase.authority_checker import AuthorityChecker


class LoginDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_id = None
        self.user_data = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Login")
        self.setFixedSize(350, 180)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title label
        title_label = QtWidgets.QLabel("Please enter your Worker ID:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)

        # ID Input field
        self.id_input = QtWidgets.QLineEdit(self)
        self.id_input.setPlaceholderText("Enter ID")
        self.id_input.setToolTip("Enter Worker ID")
        self.id_input.setMinimumHeight(32)
        self.id_input.returnPressed.connect(self._on_confirm)
        layout.addWidget(self.id_input)

        # Error message label (initially hidden)
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 12px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Confirm button
        self.confirm_button = QtWidgets.QPushButton("Confirm", self)
        self.confirm_button.setToolTip("Verify ID and login")
        self.confirm_button.setMinimumHeight(36)
        self.confirm_button.clicked.connect(self._on_confirm)
        layout.addWidget(self.confirm_button)

        layout.addStretch()

    def _on_confirm(self):
        entered_id = self.id_input.text().strip()

        if not entered_id:
            self.error_label.setText("Please enter your ID.")
            self.error_label.setVisible(True)
            return

        if self._validate_id(entered_id):
            self.user_id = entered_id
            self.error_label.setVisible(False)
            self.accept()
        else:
            self.error_label.setVisible(True)

    def _validate_id(self, user_id: str) -> bool:
        try:
            checker = AuthorityChecker()
            users = checker.get_all_users()
        except Exception:
            self.error_label.setText(
                "Server connection failed. Please try again."
            )
            return False

        for user in users:
            if user.get('email', '').lower() == user_id.lower():
                self.user_data = user
                return True

        self.error_label.setText(
            "Unregistered ID. Please contact the administrator."
        )
        return False

    def get_user_id(self) -> str:
        return self.user_id

    def get_user_data(self) -> dict:
        return self.user_data
