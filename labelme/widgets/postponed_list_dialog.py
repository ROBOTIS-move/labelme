
import os
from qtpy import QtWidgets
from qtpy import QtGui


class PostponedListDialog(QtWidgets.QDialog):

    def __init__(self, postpone_dir, user_id, parent=None):
        super(PostponedListDialog, self).__init__(parent)
        self.postpone_dir = postpone_dir
        self.user_id = user_id
        self.selected_image = None

        self.setWindowTitle("Load Postponed Task")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._init_ui()
        self._load_postponed_list()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # Info label
        info_label = QtWidgets.QLabel(
            f"Postponed tasks for user '{self.user_id}':"
        )
        info_label.setToolTip(f"postponed task list for user {self.user_id}")
        layout.addWidget(info_label)

        # List widget
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        load_button = QtWidgets.QPushButton("Load")
        load_button.setToolTip("Load selected task")
        load_button.clicked.connect(self.accept)
        button_layout.addWidget(load_button)

        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _load_postponed_list(self):
        user_postpone_dir = os.path.join(self.postpone_dir, self.user_id)

        if not os.path.exists(user_postpone_dir):
            self.list_widget.addItem("(No postponed tasks)")
            return

        # Filter image files only (get supported formats dynamically)
        image_extensions = [
            f".{fmt.data().decode().lower()}"
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        image_files = []

        for filename in os.listdir(user_postpone_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_extensions:
                image_files.append(filename)

        if not image_files:
            self.list_widget.addItem("(No postponed tasks)")
            return

        # Add to list
        for image_file in sorted(image_files):
            self.list_widget.addItem(image_file)

    def accept(self):
        current_item = self.list_widget.currentItem()
        if current_item and current_item.text() != "(No postponed tasks)":
            self.selected_image = current_item.text()
            super(PostponedListDialog, self).accept()

    def get_selected_image(self):
        return self.selected_image
