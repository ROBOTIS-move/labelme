"""Postponed Task List Dialog."""
import os
from qtpy import QtWidgets
from qtpy.QtCore import Qt


class PostponedListDialog(QtWidgets.QDialog):
    """보류된 작업 목록을 표시하고 선택하는 다이얼로그."""

    def __init__(self, postpone_dir, user_id, parent=None):
        super(PostponedListDialog, self).__init__(parent)
        self.postpone_dir = postpone_dir
        self.user_id = user_id
        self.selected_image = None

        self.setWindowTitle("보류된 작업 불러오기")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._init_ui()
        self._load_postponed_list()

    def _init_ui(self):
        """UI 초기화."""
        layout = QtWidgets.QVBoxLayout()

        # 안내 레이블
        info_label = QtWidgets.QLabel(
            f"사용자 '{self.user_id}'의 보류된 작업 목록:"
        )
        layout.addWidget(info_label)

        # 리스트 위젯
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget)

        # 버튼
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        load_button = QtWidgets.QPushButton("불러오기")
        load_button.clicked.connect(self.accept)
        button_layout.addWidget(load_button)

        cancel_button = QtWidgets.QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _load_postponed_list(self):
        """보류된 작업 목록을 로드하여 리스트에 추가."""
        user_postpone_dir = os.path.join(self.postpone_dir, self.user_id)

        if not os.path.exists(user_postpone_dir):
            self.list_widget.addItem("(보류된 작업이 없습니다)")
            return

        # 이미지 파일만 필터링 (jpg, png, jpeg)
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        image_files = []

        for filename in os.listdir(user_postpone_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_extensions:
                image_files.append(filename)

        if not image_files:
            self.list_widget.addItem("(보류된 작업이 없습니다)")
            return

        # 리스트에 추가
        for image_file in sorted(image_files):
            self.list_widget.addItem(image_file)

    def accept(self):
        """선택된 항목 확인."""
        current_item = self.list_widget.currentItem()
        if current_item and current_item.text() != "(보류된 작업이 없습니다)":
            self.selected_image = current_item.text()
            super(PostponedListDialog, self).accept()

    def get_selected_image(self):
        """선택된 이미지 파일명 반환."""
        return self.selected_image
