# -*- coding: utf-8 -*-

import logging

from qtpy import QtWidgets
from qtpy import QtCore

from labelme.firebase.constants import TaskStatus
from labelme.firebase.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ModeSelectionDialog(QtWidgets.QDialog):

    # Working mode constants
    MODE_LABELING = "labeling"
    MODE_REVIEW = "review"
    MODE_FINAL_REVIEW = "final_review"

    def __init__(self, user_data: dict, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.user_id = user_data.get('email', '')
        self.selected_mode = None
        self.db = DatabaseManager()
        self._counts = {}
        self._init_ui()
        self._load_task_counts()

    def _init_ui(self):
        self.setWindowTitle("Select Working Mode")
        self.setFixedSize(400, 480)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 24, 32, 24)

        # Welcome message
        welcome_label = QtWidgets.QLabel(f"Welcome, {self.user_id}!")
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        welcome_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(welcome_label)

        # Task Overview
        layout.addWidget(self._build_overview_group())

        # Instruction
        instruction_label = QtWidgets.QLabel(
            "Please select your working mode:"
        )
        instruction_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(instruction_label)

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
        self.final_review_btn.setToolTip("Final review mode")
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

    def _build_overview_group(self):
        group = QtWidgets.QGroupBox("Task Overview")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
        """)
        v = QtWidgets.QVBoxLayout(group)
        v.setSpacing(4)

        is_reviewer = (
            self.user_data.get('reviewer', False)
            or self.user_data.get('supervisor', False)
        )
        is_final = (
            self.user_data.get('finalReviewer', False)
            or self.user_data.get('supervisor', False)
        )

        self._count_labels = {}
        rows = [
            ('ready', 'Ready (unassigned)', True),
            ('my_modify', 'My Modify Requests', True),
            ('review_waiting', 'Review Waiting', is_reviewer),
            ('my_rereview', 'My Re-review Waiting', is_reviewer),
            ('final_review', 'Final Review Waiting', is_final),
        ]
        for key, label_text, visible in rows:
            if not visible:
                continue
            row = QtWidgets.QHBoxLayout()
            name_label = QtWidgets.QLabel(label_text)
            name_label.setStyleSheet("font-weight: normal;")
            count_label = QtWidgets.QLabel("...")
            count_label.setAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )
            count_label.setStyleSheet(
                "font-weight: normal; color: #999;"
            )
            count_label.setMinimumWidth(40)
            row.addWidget(name_label)
            row.addWidget(count_label)
            v.addLayout(row)
            self._count_labels[key] = count_label

        return group

    def _load_task_counts(self):
        try:
            all_docs = self.db.get_all_document()
        except Exception as e:
            logger.warning("Failed to load task counts: %s", e)
            return

        if not all_docs:
            self._update_count_labels({})
            return

        counts = {
            'ready': 0,
            'my_modify': 0,
            'review_waiting': 0,
            'my_rereview': 0,
            'final_review': 0,
        }
        is_supervisor = self.user_data.get('supervisor', False)
        is_5_gen = self.user_data.get('5-generation', False)

        for doc in all_docs:
            # Filter by classType (same logic as workers._filter_by_class_type)
            if not is_supervisor:
                class_type = doc.get('classType', '')
                if is_5_gen and class_type != 'FrontViewSegmentation':
                    continue
                if not is_5_gen and class_type == 'FrontViewSegmentation':
                    continue

            status = doc.get('status', '')
            if status == TaskStatus.READY.value:
                counts['ready'] += 1
            elif status == TaskStatus.MODIFY.value:
                if doc.get('workerId') == self.user_id:
                    counts['my_modify'] += 1
            elif status == TaskStatus.REQUEST_REVIEW.value:
                if doc.get('reviewerId', '') == '':
                    counts['review_waiting'] += 1
            elif status == TaskStatus.FINISHED_MODIFY.value:
                if doc.get('reviewerId') == self.user_id:
                    counts['my_rereview'] += 1
            elif status == TaskStatus.REQUEST_FINAL_REVIEW.value:
                counts['final_review'] += 1

        self._update_count_labels(counts)

    def _update_count_labels(self, counts):
        for key, label in self._count_labels.items():
            val = counts.get(key, 0)
            label.setText(str(val))
            if val > 0:
                label.setStyleSheet(
                    "font-weight: bold; color: #333;"
                )
            else:
                label.setStyleSheet(
                    "font-weight: normal; color: #999;"
                )

    def _on_labeling(self):
        self.selected_mode = self.MODE_LABELING
        self.accept()

    def _on_review(self):
        if not (self.user_data.get('reviewer', False)
               or self.user_data.get('supervisor', False)):
            QtWidgets.QMessageBox.warning(
                self,
                "Permission Denied",
                "You do not have reviewer permission.\n"
                "Please contact the administrator."
            )
            return
        self.selected_mode = self.MODE_REVIEW
        self.accept()

    def _on_final_review(self):
        if not (self.user_data.get('finalReviewer', False)
               or self.user_data.get('supervisor', False)):
            QtWidgets.QMessageBox.warning(
                self,
                "Permission Denied",
                "You do not have final reviewer permission.\n"
                "Please contact the administrator."
            )
            return
        self.selected_mode = self.MODE_FINAL_REVIEW
        self.accept()

    def get_selected_mode(self) -> str:
        return self.selected_mode
