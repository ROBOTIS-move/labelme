# -*- coding: utf-8 -*-

import os
import json

from qtpy import QtWidgets
from qtpy import QtCore


class CommentWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = None
        self.current_user_id = None  # Currently logged in user ID (email)
        self.current_user_name = None  # Currently logged in user name
        self.comments = []  # [{"user": "name", "text": "msg"}, ...]
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # Comments header
        header_label = QtWidgets.QLabel("Comments")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header_label)

        # Comments list (QListWidget for individual item management)
        self.comments_list = QtWidgets.QListWidget(self)
        self.comments_list.setMinimumHeight(150)
        self.comments_list.setWordWrap(True)
        self.comments_list.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )
        self.comments_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.comments_list.customContextMenuRequested.connect(self._show_context_menu)
        self.comments_list.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #333333;
            }
        """)
        layout.addWidget(self.comments_list)

        # Comment input area
        self.comment_input = QtWidgets.QTextEdit(self)
        self.comment_input.setPlaceholderText("Enter your comment...")
        self.comment_input.setMinimumHeight(32)
        self.comment_input.setMaximumHeight(80)
        self.comment_input.setLineWrapMode(QtWidgets.QTextEdit.WidgetWidth)
        layout.addWidget(self.comment_input)

        # Confirm button
        self.confirm_button = QtWidgets.QPushButton("Add Comment", self)
        self.confirm_button.setMinimumHeight(32)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.confirm_button.clicked.connect(self._on_confirm)
        layout.addWidget(self.confirm_button)

    def set_read_only(self, read_only: bool):
        self.comment_input.setVisible(not read_only)
        self.confirm_button.setVisible(not read_only)

    def set_user_id(self, user_id: str):
        self.current_user_id = user_id

    def set_user_name(self, user_name: str):
        self.current_user_name = user_name

    def set_image_path(self, image_path: str):
        self.current_image_path = image_path
        self.comments = []
        self.comments_list.clear()

        # Load existing comment file if it exists
        if image_path:
            comment_file = self._get_comment_file_path(image_path)
            if os.path.exists(comment_file):
                self._load_comments(comment_file)

    def _get_comment_file_path(self, image_path: str) -> str:
        if not image_path:
            return ""
        base_path = os.path.splitext(image_path)[0]
        return base_path + "_comments.json"

    def _load_comments(self, comment_file: str):
        try:
            with open(comment_file, "r", encoding="utf-8") as f:
                self.comments = json.load(f)
                if not isinstance(self.comments, list):
                    self.comments = []
        except (json.JSONDecodeError, Exception):
            self.comments = []

        # Display comments in UI
        self._refresh_comments_display()

    def _refresh_comments_display(self):
        self.comments_list.clear()
        for idx, comment in enumerate(self.comments):
            user = comment.get("user", "unknown")
            text = comment.get("text", "")
            display_text = f"[{user}] {text}"

            item = QtWidgets.QListWidgetItem(display_text)
            item.setData(QtCore.Qt.UserRole, idx)  # Save index

            # Style differently for comments written by self
            if user == (self.current_user_name or self.current_user_id):
                item.setForeground(QtCore.Qt.darkBlue)

            self.comments_list.addItem(item)

    def _show_context_menu(self, position):
        item = self.comments_list.itemAt(position)
        if not item:
            return

        idx = item.data(QtCore.Qt.UserRole)
        if idx is None or idx >= len(self.comments):
            return

        comment = self.comments[idx]
        user = comment.get("user", "")

        menu = QtWidgets.QMenu(self)

        # Only allow deletion of own comments
        if user == (self.current_user_name or self.current_user_id):
            delete_action = menu.addAction("Delete")
            action = menu.exec_(self.comments_list.mapToGlobal(position))
            if action == delete_action:
                self._delete_comment(idx)
        else:
            info_action = menu.addAction("No permission to delete")
            info_action.setEnabled(False)
            menu.exec_(self.comments_list.mapToGlobal(position))

    def _delete_comment(self, idx: int):
        if 0 <= idx < len(self.comments):
            del self.comments[idx]
            self._save_comments()
            self._refresh_comments_display()

    def _on_confirm(self):
        comment_text = self.comment_input.toPlainText().strip()

        if not comment_text:
            return

        if not self.current_image_path:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No image loaded."
            )
            return

        if not self.current_user_id:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "User ID not set."
            )
            return

        # Add comment
        new_comment = {
            "user": self.current_user_name or self.current_user_id,
            "text": comment_text
        }
        self.comments.append(new_comment)

        # Save to file
        self._save_comments()

        # Refresh UI
        self._refresh_comments_display()

        # Clear input
        self.comment_input.clear()

    def _save_comments(self):
        if not self.current_image_path:
            return

        comment_file = self._get_comment_file_path(self.current_image_path)
        try:
            with open(comment_file, "w", encoding="utf-8") as f:
                json.dump(self.comments, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Save Error",
                f"Failed to save comments: {str(e)}"
            )

    def clear_comments(self):
        self.comments = []
        self.comments_list.clear()
        self.comment_input.clear()

    def get_comment_file_path(self) -> str:
        if self.current_image_path:
            return self._get_comment_file_path(self.current_image_path)
        return ""
