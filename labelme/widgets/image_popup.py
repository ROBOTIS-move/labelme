#!/usr/bin/env python3
# Copyright 2022 ROBOTIS CO., LTD.
# Authors: Eungi Cho

import io
import os

import PIL.Image
from qtpy import QT_VERSION
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

from labelme import utils


QT5 = QT_VERSION[0] == "5"


class ImagePopup(QtWidgets.QLabel):
    def __init__(self, parent=None, folder_path=None):
        super(ImagePopup, self).__init__(parent)

        self.masked_path = os.path.join(folder_path, 'masked_image')
        self.overlayed_path = os.path.join(folder_path, 'overlayed_image')

        self.popup_state = False

        self.masked_widget = QtWidgets.QLabel()
        self.masked_widget.setWindowTitle("masked image")
        self.masked_widget.setScaledContents(True)

        self.overlayed_widget = QtWidgets.QLabel()
        self.overlayed_widget.setWindowTitle("overlayed image")
        self.overlayed_widget.setScaledContents(True)

    def popUp(self, current_image=None):
        if self.popup_state:
            data_name = os.path.split(current_image)[1][:-3]

            masked_image = os.path.join(self.masked_path, data_name + 'png')
            if os.path.isfile(masked_image):
                mask, (mask_width, mask_height) = self.load_image(masked_image)
                mask = QtGui.QImage.fromData(mask)
                self.masked_widget.setMinimumHeight(mask_height)
                self.masked_widget.setMinimumWidth(mask_width)
                self.masked_widget.setPixmap(QtGui.QPixmap.fromImage(mask))
                self.masked_widget.show()

            overlayed_image = os.path.join(self.overlayed_path, data_name + 'jpg')
            if os.path.isfile(overlayed_image):
                overlay, (overlay_width, overlay_height) = self.load_image(overlayed_image)
                overlay = QtGui.QImage.fromData(overlay)
                self.overlayed_widget.setMinimumHeight(overlay_height)
                self.overlayed_widget.setMinimumWidth(overlay_width)
                self.overlayed_widget.setPixmap(QtGui.QPixmap.fromImage(overlay))
                self.overlayed_widget.show()

    def load_image(self, file_path):
        try:
            image_pil = PIL.Image.open(file_path)
        except IOError:
            print("Failed opening image file: {}".format(file_path))
            return

        # apply orientation to image according to exif
        image_pil = utils.apply_exif_orientation(image_pil)

        with io.BytesIO() as f:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".jpg", ".jpeg"]:
                format = "JPEG"
            else:
                format = "PNG"
            image_pil.save(f, format=format)
            f.seek(0)
            return f.read(), image_pil.size
