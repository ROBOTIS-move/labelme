# -*- coding: utf-8 -*-
"""
Task Info Widget for Cloud-Native Labelme.
작업 모드 및 잔여 시간을 표시하는 위젯.
"""

from qtpy import QtWidgets
from qtpy import QtCore


class TaskInfoWidget(QtWidgets.QWidget):
    """
    작업 정보 위젯.
    현재 모드와 잔여 시간을 표시.
    """

    # 타이머 색상 기준 (초 단위)
    WARNING_THRESHOLD_SECONDS = 6 * 60 * 60  # 6시간
    CRITICAL_THRESHOLD_SECONDS = 2 * 60 * 60  # 2시간

    # 모드별 표시 정보
    MODE_INFO = {
        "labeling": {"text": "Labeling", "color": "#4CAF50"},  # 초록
        "review": {"text": "Review", "color": "#2196F3"},  # 파랑
        "final_review": {"text": "Final Review", "color": "#FF9800"},  # 주황
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = None
        self.remaining_seconds = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Mode Badge
        self.mode_label = QtWidgets.QLabel("--")
        self.mode_label.setAlignment(QtCore.Qt.AlignCenter)
        self.mode_label.setMinimumWidth(100)
        self.mode_label.setStyleSheet("""
            QLabel {
                background-color: #9E9E9E;
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.mode_label)

        # Timer Label
        self.timer_label = QtWidgets.QLabel("--:--:--")
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        self.timer_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #4CAF50;
                padding: 4px 8px;
            }
        """)
        layout.addWidget(self.timer_label)

        layout.addStretch()

    def set_mode(self, mode: str):
        """현재 모드 설정."""
        self.current_mode = mode
        info = self.MODE_INFO.get(mode, {"text": "Unknown", "color": "#9E9E9E"})
        self.mode_label.setText(info["text"])
        self.mode_label.setStyleSheet(f"""
            QLabel {{
                background-color: {info["color"]};
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)

    def set_remaining_time(self, seconds: int):
        """
        잔여 시간 설정 (초 단위).
        색상 자동 변경: 정상(초록), 6시간 이내(노란색), 2시간 이내(빨간색).
        """
        self.remaining_seconds = seconds

        if seconds <= 0:
            self.timer_label.setText("만료됨")
            color = "#F44336"  # 빨간색
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")

            # 색상 결정
            if seconds <= self.CRITICAL_THRESHOLD_SECONDS:
                color = "#F44336"  # 빨간색
            elif seconds <= self.WARNING_THRESHOLD_SECONDS:
                color = "#FFC107"  # 노란색
            else:
                color = "#4CAF50"  # 초록색

        self.timer_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {color};
                padding: 4px 8px;
            }}
        """)

    def reset(self):
        """위젯 초기화."""
        self.current_mode = None
        self.remaining_seconds = None
        self.mode_label.setText("--")
        self.mode_label.setStyleSheet("""
            QLabel {
                background-color: #9E9E9E;
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.timer_label.setText("--:--:--")
        self.timer_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #4CAF50;
                padding: 4px 8px;
            }
        """)
