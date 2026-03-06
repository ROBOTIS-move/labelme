from qtpy import QtWidgets
from qtpy.QtCore import Qt


class WorkHistoryDialog(QtWidgets.QDialog):
    def __init__(self, account_data, user_id, parent=None):
        super().__init__(parent)
        self.account_data = account_data or {}
        self.user_id = user_id
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(f"Work History - {self.user_id}")
        self.setMinimumSize(500, 450)
        layout = QtWidgets.QVBoxLayout(self)

        if not self.account_data:
            label = QtWidgets.QLabel("No work history")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        else:
            layout.addWidget(self._build_summary_bar())
            layout.addWidget(self._build_tabs())

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _compute_totals(self):
        totals = {"labeling": 0, "review": 0, "finalReview": 0}
        for round_data in self.account_data.values():
            if not isinstance(round_data, dict):
                continue
            for key in totals:
                items = round_data.get(key, [])
                if isinstance(items, list):
                    totals[key] += len(items)
        return totals

    def _build_summary_bar(self):
        totals = self._compute_totals()
        group = QtWidgets.QGroupBox("Summary")
        h = QtWidgets.QHBoxLayout(group)
        h.addWidget(QtWidgets.QLabel(
            f"Labeling: {totals['labeling']}  "
            f"Review: {totals['review']}  "
            f"Final Review: {totals['finalReview']}"
        ))
        return group

    def _build_tabs(self):
        tab_widget = QtWidgets.QTabWidget()
        # Sort round keys numerically
        sorted_keys = sorted(
            self.account_data.keys(),
            key=lambda k: int(k) if str(k).isdigit() else 0,
        )
        for key in sorted_keys:
            round_data = self.account_data[key]
            if not isinstance(round_data, dict):
                continue
            page = self._build_round_page(round_data)
            tab_widget.addTab(page, f"Round {key}")
        return tab_widget

    def _build_round_page(self, round_data):
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)

        for key, title in [
            ("labeling", "Labeling"),
            ("review", "Review"),
            ("finalReview", "Final Review"),
        ]:
            items = round_data.get(key, [])
            if not isinstance(items, list):
                items = []
            layout.addWidget(self._build_section(title, items))

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _build_section(self, title, image_list):
        group = QtWidgets.QGroupBox(f"{title} ({len(image_list)})")
        v = QtWidgets.QVBoxLayout(group)
        list_widget = QtWidgets.QListWidget()
        list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.NoSelection
        )
        if image_list:
            list_widget.addItems(
                [str(item) for item in image_list]
            )
        else:
            list_widget.addItem("(No items)")
        # Auto-size height based on content
        row_h = list_widget.sizeHintForRow(0)
        count = min(list_widget.count(), 8)
        list_widget.setFixedHeight(row_h * count + 4)
        v.addWidget(list_widget)
        return group
