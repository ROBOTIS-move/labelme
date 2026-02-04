# -*- coding: utf-8 -*-

from qtpy import QtWidgets
from qtpy import QtCore


class ModeSelectionDialog(QtWidgets.QDialog):

    # Working mode constants
    MODE_LABELING = "labeling"
    MODE_REVIEW = "review"
    MODE_FINAL_REVIEW = "final_review"

    # Admin code (To be fetched from Firebase later)
    ADMIN_CODE = "admin123"

    def __init__(self, user_id: str, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.selected_mode = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Select Working Mode")
        self.setFixedSize(400, 280)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        # Welcome message
        welcome_label = QtWidgets.QLabel(f"Welcome, {self.user_id}!")
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        welcome_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(welcome_label)

        # Instruction
        instruction_label = QtWidgets.QLabel("Please select your working mode:")
        instruction_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(instruction_label)

        layout.addSpacing(8)

        # Button container
        button_layout = QtWidgets.QVBoxLayout()
        button_layout.setSpacing(12)

        # Labeling button
        self.labeling_btn = QtWidgets.QPushButton("Labeling (General)")
        self.labeling_btn.setToolTip("General working mode")
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
        self.review_btn = QtWidgets.QPushButton("Review (1st Review)")
        self.review_btn.setToolTip("1st review mode")
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
        self.final_review_btn = QtWidgets.QPushButton("Final Review")
        self.final_review_btn.setToolTip("Final review mode (Admin only)")
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
        self.selected_mode = self.MODE_LABELING
        self.accept()

    def _on_review(self):
        self.selected_mode = self.MODE_REVIEW
        self.accept()

    def _on_final_review(self):
        admin_code, ok = QtWidgets.QInputDialog.getText(
            self,
            "Admin Authentication",
            "Please enter admin code:",
            QtWidgets.QLineEdit.Password
        )

        if ok and admin_code:
            # Mock admin code validation (Replace with Firebase integration later)
            if self._validate_admin_code(admin_code):
                self.selected_mode = self.MODE_FINAL_REVIEW
                self.accept()
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Authentication Failed",
                    "Invalid admin code."
                )

    def _validate_admin_code(self, code: str) -> bool:
        # TODO: Replace with actual validation logic upon Firebase integration
        return code == self.ADMIN_CODE

    def get_selected_mode(self) -> str:
        return self.selected_mode
