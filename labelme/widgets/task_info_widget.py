# -*- coding: utf-8 -*-

from qtpy import QtWidgets
from qtpy import QtCore


class TaskInfoWidget(QtWidgets.QWidget):

    # Timer color thresholds (seconds)
    WARNING_THRESHOLD_SECONDS = 6 * 60 * 60  # 6 hours
    CRITICAL_THRESHOLD_SECONDS = 2 * 60 * 60  # 2 hours

    # Display info per mode
    MODE_INFO = {
        "labeling": {"text": "Labeling", "color": "#4CAF50"},  # Green
        "review": {"text": "Review", "color": "#2196F3"},  # Blue
        "final_review": {"text": "Final Review", "color": "#FF9800"},  # Orange
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

        # Batch Position Label (hidden by default)
        self.batch_label = QtWidgets.QLabel("")
        self.batch_label.setAlignment(QtCore.Qt.AlignCenter)
        self.batch_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #FF9800;
                padding: 4px 8px;
            }
        """)
        self.batch_label.setVisible(False)
        layout.addWidget(self.batch_label)

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
        self.remaining_seconds = seconds

        if seconds <= 0:
            self.timer_label.setText("Expired")
            self.timer_label.setToolTip("Task time has expired")
            color = "#F44336"  # Red
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")

            # Determine color
            if seconds <= self.CRITICAL_THRESHOLD_SECONDS:
                color = "#F44336"  # Red
            elif seconds <= self.WARNING_THRESHOLD_SECONDS:
                color = "#FFC107"  # Yellow
            else:
                color = "#4CAF50"  # Green

        self.timer_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {color};
                padding: 4px 8px;
            }}
        """)

    def set_batch_position(self, text):
        self.batch_label.setText(text)
        self.batch_label.setVisible(True)

    def clear_batch_position(self):
        self.batch_label.setText("")
        self.batch_label.setVisible(False)

    def reset(self):
        self.current_mode = None
        self.remaining_seconds = None
        self.clear_batch_position()
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
