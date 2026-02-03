# -*- coding: utf-8 -*-
"""
Comment Widget for Cloud-Native Labelme.
Review 모드에서 사용하는 코멘트(댓글) 위젯.
JSON 기반 저장 및 삭제 기능 지원.
"""

import os
import json

from qtpy import QtWidgets
from qtpy import QtCore


class CommentWidget(QtWidgets.QWidget):
    """
    코멘트(댓글) 위젯.
    Review 및 Final Review 모드에서만 표시.
    JSON 파일로 저장하며, 본인이 작성한 댓글만 삭제 가능.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = None
        self.current_user_id = None  # 현재 로그인한 사용자 ID
        self.comments = []  # [{"user": "id", "text": "msg"}, ...]
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
            }
        """)
        layout.addWidget(self.comments_list)

        # Comment input area
        self.comment_input = QtWidgets.QLineEdit(self)
        self.comment_input.setPlaceholderText("Enter your comment...")
        self.comment_input.setMinimumHeight(32)
        self.comment_input.returnPressed.connect(self._on_confirm)
        layout.addWidget(self.comment_input)

        # Confirm button
        self.confirm_button = QtWidgets.QPushButton("Submit", self)
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

    def set_user_id(self, user_id: str):
        """현재 로그인한 사용자 ID 설정."""
        self.current_user_id = user_id

    def set_image_path(self, image_path: str):
        """
        현재 작업 중인 이미지 경로 설정.
        이 경로를 기반으로 JSON 파일을 저장.
        """
        self.current_image_path = image_path
        self.comments = []
        self.comments_list.clear()

        # 기존 코멘트 파일이 있으면 로드
        if image_path:
            comment_file = self._get_comment_file_path(image_path)
            if os.path.exists(comment_file):
                self._load_comments(comment_file)

    def _get_comment_file_path(self, image_path: str) -> str:
        """이미지 경로에서 코멘트 파일 경로 생성."""
        if not image_path:
            return ""
        base_path = os.path.splitext(image_path)[0]
        return base_path + "_comments.json"

    def _load_comments(self, comment_file: str):
        """기존 코멘트 JSON 파일 로드."""
        try:
            with open(comment_file, "r", encoding="utf-8") as f:
                self.comments = json.load(f)
                if not isinstance(self.comments, list):
                    self.comments = []
        except (json.JSONDecodeError, Exception):
            self.comments = []

        # UI에 댓글 표시
        self._refresh_comments_display()

    def _refresh_comments_display(self):
        """댓글 리스트 UI 갱신."""
        self.comments_list.clear()
        for idx, comment in enumerate(self.comments):
            user = comment.get("user", "unknown")
            text = comment.get("text", "")
            display_text = f"[{user}] {text}"

            item = QtWidgets.QListWidgetItem(display_text)
            item.setData(QtCore.Qt.UserRole, idx)  # 인덱스 저장

            # 본인이 작성한 댓글은 스타일 다르게
            if user == self.current_user_id:
                item.setForeground(QtCore.Qt.darkBlue)

            self.comments_list.addItem(item)

    def _show_context_menu(self, position):
        """우클릭 컨텍스트 메뉴 표시."""
        item = self.comments_list.itemAt(position)
        if not item:
            return

        idx = item.data(QtCore.Qt.UserRole)
        if idx is None or idx >= len(self.comments):
            return

        comment = self.comments[idx]
        user = comment.get("user", "")

        menu = QtWidgets.QMenu(self)

        # 본인이 작성한 댓글만 삭제 가능
        if user == self.current_user_id:
            delete_action = menu.addAction("Delete")
            action = menu.exec_(self.comments_list.mapToGlobal(position))
            if action == delete_action:
                self._delete_comment(idx)
        else:
            info_action = menu.addAction("No permission to delete")
            info_action.setEnabled(False)
            menu.exec_(self.comments_list.mapToGlobal(position))

    def _delete_comment(self, idx: int):
        """댓글 삭제 및 파일 업데이트."""
        if 0 <= idx < len(self.comments):
            del self.comments[idx]
            self._save_comments()
            self._refresh_comments_display()

    def _on_confirm(self):
        """확인 버튼 클릭 시 코멘트를 JSON 파일로 저장."""
        comment_text = self.comment_input.text().strip()

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

        # 코멘트 추가
        new_comment = {
            "user": self.current_user_id,
            "text": comment_text
        }
        self.comments.append(new_comment)

        # 파일로 저장
        self._save_comments()

        # UI 갱신
        self._refresh_comments_display()

        # 입력창 초기화
        self.comment_input.clear()

    def _save_comments(self):
        """코멘트를 JSON 파일로 저장."""
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
        """코멘트 초기화."""
        self.comments = []
        self.comments_list.clear()
        self.comment_input.clear()

    def get_comment_file_path(self) -> str:
        """현재 이미지의 코멘트 파일 경로 반환."""
        if self.current_image_path:
            return self._get_comment_file_path(self.current_image_path)
        return ""
