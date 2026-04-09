
import os
from qtpy import QtWidgets
from qtpy import QtGui


class PostponedListDialog(QtWidgets.QDialog):

    def __init__(
        self, postpone_dir=None, user_id=None,
        image_names=None, parent=None,
    ):
        super(PostponedListDialog, self).__init__(parent)
        self.postpone_dir = postpone_dir
        self.user_id = user_id
        self.image_names = image_names
        self.selected_image = None

        self.setWindowTitle("Load Postponed Task")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._init_ui()
        if self.image_names is not None:
            self._load_from_list(self.image_names)
        else:
            self._load_postponed_list()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # Info label
        if self.user_id:
            label_text = f"Postponed tasks for user '{self.user_id}':"
        else:
            label_text = "Select a task to restore:"
        info_label = QtWidgets.QLabel(label_text)
        info_label.setToolTip(label_text)
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

    def _load_from_list(self, image_names):
        if not image_names:
            self.list_widget.addItem("(No postponed tasks)")
            return
        for name in sorted(image_names):
            self.list_widget.addItem(name)
        self.list_widget.setCurrentRow(0)

    def accept(self):
        current_item = self.list_widget.currentItem()
        if current_item and current_item.text() != "(No postponed tasks)":
            self.selected_image = current_item.text()
            super(PostponedListDialog, self).accept()

    def get_selected_image(self):
        return self.selected_image
