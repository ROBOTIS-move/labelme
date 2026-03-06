# -*- coding: utf-8 -*-

import math

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets


class LoadingDialog(QtWidgets.QDialog):

    _SPINNER_SIZE = 40
    _ARC_COUNT = 12
    _TIMER_INTERVAL_MS = 80

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Please wait")
        self.setFixedSize(260, 160)
        self.setModal(True)
        self.setWindowFlags(
            QtCore.Qt.Dialog
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Spinner area
        self._spinner_widget = _SpinnerWidget(
            self._SPINNER_SIZE, self._ARC_COUNT, self
        )
        layout.addWidget(self._spinner_widget, alignment=QtCore.Qt.AlignCenter)

        # Message label
        self._message_label = QtWidgets.QLabel("")
        self._message_label.setAlignment(QtCore.Qt.AlignCenter)
        self._message_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self._message_label)

    def show_message(self, message="Loading..."):
        self._message_label.setText(message)
        self._angle = 0
        self._timer.start(self._TIMER_INTERVAL_MS)
        self.show()
        QtWidgets.QApplication.processEvents()

    def dismiss(self):
        self._timer.stop()
        self.hide()

    def _rotate(self):
        self._angle = (self._angle + 1) % self._ARC_COUNT
        self._spinner_widget.set_angle(self._angle)

    def closeEvent(self, event):
        # Block manual close
        event.ignore()


class _SpinnerWidget(QtWidgets.QWidget):

    def __init__(self, size, arc_count, parent=None):
        super().__init__(parent)
        self._size = size
        self._arc_count = arc_count
        self._angle = 0
        self.setFixedSize(size, size)

    def set_angle(self, angle):
        self._angle = angle
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        center_x = self._size / 2.0
        center_y = self._size / 2.0
        radius = self._size / 2.0 - 4
        dot_radius = 3.0

        for i in range(self._arc_count):
            angle_rad = 2 * math.pi * i / self._arc_count
            x = center_x + radius * math.cos(angle_rad)
            y = center_y + radius * math.sin(angle_rad)

            # Fade: dots closer to current angle are more opaque
            distance = (self._angle - i) % self._arc_count
            opacity = max(0.15, distance / self._arc_count)

            color = QtGui.QColor(80, 80, 80)
            color.setAlphaF(opacity)
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(
                QtCore.QPointF(x, y), dot_radius, dot_radius
            )

        painter.end()
