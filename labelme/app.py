# -*- coding: utf-8 -*-

import functools
import json
import math
import os
import os.path as osp
import re
import webbrowser
import datetime
import glob
import shutil

import imgviz
import natsort
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy import QtWidgets

from labelme import __appname__
from labelme import PY2

from . import utils
from labelme.config import get_config
from labelme.cli import draw_object_label
from labelme.cli import draw_segment_label
from labelme.cli import crop_label_class
from labelme.label_file import LabelFile
from labelme.label_file import LabelFileError
from labelme.logger import logger
from labelme.shape import Shape
from labelme.widgets import BrightnessContrastDialog
from labelme.widgets import Canvas
from labelme.widgets import ConvertLabelPopup
from labelme.widgets import FileDialogPreview
from labelme.widgets import ImagePopup
from labelme.widgets import LabelDialog
from labelme.widgets import LabelListWidget
from labelme.widgets import LabelListWidgetItem
from labelme.widgets import ToolBar
from labelme.widgets import UniqueLabelQListWidget
from labelme.widgets import ZoomWidget
from labelme.widgets import WorkerNameWindow
from labelme.widgets import InvalidVersionWindow
from labelme.widgets import LoginDialog
from labelme.widgets import ModeSelectionDialog
from labelme.widgets import CommentWidget
from labelme.widgets import DiscardDialog
from labelme.widgets import TaskInfoWidget
from labelme.widgets import PostponedListDialog
from labelme.utils.encrypt_cache import EncryptCache
from labelme.firebase.constants import (
    TaskStatus,
    StoragePath,
    STATUS_TRANSITIONS,
    USER_FIELD_MAP,
)
from labelme.firebase.database_manager import DatabaseManager
from labelme.firebase.image_manager import ImageUpload, ImageDownload
from labelme.firebase.workers import (
    LoadTaskWorker,
    SubmitTaskWorker,
    PostponeTaskWorker,
    LoadPostponeWorker,
    RestorePostponeWorker,
    DropTaskWorker,
    DiscardTaskWorker,
    ReadyGtWorker,
)

# FIXME
# - [medium] Set max zoom value to something big enough for FitWidth/Window

# TODO(unknown):
# - Zoom is too "steppy".


LABEL_COLORMAP = imgviz.label_colormap()


class MainWindow(QtWidgets.QMainWindow):

    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2

    def __init__(
        self,
        config=None,
        filename=None,
        output=None,
        output_file=None,
        output_dir=None,
    ):
        version_checker = utils.VersionChecker()
        version_checker.check_version()
        if not version_checker.internet_status:
            version_popup = InvalidVersionWindow(
                0,
                version_checker.local_version,
                version_checker.github_version)
            version_popup.setModal(True)
            version_popup.exec_()
        if not version_checker.version_result:
            version_popup = InvalidVersionWindow(
                1,
                version_checker.local_version,
                version_checker.github_version)
            version_popup.setModal(True)
            version_popup.exec_()
        self._last_label_names = []
        if output is not None:
            logger.warning(
                "argument output is deprecated, use output_file instead"
            )
            if output_file is None:
                output_file = output

        # see labelme/config/default_config.yaml for valid configuration
        if config is None:
            config = get_config()
        self._config = config

        # set default shape colors
        Shape.line_color = QtGui.QColor(*self._config["shape"]["line_color"])
        Shape.fill_color = QtGui.QColor(*self._config["shape"]["fill_color"])
        Shape.select_line_color = QtGui.QColor(
            *self._config["shape"]["select_line_color"]
        )
        Shape.select_fill_color = QtGui.QColor(
            *self._config["shape"]["select_fill_color"]
        )
        Shape.vertex_fill_color = QtGui.QColor(
            *self._config["shape"]["vertex_fill_color"]
        )
        Shape.hvertex_fill_color = QtGui.QColor(
            *self._config["shape"]["hvertex_fill_color"]
        )

        # Set point size from config file
        Shape.point_size = self._config["shape"]["point_size"]

        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        # Whether we need to save or not.
        self.dirty = False

        self._noSelectionSlot = False

        self._copied_shapes = None

        self._last_label = None
        self._prev_brightness_contrast = (None, None)

        # Main widgets and related state.
        self.labelDialog = LabelDialog(
            parent=self,
            labels=self._config["labels"],
            sort_labels=self._config["sort_labels"],
            show_text_field=self._config["show_label_text_field"],
            completion=self._config["label_completion"],
            fit_to_content=self._config["fit_to_content"],
            flags=self._config["label_flags"],
        )

        self.labelList = LabelListWidget()
        self.lastOpenDir = None

        self.flag_dock = self.flag_widget = None
        self.flag_dock = QtWidgets.QDockWidget(self.tr("Flags"), self)
        self.flag_dock.setObjectName("Flags")
        self.flag_widget = QtWidgets.QListWidget()
        self.flag_dock.setWidget(self.flag_widget)

        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList.itemDoubleClicked.connect(self.editLabel)
        self.labelList.itemChanged.connect(self.labelItemChanged)
        self.labelList.itemDropped.connect(self.labelOrderChanged)
        self.shape_dock = QtWidgets.QDockWidget(
            self.tr("Polygon Labels"), self
        )
        self.shape_dock.setObjectName("Labels")
        self.shape_dock.setWidget(self.labelList)

        self.uniqLabelList = UniqueLabelQListWidget()
        self.uniqLabelList.setToolTip(
            self.tr(
                "Select label to start annotating for it. "
                "Press 'Esc' to deselect."
            )
        )
        if self._config["labels"]:
            for label in self._config["labels"]:
                item = self.uniqLabelList.createItemFromLabel(label)
                self.uniqLabelList.addItem(item)
                rgb = self._get_rgb_by_label(label)
                self.uniqLabelList.setItemLabel(item, label, rgb)
        self.label_dock = QtWidgets.QDockWidget(self.tr("Label List"), self)
        self.label_dock.setObjectName("Label List")
        self.label_dock.setWidget(self.uniqLabelList)

        self.fileSearch = QtWidgets.QLineEdit()
        self.fileSearch.setPlaceholderText(self.tr("Search Filename"))
        self.fileSearch.textChanged.connect(self.fileSearchChanged)
        self.fileListWidget = QtWidgets.QListWidget()
        self.fileListWidget.itemSelectionChanged.connect(
            self.fileSelectionChanged
        )
        fileListLayout = QtWidgets.QVBoxLayout()
        fileListLayout.setContentsMargins(0, 0, 0, 0)
        fileListLayout.setSpacing(0)
        fileListLayout.addWidget(self.fileSearch)
        fileListLayout.addWidget(self.fileListWidget)
        self.file_dock = QtWidgets.QDockWidget(self.tr("File List"), self)
        self.file_dock.setObjectName("Files")
        fileListWidget = QtWidgets.QWidget()
        fileListWidget.setLayout(fileListLayout)
        self.file_dock.setWidget(fileListWidget)

        self.zoomWidget = ZoomWidget()
        self.setAcceptDrops(True)

        self.canvas = self.labelList.canvas = Canvas(
            epsilon=self._config["epsilon"],
            double_click=self._config["canvas"]["double_click"],
            num_backups=self._config["canvas"]["num_backups"],
        )
        self.canvas.zoomRequest.connect(self.zoomRequest)

        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidget(self.canvas)
        scrollArea.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scrollArea.verticalScrollBar(),
            Qt.Horizontal: scrollArea.horizontalScrollBar(),
        }
        self.canvas.scrollRequest.connect(self.scrollRequest)

        # save edit state
        self.current_edit_shape = None

        self.canvas.newShape.connect(self.newShape)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)

        self.setCentralWidget(scrollArea)

        # Cloud-Native Mode: Flags and User Info
        self.is_cloud_native_mode = False  # Changed to True upon successful login
        self.current_user_id = None
        self.current_mode = None  # 'labeling', 'review', 'final_review'

        # Firebase integration
        self.db_manager = DatabaseManager()
        self.image_uploader = ImageUpload()
        self.image_downloader = ImageDownload()
        self.current_doc_id = None
        self.current_task_status = None
        self.current_document = None
        self._active_worker = None

        # Cloud-Native: Work directory setup (Improved to be configurable)
        # TODO: Improve to allow user to configure path via QSettings
        default_work_dir = os.path.join(os.path.expanduser("~"), ".labelme", "cloud_tasks")
        self.work_base_dir = os.environ.get("LABELME_WORK_DIR", default_work_dir)
        self.processing_dir = os.path.join(self.work_base_dir, "processing")
        self.postpone_dir = os.path.join(self.work_base_dir, "postpone")

        # Create directories (Warn on failure)
        try:
            os.makedirs(self.processing_dir, exist_ok=True)
            os.makedirs(self.postpone_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create work directories: {e}")


        # Cloud-Native: Timer related variables
        self.deadline = None  # datetime object
        self.deadline_timer = QtCore.QTimer(self)
        self.deadline_timer.timeout.connect(self._updateDeadlineTimer)

        # Comment Dock (Displayed only in Review/Final Review modes)
        self.comment_widget = CommentWidget(self)
        self.comment_dock = QtWidgets.QDockWidget(self.tr("Comments"), self)
        self.comment_dock.setObjectName("Comments")
        self.comment_dock.setWidget(self.comment_widget)

        # Task Info Dock (Mode badge + Timer, Fixed at top)
        self.task_info_widget = TaskInfoWidget(self)
        self.task_info_dock = QtWidgets.QDockWidget(self.tr("Task Info"), self)
        self.task_info_dock.setObjectName("TaskInfo")
        self.task_info_dock.setWidget(self.task_info_widget)
        self.task_info_dock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)

        features = QtWidgets.QDockWidget.DockWidgetFeatures()
        for dock in ["flag_dock", "label_dock", "shape_dock", "file_dock"]:
            if self._config[dock]["closable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetClosable
            if self._config[dock]["floatable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetFloatable
            if self._config[dock]["movable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetMovable
            getattr(self, dock).setFeatures(features)
            if self._config[dock]["show"] is False:
                getattr(self, dock).setVisible(False)

        # Dock Layout: TaskInfo at the very top, other Docks below
        self.addDockWidget(Qt.RightDockWidgetArea, self.task_info_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.flag_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.label_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.shape_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.comment_dock)

        # Cloud-Native Mode: Hide unnecessary Docks by default (Flags, Label List, File List)
        # Display only shape_dock (Polygon Labels) and comment_dock, task_info_dock is always displayed
        self.flag_dock.setVisible(False)
        self.label_dock.setVisible(False)
        self.file_dock.setVisible(False)
        self.comment_dock.setVisible(False)  # Initially hidden, displayed depending on mode
        self.task_info_dock.setVisible(True)  # Always displayed

        # Encrypt Cache
        self.encrypt = EncryptCache()

        # Actions
        action = functools.partial(utils.newAction, self)
        shortcuts = self._config["shortcuts"]
        quit = action(
            self.tr("&Quit"),
            self.close,
            shortcuts["quit"],
            "quit",
            self.tr("Quit application"),
        )
        open_ = action(
            self.tr("&Open"),
            self.openFile,
            shortcuts["open"],
            "open",
            self.tr("Open image or label file"),
        )
        opendir = action(
            self.tr("&Open Dir"),
            self.openDirDialog,
            shortcuts["open_dir"],
            "open",
            self.tr("Open Dir"),
        )
        openNextImg = action(
            self.tr("&Next Image"),
            self.openNextImg,
            shortcuts["open_next"],
            "next",
            self.tr("Open next (hold Ctl+Shift to copy labels)"),
            enabled=False,
        )
        openPrevImg = action(
            self.tr("&Prev Image"),
            self.openPrevImg,
            shortcuts["open_prev"],
            "prev",
            self.tr("Open prev (hold Ctl+Shift to copy labels)"),
            enabled=False,
        )
        save = action(
            self.tr("&Save"),
            self.saveFile,
            shortcuts["save"],
            "save",
            self.tr("Save labels to file"),
            enabled=False,
        )
        saveAs = action(
            self.tr("&Save As"),
            self.saveFileAs,
            shortcuts["save_as"],
            "save-as",
            self.tr("Save labels to a different file"),
            enabled=False,
        )

        deleteFile = action(
            self.tr("&Delete File"),
            self.deleteFile,
            shortcuts["delete_file"],
            "delete",
            self.tr("Delete current label file"),
            enabled=False,
        )

        changeOutputDir = action(
            self.tr("&Change Output Dir"),
            slot=self.changeOutputDirDialog,
            shortcut=shortcuts["save_to"],
            icon="open",
            tip=self.tr("Change where annotations are loaded/saved"),
        )

        saveAuto = action(
            self.tr("Save &Automatically"),
            self.toggleAutoSaveMode,
            icon=None,
            tip=self.tr("Save automatically"),
            checkable=True,
            enabled=True,
        )
        saveAuto.setChecked(self._config["auto_save"])

        saveWithImageData = action(
            text="Save With Image Data",
            slot=self.enableSaveImageWithData,
            tip="Save image data in label file",
            checkable=True,
            checked=self._config["store_data"],
        )

        close = action(
            "&Close",
            self.closeFile,
            shortcuts["close"],
            "close",
            "Close current file",
        )

        toggle_keep_prev_mode = action(
            self.tr("Keep Previous Annotation"),
            self.toggleKeepPrevMode,
            shortcuts["toggle_keep_prev_mode"],
            None,
            self.tr('Toggle "keep pevious annotation" mode'),
            checkable=True,
        )
        toggle_keep_prev_mode.setChecked(self._config["keep_prev"])

        add_point_mode = action(
            self.tr("Add Points to Edge"),
            self.toggleAddPointMode,
            shortcuts["toggle_add_points_mode"],
            None,
            self.tr('Toggle "add point to edge" mode'),
            checkable=True,
        )
        add_point_mode.setChecked(self._config["add_point"])

        single_class_mode = action(
            self.tr("Single class mode"),
            self.toggleSingleClassMode,
            shortcuts["single_class_mode"],
            None,
            self.tr('Toggle "single class" mode'),
            checkable=True,
        )
        single_class_mode.setChecked(self._config["single_class"])

        keep_brightness_contrast = action(
            self.tr("Keep brightness and contrast"),
            self.toggleKeepBrightnessContrast,
            shortcuts["keep_brightness_contrast"],
            None,
            self.tr('Toggle "keep brightness and contrast"'),
            checkable=True,
        )
        keep_brightness_contrast.setChecked(
            self._config["keep_prev_brightness"] and self._config["keep_prev_contrast"])

        self.display_label_option = action(
            self.tr("Display label name"),
            self.togglePaintLabelsOption,
            shortcuts["display_label_name"],
            None,
            self.tr('Toggle "display label name" mode'),
            checkable=True,
        )
        self.display_label_option.setChecked(self._config["display_label_option"])

        self.display_probability_option = action(
            self.tr("Display label probability"),
            self.togglePaintProbabilityOption,
            None,
            None,
            self.tr('Toggle "display label probability" mode'),
            checkable=True,
        )
        self.display_probability_option.setChecked(self._config["display_probability_option"])

        createMode = action(
            self.tr("Create Polygons"),
            lambda: self.toggleDrawMode(False, createMode="polygon"),
            shortcuts["create_polygon"],
            "objects",
            self.tr("Start drawing polygons"),
            enabled=False,
        )
        createRectangleMode = action(
            self.tr("Create Rectangle"),
            lambda: self.toggleDrawMode(False, createMode="rectangle"),
            shortcuts["create_rectangle"],
            "objects",
            self.tr("Start drawing rectangles"),
            enabled=False,
        )
        createCircleMode = action(
            self.tr("Create Circle"),
            lambda: self.toggleDrawMode(False, createMode="circle"),
            shortcuts["create_circle"],
            "objects",
            self.tr("Start drawing circles"),
            enabled=False,
        )
        createLineMode = action(
            self.tr("Create Line"),
            lambda: self.toggleDrawMode(False, createMode="line"),
            shortcuts["create_line"],
            "objects",
            self.tr("Start drawing lines"),
            enabled=False,
        )
        createPointMode = action(
            self.tr("Create Point"),
            lambda: self.toggleDrawMode(False, createMode="point"),
            shortcuts["create_point"],
            "objects",
            self.tr("Start drawing points"),
            enabled=False,
        )
        createLineStripMode = action(
            self.tr("Create LineStrip"),
            lambda: self.toggleDrawMode(False, createMode="linestrip"),
            shortcuts["create_linestrip"],
            "objects",
            self.tr("Start drawing linestrip. Ctrl+LeftClick ends creation."),
            enabled=False,
        )
        editMode = action(
            self.tr("Edit Polygons"),
            self.setEditMode,
            shortcuts["edit_polygon"],
            "edit",
            self.tr("Move and edit the selected polygons"),
            enabled=False,
        )

        delete_popup = action(
            self.tr("Enable popup to confirm polygon deletion"),
            self.toggle_delete_popup,
            shortcuts["delete_popup"],
            None,
            self.tr('Toggle "delete_popup"'),
            checkable=True,
        )
        delete_popup.setChecked(self._config["delete_popup"])

        delete = action(
            self.tr("Delete Polygons"),
            self.deleteSelectedShape,
            shortcuts["delete_polygon"],
            "cancel",
            self.tr("Delete the selected polygons"),
            enabled=False,
        )
        duplicate = action(
            self.tr("Duplicate Polygons"),
            self.duplicateSelectedShape,
            shortcuts["duplicate_polygon"],
            "copy",
            self.tr("Create a duplicate of the selected polygons"),
            enabled=False,
        )
        copy = action(
            self.tr("Copy Polygons"),
            self.copySelectedShape,
            shortcuts["copy_polygon"],
            "copy",
            self.tr("Copy selected polygons to clipboard"),
            enabled=False,
        )
        paste = action(
            self.tr("Paste Polygons"),
            self.pasteSelectedShape,
            shortcuts["paste_polygon"],
            "copy",
            self.tr("Paste copied polygons"),
            enabled=False,
        )
        undoLastPoint = action(
            self.tr("Undo last point"),
            self.canvas.undoLastPoint,
            shortcuts["undo_last_point"],
            "undo",
            self.tr("Undo last drawn point"),
            enabled=False,
        )
        removePoint = action(
            text="Remove Selected Point",
            slot=self.removeSelectedPoint,
            shortcut=shortcuts["remove_selected_point"],
            icon="edit",
            tip="Remove selected point from polygon",
            enabled=False,
        )

        redo = action(
            self.tr("Redo"),
            self.redoShapeEdit,
            shortcuts["redo"],
            "redo",
            self.tr("Redo last add and edit of shape"),
            enabled=False,
        )
        undo = action(
            self.tr("Undo"),
            self.undoShapeEdit,
            shortcuts["undo"],
            "undo",
            self.tr("Undo last add and edit of shape"),
            enabled=False,
        )

        hideAll = action(
            self.tr("&Hide\nAll"),
            functools.partial(self.togglePolygons, False),
            shortcuts["hide_all"],
            icon="eye",
            tip=self.tr("Hide all polygons"),
            enabled=False,
        )
        showAll = action(
            self.tr("&Show\nAll"),
            functools.partial(self.togglePolygons, True),
            shortcuts["show_all"],
            icon="eye",
            tip=self.tr("Show all polygons"),
            enabled=False,
        )
        self.hide_polygon_flag = False
        hidePolygons = action(
            self.tr("&Hide\nPolygons"),
            lambda: self.toggleHideFlagAndToggleShapes('polygon'),
            shortcuts['hide_and_show_polygons'],
            tip=self.tr("Hide polygons"),
            enabled=False,
        )
        self.hide_rectangle_flag = False
        hideRectangles = action(
            self.tr("&Hide\nRectangles"),
            lambda: self.toggleHideFlagAndToggleShapes('rectangle'),
            shortcuts['hide_and_show_rectangles'],
            tip=self.tr("Hide rectangles"),
            enabled=False,
        )
        help = action(
            self.tr("&Tutorial"),
            self.tutorial,
            icon="help",
            tip=self.tr("Show tutorial page"),
        )

        administrator = action(
            self.tr("&Check\nLabels"),
            self.check_labels,
            shortcuts["check_labels"],
            icon="eye",
            tip=self.tr("Check labels"),
            enabled=False,
        )

        crop_classes = action(
            self.tr("Crop Classes"),
            self.crop_classes,
            shortcuts["crop_classes"],
            icon="eye",
            tip=self.tr("Crop classes"),
            enabled=False,
        )

        delete_label_folder = action(
            self.tr("Delete Label Folder"),
            self.delete_label_dir,
            tip=self.tr("Delete label folder"),
            enabled=False,
        )

        convert_segmentation = action(
            self.tr("Convert\nSegmentation"),
            self.convert_segments,
            icon="eye",
            tip=self.tr("Convert segmentation"),
            enabled=False,
        )

        convert_objects = action(
            self.tr("Convert\nObjects"),
            self.convert_bounding_boxes,
            icon="eye",
            tip=self.tr("Convert bounding boxes"),
            enabled=False,
        )

        self.measure_cursor_flag = False
        self.cross_cursor = self.make_cross_cursor()
        self.canvas.cross_cursor = self.cross_cursor
        measure_cursor = action(
            self.tr("Measure Cursor"),
            self.measure_cursor,
            shortcuts["measure_cursor"],
            icon="measure",
            tip=self.tr("Measure distance with cursor"),
            enabled=True,
        )

        # ============ Cloud-Native Actions ============
        loadTask = action(
            self.tr("Load Task"),
            self.loadTaskAction,
            None,
            "open",
            self.tr("Load a task from cloud"),
            enabled=True,
        )

        loadModifyTask = action(
            self.tr("Load Modify"),
            self.loadModifyTaskAction,
            None,
            "open",
            self.tr("Load a task that needs modification"),
            enabled=True,
        )

        loadPostponeTask = action(
            self.tr("Load Postpone"),
            self.loadPostponeTaskAction,
            None,
            "undo",
            self.tr("Load a postponed task"),
            enabled=True,
        )

        loadReadyGtTask = action(
            self.tr("Load Ready GT"),
            self.loadReadyGtTaskAction,
            None,
            "open",
            self.tr("Load a ready GT task for final processing"),
            enabled=True,
        )

        submitTask = action(
            self.tr("Submit"),
            self.submitTaskAction,
            None,
            "save",
            self.tr("Submit current task"),
            enabled=False,
        )

        postponeTask = action(
            self.tr("Postpone"),
            self.postponeTaskAction,
            None,
            None,
            self.tr("Postpone current task"),
            enabled=False,
        )

        dropTask = action(
            self.tr("Drop Task"),
            self.dropTaskAction,
            None,
            None,
            self.tr("Drop current task and return to pool"),
            enabled=False,
        )

        discardTask = action(
            self.tr("Discard Task"),
            self.discardTaskAction,
            None,
            "cancel",
            self.tr("Discard current task with reason"),
            enabled=False,
        )
        # ============ End Cloud-Native Actions ============

        zoom = QtWidgets.QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            str(
                self.tr(
                    "Zoom in or out of the image. Also accessible with "
                    "{} and {} from the canvas."
                )
            ).format(
                utils.fmtShortcut(
                    "{},{}".format(shortcuts["zoom_in"], shortcuts["zoom_out"])
                ),
                utils.fmtShortcut(self.tr("Ctrl+Wheel")),
            )
        )
        self.zoomWidget.setEnabled(False)

        zoomIn = action(
            self.tr("Zoom &In"),
            functools.partial(self.addZoom, 1.1),
            shortcuts["zoom_in"],
            "zoom-in",
            self.tr("Increase zoom level"),
            enabled=False,
        )
        zoomOut = action(
            self.tr("&Zoom Out"),
            functools.partial(self.addZoom, 0.9),
            shortcuts["zoom_out"],
            "zoom-out",
            self.tr("Decrease zoom level"),
            enabled=False,
        )
        zoomOrg = action(
            self.tr("&Original size"),
            functools.partial(self.setZoom, 100),
            shortcuts["zoom_to_original"],
            "zoom",
            self.tr("Zoom to original size"),
            enabled=False,
        )
        keepPrevScale = action(
            self.tr("&Keep Previous Scale"),
            self.enableKeepPrevScale,
            tip=self.tr("Keep previous zoom scale"),
            checkable=True,
            checked=self._config["keep_prev_scale"],
            enabled=True,
        )
        fitWindow = action(
            self.tr("&Fit Window"),
            self.setFitWindow,
            shortcuts["fit_window"],
            "fit-window",
            self.tr("Zoom follows window size"),
            checkable=True,
            enabled=False,
        )
        fitWidth = action(
            self.tr("Fit &Width"),
            self.setFitWidth,
            shortcuts["fit_width"],
            "fit-width",
            self.tr("Zoom follows window width"),
            checkable=True,
            enabled=False,
        )
        brightnessContrast = action(
            "&Brightness Contrast",
            self.brightnessContrast,
            shortcuts["set_brightness_contrast"],
            "color",
            "Adjust brightness and contrast",
            enabled=False,
        )
        prevBrightnessContrast = action(
            "&Previous Brightness Contrast",
            self.prevBrightnessContrast,
            shortcuts["set_prev_brightness_contrast"],
            "color",
            "Adjust brightness and contrast",
            enabled=False,
        )
        # Group zoom controls into a list for easier toggling.
        zoomActions = (
            self.zoomWidget,
            zoomIn,
            zoomOut,
            zoomOrg,
            fitWindow,
            fitWidth,
        )
        self.zoomMode = self.FIT_WINDOW
        fitWindow.setChecked(Qt.Checked)
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action(
            self.tr("&Edit Label"),
            self.editLabel,
            shortcuts["edit_label"],
            "edit",
            self.tr("Modify the label of the selected polygon"),
            enabled=False,
        )

        edit_label_name = action(
            self.tr("&Edit Label Name"),
            self.editLabel,
            shortcuts["edit_label_name"],
            "edit",
            self.tr("Modify the label name of the selected polygon"),
            enabled=False,
        )

        fill_drawing = action(
            self.tr("Fill Drawing Polygon"),
            self.canvas.setFillDrawing,
            None,
            "color",
            self.tr("Fill polygon while drawing"),
            checkable=True,
            enabled=True,
        )
        fill_drawing.trigger()

        # Lavel list context menu.
        labelMenu = QtWidgets.QMenu()
        utils.addActions(labelMenu, (edit, delete))
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(
            self.popLabelListMenu
        )

        # Store actions for further handling.
        self.actions = utils.struct(
            saveAuto=saveAuto,
            saveWithImageData=saveWithImageData,
            changeOutputDir=changeOutputDir,
            save=save,
            saveAs=saveAs,
            open=open_,
            close=close,
            deleteFile=deleteFile,
            toggleKeepPrevMode=toggle_keep_prev_mode,
            add_point_mode=add_point_mode,
            single_class_mode=single_class_mode,
            keep_brightness_contrast=keep_brightness_contrast,
            delete=delete,
            edit=edit,
            duplicate=duplicate,
            copy=copy,
            paste=paste,
            undoLastPoint=undoLastPoint,
            redo=redo,
            undo=undo,
            removePoint=removePoint,
            createMode=createMode,
            editMode=editMode,
            edit_label_name=edit_label_name,
            createRectangleMode=createRectangleMode,
            createCircleMode=createCircleMode,
            createLineMode=createLineMode,
            createPointMode=createPointMode,
            createLineStripMode=createLineStripMode,
            zoom=zoom,
            zoomIn=zoomIn,
            zoomOut=zoomOut,
            zoomOrg=zoomOrg,
            keepPrevScale=keepPrevScale,
            fitWindow=fitWindow,
            fitWidth=fitWidth,
            brightnessContrast=brightnessContrast,
            prevBrightnessContrast=prevBrightnessContrast,
            zoomActions=zoomActions,
            openNextImg=openNextImg,
            openPrevImg=openPrevImg,
            fileMenuActions=(open_, opendir, save, saveAs, close, quit),
            # Cloud-Native Actions
            loadTask=loadTask,
            loadModifyTask=loadModifyTask,
            loadPostponeTask=loadPostponeTask,
            loadReadyGtTask=loadReadyGtTask,
            submitTask=submitTask,
            postponeTask=postponeTask,
            dropTask=dropTask,
            discardTask=discardTask,
            tool=(),
            # XXX: need to add some actions here to activate the shortcut
            editMenu=(
                edit,
                edit_label_name,
                duplicate,
                delete,
                None,
                redo,
                undo,
                undoLastPoint,
                None,
                removePoint,
                None,
                delete_popup,
                toggle_keep_prev_mode,
                add_point_mode,
                single_class_mode,
            ),
            # menu shown at right click
            menu=(
                createMode,
                createRectangleMode,
                createCircleMode,
                createLineMode,
                createPointMode,
                createLineStripMode,
                editMode,
                edit,
                duplicate,
                copy,
                paste,
                delete,
                redo,
                undo,
                undoLastPoint,
                removePoint,
            ),
            onLoadActive=(
                close,
                createMode,
                createRectangleMode,
                editMode,
                brightnessContrast,
                prevBrightnessContrast,
            ),
            onLoadSegmentationActive=(
                close,
                createMode,
                editMode,
                convert_segmentation,
            ),
            onLoadObject2dActive=(
                close,
                createRectangleMode,
                editMode,
                convert_objects,
            ),
            onShapesPresent=(saveAs, hideAll, showAll, hidePolygons, hideRectangles),
            onAdministrator=(
                administrator,
                crop_classes,
                delete_label_folder,
                measure_cursor,
            ),
        )

        self.canvas.vertexSelected.connect(self.actions.removePoint.setEnabled)

        self.menus = utils.struct(
            file=self.menu(self.tr("&File")),
            edit=self.menu(self.tr("&Edit")),
            view=self.menu(self.tr("&View")),
            help=self.menu(self.tr("&Help")),
            administrator=self.menu(self.tr("&Administrator")),
            mode=self.menu(self.tr("&Mode")),  # Cloud-Native: Add Mode menu
            recentFiles=QtWidgets.QMenu(self.tr("Open &Recent")),
            labelList=labelMenu,
        )

        utils.addActions(
            self.menus.file,
            (
                # Cloud-Native Actions (Main Menu)
                loadTask,
                loadModifyTask,
                loadPostponeTask,
                loadReadyGtTask,
                submitTask,
                postponeTask,
                dropTask,
                discardTask,
                None,
                # Existing actions (Hidden but kept for shortcuts)
                # open_,
                # openNextImg,
                # openPrevImg,
                # opendir,
                # self.menus.recentFiles,
                save,
                saveAs,
                saveAuto,
                changeOutputDir,
                saveWithImageData,
                close,
                deleteFile,
                None,
                quit,
            ),
        )
        utils.addActions(self.menus.help, (help,))
        utils.addActions(
            self.menus.administrator,
            (
                administrator,
                None,
                convert_segmentation,
                convert_objects,
                crop_classes,
                delete_label_folder,
                measure_cursor,
            )
        )

        # Cloud-Native: Add Change action to Mode menu
        changeModeAction = action(
            self.tr("&Change Mode"),
            self.changeModeAction,
            None,
            None,
            self.tr("Change work mode (only when no image is loaded)"),
            enabled=True,
        )
        utils.addActions(self.menus.mode, (changeModeAction,))
        utils.addActions(
            self.menus.view,
            (
                self.flag_dock.toggleViewAction(),
                self.label_dock.toggleViewAction(),
                self.shape_dock.toggleViewAction(),
                self.file_dock.toggleViewAction(),
                self.comment_dock.toggleViewAction(),
                self.display_label_option,
                self.display_probability_option,
                None,
                fill_drawing,
                None,
                hideAll,
                showAll,
                hidePolygons,
                hideRectangles,
                None,
                zoomIn,
                zoomOut,
                zoomOrg,
                keepPrevScale,
                None,
                fitWindow,
                fitWidth,
                None,
                brightnessContrast,
                keep_brightness_contrast,
                prevBrightnessContrast,
            ),
        )

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        utils.addActions(self.canvas.menus[0], self.actions.menu)
        utils.addActions(
            self.canvas.menus[1],
            (
                action("&Copy here", self.copyShape),
                action("&Move here", self.moveShape),
            ),
        )

        self.tools = self.toolbar("Tools")
        # Menu buttons on Left (Cloud-Native version)
        self.actions.tool = (
            loadTask,
            loadModifyTask,
            loadPostponeTask,
            loadReadyGtTask,
            submitTask,
            None,
            createMode,
            createRectangleMode,
            editMode,
            duplicate,
            copy,
            paste,
            delete,
            redo,
            undo,
            brightnessContrast,
            None,
            postponeTask,
            discardTask,
            None,
            hideAll,
            showAll,
            None,
            zoom,
            fitWidth,
        )

        # Removed status bar timer label - Replaced by TaskInfoWidget

        self.statusBar().showMessage(str(self.tr("%s started.")) % __appname__)
        self.statusBar().show()

        if output_file is not None and self._config["auto_save"]:
            logger.warn(
                "If `auto_save` argument is True, `output_file` argument "
                "is ignored and output filename is automatically "
                "set as IMAGE_BASENAME.json."
            )
        self.output_file = output_file
        self.output_dir = output_dir

        # Application state.
        self.image = QtGui.QImage()
        self.imagePath = None
        self.recentFiles = []
        self.maxRecent = 7
        self.otherData = None
        self.zoom_level = 100
        self.fit_window = False
        self.zoom_values = {}  # key=filename, value=(zoom_mode, zoom_value)
        self.brightnessContrast_values = {}
        self.scroll_values = {
            Qt.Horizontal: {},
            Qt.Vertical: {},
        }  # key=filename, value=scroll_value

        if filename is not None and osp.isdir(filename):
            self.importDirImages(filename, load=False)
        else:
            self.filename = filename

        if config["file_search"]:
            self.fileSearch.setText(config["file_search"])
            self.fileSearchChanged()

        # XXX: Could be completely declarative.
        # Restore application settings.
        self.settings = QtCore.QSettings("labelme", "labelme")
        self.recentFiles = self.settings.value("recentFiles", []) or []
        size = self.settings.value("window/size", QtCore.QSize(600, 500))
        position = self.settings.value("window/position", QtCore.QPoint(0, 0))
        state = self.settings.value("window/state", QtCore.QByteArray())
        self.resize(size)
        self.move(position)
        # or simply:
        # self.restoreGeometry(settings['window/geometry']
        self.restoreState(state)

        # Populate the File menu dynamically.
        self.updateFileMenu()
        # Since loading the file may take some time,
        # make sure it runs in the background.
        if self.filename is not None:
            self.queueEvent(functools.partial(self.loadFile, self.filename))

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

        # ============ Cloud-Native Startup Logic ============
        # Run login and mode selection dialog at app startup
        # Must be run before self.show()
        QtCore.QTimer.singleShot(100, self._showStartupDialogs)

        # self.firstStart = True
        # if self.firstStart:
        #    QWhatsThis.enterWhatsThisMode()

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            utils.addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName("%sToolBar" % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            utils.addActions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar

    # Support Functions

    def noShapes(self):
        return not len(self.labelList)

    def populateModeActions(self):
        tool, menu = self.actions.tool, self.actions.menu
        self.tools.clear()
        utils.addActions(self.tools, tool)
        self.canvas.menus[0].clear()
        utils.addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (
            self.actions.createMode,
            self.actions.createRectangleMode,
            self.actions.createCircleMode,
            self.actions.createLineMode,
            self.actions.createPointMode,
            self.actions.createLineStripMode,
            self.actions.editMode,
        )
        utils.addActions(self.menus.edit, actions + self.actions.editMenu)

    def setDirty(self):
        # Even if we autosave the file, we keep the ability to undo
        self.actions.redo.setEnabled(self.canvas.isShapeRedostorable)
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)

        if self._config["auto_save"] or self.actions.saveAuto.isChecked():
            label_file = osp.splitext(self.imagePath)[0] + ".json"
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            self.saveLabels(label_file)
            return
        self.dirty = True
        self.actions.save.setEnabled(True)
        title = __appname__
        if self.filename is not None:
            title = "{} - {}*".format(title, os.path.basename(self.filename))
        self.setWindowTitle(title)

    def setClean(self):
        self.dirty = False
        self.actions.save.setEnabled(False)
        if self._classType is None:
            self.actions.createRectangleMode.setEnabled(True)
            self.actions.createMode.setEnabled(True)
        else:
            self.actions.createRectangleMode.setEnabled('Detection' in self._classType)
            self.actions.createMode.setEnabled('Segmentation' in self._classType)
            self.actions.createRectangleMode.setEnabled('detection' in self._classType)
            self.actions.createMode.setEnabled('segmentation' in self._classType)
            if self._classType == 'ELButtonShapeSegmentation':
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createMode.setEnabled(True)
        self.actions.createCircleMode.setEnabled(False)
        self.actions.createLineMode.setEnabled(False)
        self.actions.createPointMode.setEnabled(False)
        self.actions.createLineStripMode.setEnabled(False)
        title = __appname__
        if self.filename is not None:
            title = "{} - {}".format(title, os.path.basename(self.filename))
        self.setWindowTitle(title)

        # if self.hasLabelFile():
        #     self.actions.deleteFile.setEnabled(True)
        # else:
        #     self.actions.deleteFile.setEnabled(False)
        self.actions.deleteFile.setEnabled(False)

    def toggleActions(self, value=True):

        for z in self.actions.zoomActions:
            z.setEnabled(value)

        for action in self.actions.onAdministrator:
            action.setEnabled(value)

        self.actions.brightnessContrast.setEnabled(value)
        self.actions.prevBrightnessContrast.setEnabled(value)
        self.actions.edit_label_name.setEnabled(value)

        # Cloud-Native: Activate Cloud-Native actions when image is loaded
        if hasattr(self.actions, 'submitTask'):
            self.actions.submitTask.setEnabled(value)
        if hasattr(self.actions, 'postponeTask'):
            self.actions.postponeTask.setEnabled(value)
        if hasattr(self.actions, 'dropTask'):
            self.actions.dropTask.setEnabled(value)
        if hasattr(self.actions, 'discardTask'):
            self.actions.discardTask.setEnabled(value)
        if hasattr(self.actions, 'loadTask'):
            self.actions.loadTask.setEnabled(not value)
        if hasattr(self.actions, 'loadModifyTask'):
            self.actions.loadModifyTask.setEnabled(not value)
        if hasattr(self.actions, 'loadPostponeTask'):
            self.actions.loadPostponeTask.setEnabled(not value)
        if hasattr(self.actions, 'loadReadyGtTask'):
            self.actions.loadReadyGtTask.setEnabled(not value)

        if self._classType is None:
            for action in self.actions.onLoadActive:
                action.setEnabled(value)
        elif 'segmentation' in self._classType or 'Segmentation' in self._classType:
            for action in self.actions.onLoadSegmentationActive:
                action.setEnabled(value)
        elif 'detection' in self._classType or 'Detection' in self._classType:
            for action in self.actions.onLoadObject2dActive:
                action.setEnabled(value)

    def queueEvent(self, function):
        QtCore.QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def resetState(self):
        self.labelList.clear()
        self.filename = None
        self.imagePath = None
        self.imageData = None
        self.labelFile = None
        self.otherData = None
        self.canvas.resetState()

        # Cloud-Native: Stop and reset timer
        self._stopDeadlineTimer()

    def currentItem(self):
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    def addRecentFile(self, filename):
        if filename in self.recentFiles:
            self.recentFiles.remove(filename)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filename)

    # Callbacks

    def redoShapeEdit(self):
        self.canvas.redoStoreShape()
        self.labelList.clear()
        self.loadShapes(self.canvas.shapes)
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)
        self.actions.redo.setEnabled(self.canvas.isShapeRedostorable)

    def undoShapeEdit(self):
        self.canvas.restoreShape()
        self.labelList.clear()
        self.loadShapes(self.canvas.shapes)
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)
        self.actions.redo.setEnabled(self.canvas.isShapeRedostorable)

    def tutorial(self):
        url = "https://github.com/wkentaro/labelme/tree/main/examples/tutorial"  # NOQA
        webbrowser.open(url)

    def check_labels(self):
        if self.filename is None:
            QtWidgets.QMessageBox.warning(
                self, "Check Labels",
                "No image loaded."
            )
            return
        if not hasattr(self, 'ImagePopup'):
            folder_path = os.path.dirname(self.filename)
            self.ImagePopup = ImagePopup(
                parent=self,
                folder_path=folder_path,
            )
        if (self._classType is None or
            'segmentation' in self._classType or
            'Segmentation' in self._classType):
            self.ImagePopup.masked_widget_state = True
            self.ImagePopup.overlayed_widget_state = True
        elif (self._classType is None or
              'detection' in self._classType or
              'Detection' in self._classType):
            self.ImagePopup.object_widget_state = True
        self.ImagePopup.popUp(self.filename, True)

    def crop_classes(self):
        folder_path = os.path.split(self.filename)[0]
        wait_popup = ConvertLabelPopup()
        crop_label_class.crop_labels(folder_path, wait_popup)

    def delete_label_dir(self):
        folder_path = os.path.split(self.filename)[0]
        crop_label_class.delete_class_dir(folder_path)

    def convert_segments(self):
        folder_path = os.path.split(self.filename)[0]
        wait_popup = ConvertLabelPopup()
        draw_segment_label.convert_segments(folder_path, wait_popup)

    def convert_bounding_boxes(self):
        folder_path = os.path.split(self.filename)[0]
        wait_popup = ConvertLabelPopup()
        draw_object_label.convert_objects(folder_path, wait_popup)

    def measure_cursor(self):
        if self.measure_cursor_flag is False:
            if self.canvas.mode == self.canvas.CREATE:
                return
            self.measure_cursor_flag = True
            self.setCursor(QtGui.QCursor(self.cross_cursor))
            self.canvas.setEditing(True, self.measure_cursor_flag)
        else:
            self.resetCursorFlag()
            self.canvas.setEditing(True, self.measure_cursor_flag)

    def make_cross_cursor(self):
        width = 25
        height = 25
        thickness = 3

        pixmap = QtGui.QPixmap(width, height)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(QtCore.Qt.black)
        pen.setWidth(thickness)
        painter.setPen(pen)
        painter.drawLine(width // 2, 0, width // 2, height)
        painter.drawLine(0, height // 2, width, height // 2)
        painter.end()
        return pixmap

    def toggleDrawingSensitive(self, drawing=True):

        self.actions.editMode.setEnabled(not drawing)
        self.actions.undoLastPoint.setEnabled(drawing)
        self.actions.undo.setEnabled(not drawing)
        self.canvas.redoShapesBackupsReset()
        self.actions.redo.setEnabled(not drawing)
        self.actions.delete.setEnabled(not drawing)

    def toggleDrawMode(self, edit=True, createMode="polygon"):
        self.canvas.setEditing(edit, self.measure_cursor_flag)
        self.canvas.createMode = createMode
        if edit:
            self.actions.createRectangleMode.setEnabled(
                self._classType is None or
                'detection' in self._classType or
                'Detection' in self._classType
            )
            self.actions.createMode.setEnabled(
                self._classType is None or
                'segmentation' in self._classType or
                'Segmentation' in self._classType
            )
            if self._classType == 'ELButtonShapeSegmentation':
                self.actions.createMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(True)
            self.actions.createCircleMode.setEnabled(False)
            self.actions.createLineMode.setEnabled(False)
            self.actions.createPointMode.setEnabled(False)
            self.actions.createLineStripMode.setEnabled(False)
        else:
            if createMode == "rectangle":
                self.actions.createMode.setEnabled(False)
                self.actions.createRectangleMode.setEnabled(
                    self._classType is None or
                    'detection' in self._classType or
                    'Detection' in self._classType
                )
                self.actions.createCircleMode.setEnabled(False)
                self.actions.createLineMode.setEnabled(False)
                self.actions.createPointMode.setEnabled(False)
                self.actions.createLineStripMode.setEnabled(False)
                self.current_edit_shape = 'rectangle'
            elif createMode == "polygon":
                self.actions.createMode.setEnabled(
                    self._classType is None or
                    'segmentation' in self._classType or
                    'Segmentation' in self._classType
                )
                self.actions.createRectangleMode.setEnabled(False)
                self.actions.createCircleMode.setEnabled(False)
                self.actions.createLineMode.setEnabled(False)
                self.actions.createPointMode.setEnabled(False)
                self.actions.createLineStripMode.setEnabled(False)
                self.current_edit_shape = 'polygon'
            elif createMode == "line":
                self.actions.createMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createCircleMode.setEnabled(True)
                self.actions.createLineMode.setEnabled(False)
                self.actions.createPointMode.setEnabled(True)
                self.actions.createLineStripMode.setEnabled(True)
            elif createMode == "point":
                self.actions.createMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createCircleMode.setEnabled(True)
                self.actions.createLineMode.setEnabled(True)
                self.actions.createPointMode.setEnabled(False)
                self.actions.createLineStripMode.setEnabled(True)
            elif createMode == "circle":
                self.actions.createMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createCircleMode.setEnabled(False)
                self.actions.createLineMode.setEnabled(True)
                self.actions.createPointMode.setEnabled(True)
                self.actions.createLineStripMode.setEnabled(True)
            elif createMode == "linestrip":
                self.actions.createMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createCircleMode.setEnabled(True)
                self.actions.createLineMode.setEnabled(True)
                self.actions.createPointMode.setEnabled(True)
                self.actions.createLineStripMode.setEnabled(False)
            else:
                raise ValueError("Unsupported createMode: %s" % createMode)
            if self._classType == 'ELButtonShapeSegmentation':
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createMode.setEnabled(True)
        self.actions.editMode.setEnabled(not edit)

    def setEditMode(self):
        self.toggleDrawMode(True)

    def updateFileMenu(self):
        current = self.filename

        def exists(filename):
            return osp.exists(str(filename))

        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f != current and exists(f)]
        for i, f in enumerate(files):
            icon = utils.newIcon("labels")
            action = QtWidgets.QAction(
                icon, "&%d %s" % (i + 1, QtCore.QFileInfo(f).fileName()), self
            )
            action.triggered.connect(functools.partial(self.loadRecent, f))
            menu.addAction(action)

    def popLabelListMenu(self, point):
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def validateLabel(self, label):
        # no validation
        if self._config["validate_label"] is None:
            return True

        for i in range(self.uniqLabelList.count()):
            label_i = self.uniqLabelList.item(i).data(Qt.UserRole)
            if self._config["validate_label"] in ["exact"]:
                if label_i == label:
                    return True
        return False

    def editLabel(self, item=None):
        # print("Edit label")
        if item and not isinstance(item, LabelListWidgetItem):
            raise TypeError("item must be LabelListWidgetItem type")

        if not self.canvas.editing():
            return
        if not item:
            item = self.currentItem()
        if item is None:
            return
        shape = item.shape()
        if shape is None:
            return
        if self._classType == 'ELButtonShapeSegmentation':
            self.current_edit_shape = self._classifier_shape_type(shape.label)
        text, flags, group_id = self.labelDialog.popUp(
            text=shape.label,
            flags=shape.flags,
            group_id=shape.group_id,
            widget_size=self.size(),
            class_type=self._classType,
            shape_type=self.current_edit_shape
        )
        if text is None:
            return
        if not self.validateLabel(text):
            self.errorMessage(
                self.tr("Invalid label"),
                self.tr("Invalid label '{}' with validation type '{}'").format(
                    text, self._config["validate_label"]
                ),
            )
            return
        shape.label = text
        shape.flags = flags
        shape.group_id = group_id

        self._update_shape_color(shape)
        if shape.group_id is None:
            item.setText(
                '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                    shape.label, *shape.fill_color.getRgb()[:3]
                )
            )
        else:
            item.setText("{} ({})".format(shape.label, shape.group_id))
        self.setDirty()
        if not self.uniqLabelList.findItemsByLabel(shape.label):
            item = QtWidgets.QListWidgetItem()
            item.setData(Qt.UserRole, shape.label)
            self.uniqLabelList.addItem(item)

    def _classifier_shape_type(self, label):
        if label in self._config['labels_class'][self._classType]['default']['polygon']:
            return 'polygon'
        elif label in self._config['labels_class'][self._classType]['default']['rectangle']:
            return 'rectangle'

    def fileSearchChanged(self):
        self.importDirImages(
            self.lastOpenDir,
            pattern=self.fileSearch.text(),
            load=False,
        )

    def fileSelectionChanged(self):
        items = self.fileListWidget.selectedItems()
        if not items:
            return
        item = items[0]

        if not self.mayContinue():
            return

        currIndex = self.imageList.index(str(item.text()))
        if currIndex < len(self.imageList):
            filename = self.imageList[currIndex]
            if filename:
                self.loadFile(filename)

    # React to canvas signals.
    def shapeSelectionChanged(self, selected_shapes):
        self._noSelectionSlot = True
        for shape in self.canvas.selectedShapes:
            shape.selected = False
        self.labelList.clearSelection()
        self.canvas.selectedShapes = selected_shapes
        for shape in self.canvas.selectedShapes:
            shape.selected = True
            item = self.labelList.findItemByShape(shape)
            self.labelList.selectItem(item)
            self.labelList.scrollToItem(item)
        self._noSelectionSlot = False
        n_selected = len(selected_shapes)
        self.actions.delete.setEnabled(n_selected)
        self.actions.duplicate.setEnabled(n_selected)
        self.actions.copy.setEnabled(n_selected)
        self.actions.edit.setEnabled(n_selected == 1)

    def addLabel(self, shape):
        shape.paint_label = self.display_label_option.isChecked()
        shape.paint_probability = self.display_probability_option.isChecked()
        if shape.group_id is None:
            text = shape.label
        else:
            text = "{} ({})".format(shape.label, shape.group_id)
        label_list_item = LabelListWidgetItem(text, shape)
        self.labelList.addItem(label_list_item)
        if not self.uniqLabelList.findItemsByLabel(shape.label):
            item = self.uniqLabelList.createItemFromLabel(shape.label)
            self.uniqLabelList.addItem(item)
            rgb = self._get_rgb_by_label(shape.label)
            self.uniqLabelList.setItemLabel(item, shape.label, rgb)
        self.labelDialog.addLabelHistory(shape.label)
        for action in self.actions.onShapesPresent:
            action.setEnabled(True)

        self._update_shape_color(shape)
        label_list_item.setText(
            '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                text, *shape.fill_color.getRgb()[:3]
            )
        )

    def _update_shape_color(self, shape):
        r, g, b = self._get_rgb_by_label(shape.label)
        shape.line_color = QtGui.QColor(r, g, b)
        shape.vertex_fill_color = QtGui.QColor(r, g, b)
        shape.hvertex_fill_color = QtGui.QColor(255, 255, 255)
        shape.fill_color = QtGui.QColor(r, g, b, 128)
        shape.select_line_color = QtGui.QColor(255, 255, 255)
        shape.select_fill_color = QtGui.QColor(r, g, b, 155)

    def _get_rgb_by_label(self, label):
        if self._config["shape_color"] == "auto":
            item = self.uniqLabelList.findItemsByLabel(label)[0]
            label_id = self.uniqLabelList.indexFromItem(item).row() + 1
            label_id += self._config["shift_auto_shape_color"]
            return LABEL_COLORMAP[label_id % len(LABEL_COLORMAP)]
        elif (
            self._config["shape_color"] == "manual"
            and self._config["label_colors"]
            and label in self._config["label_colors"]
        ):
            return self._config["label_colors"][label]
        elif self._config["default_shape_color"]:
            return self._config["default_shape_color"]
        return (0, 255, 0)

    def remLabels(self, shapes):
        for shape in shapes:
            item = self.labelList.findItemByShape(shape)
            self.labelList.removeItem(item)

    def loadShapes(self, shapes, replace=True):
        self._noSelectionSlot = True
        for shape in shapes:
            self.addLabel(shape)
        self.labelList.clearSelection()
        self._noSelectionSlot = False
        self.canvas.loadShapes(shapes, replace=replace)

    def loadLabels(self, shapes):
        s = []
        for shape in shapes:
            label = shape["label"]
            points = shape["points"]
            if "probability" in shape:
                probability = shape["probability"]
            else:
                probability = None
            shape_type = shape["shape_type"]
            flags = shape["flags"]
            group_id = shape["group_id"]
            other_data = shape["other_data"]

            if not points:
                # skip point-empty shape
                continue

            shape = Shape(
                label=label,
                probability=probability,
                shape_type=shape_type,
                group_id=group_id,
            )
            for x, y in points:
                shape.addPoint(QtCore.QPointF(x, y))
            if len(shape.points) == 2:
                shape.align_points()
                shape.updateCorners()
            shape.close()

            default_flags = {}
            if self._config["label_flags"]:
                for pattern, keys in self._config["label_flags"].items():
                    if re.match(pattern, label):
                        for key in keys:
                            default_flags[key] = False
            shape.flags = default_flags
            shape.flags.update(flags)
            shape.other_data = other_data

            s.append(shape)
        self.loadShapes(s)

    def loadFlags(self, flags):
        self.flag_widget.clear()
        for key, flag in flags.items():
            item = QtWidgets.QListWidgetItem(key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if flag else Qt.Unchecked)
            self.flag_widget.addItem(item)

    def saveLabels(self, filename):
        lf = LabelFile()

        def format_shape(s):
            data = s.other_data.copy()
            data.update(
                dict(
                    label=s.label.encode("utf-8") if PY2 else s.label,
                    points=[(p.x(), p.y()) for p in s.points],
                    probability=s.probability,
                    group_id=s.group_id,
                    shape_type=s.shape_type,
                    flags=s.flags,
                )
            )
            return data

        shapes = [format_shape(item.shape()) for item in self.labelList]
        flags = {}
        for i in range(self.flag_widget.count()):
            item = self.flag_widget.item(i)
            key = item.text()
            flag = item.checkState() == Qt.Checked
            flags[key] = flag
        try:
            imagePath = osp.basename(self.imagePath)
            imageData = None  # self.imageData if self._config["store_data"] else None
            if osp.dirname(filename) and not osp.exists(osp.dirname(filename)):
                os.makedirs(osp.dirname(filename))
            lf.save(
                filename=filename,
                shapes=shapes,
                imagePath=imagePath,
                imageData=imageData,
                imageHeight=self.image.height(),
                imageWidth=self.image.width(),
                otherData=self.otherData,
                flags=flags,
                classType=self._classType,
            )
            self.labelFile = lf
            items = self.fileListWidget.findItems(
                self.imagePath, Qt.MatchExactly
            )
            if len(items) > 0:
                if len(items) != 1:
                    raise RuntimeError("There are duplicate files.")
                items[0].setCheckState(Qt.Checked)
            # disable allows next and previous image to proceed
            # self.filename = filename
            return True
        except LabelFileError as e:
            self.errorMessage(
                self.tr("Error saving label data"), self.tr("<b>%s</b>") % e
            )
            return False

    def duplicateSelectedShape(self):
        added_shapes = self.canvas.duplicateSelectedShapes()
        self.labelList.clearSelection()
        for shape in added_shapes:
            self.addLabel(shape)
        self.setDirty()

    def pasteSelectedShape(self):
        self.loadShapes(self._copied_shapes, replace=False)
        self.setDirty()

    def copySelectedShape(self):
        self._copied_shapes = [s.copy() for s in self.canvas.selectedShapes]
        self.actions.paste.setEnabled(len(self._copied_shapes) > 0)

    def labelSelectionChanged(self):
        if self._noSelectionSlot:
            return
        if self.canvas.editing():
            selected_shapes = []
            for item in self.labelList.selectedItems():
                selected_shapes.append(item.shape())
            if selected_shapes:
                self.canvas.selectShapes(selected_shapes)
            else:
                self.canvas.deSelectShape()

    def labelItemChanged(self, item):
        shape = item.shape()
        self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    def labelOrderChanged(self):
        self.setDirty()
        # print("Label order changed")
        self.canvas.loadShapes([item.shape() for item in self.labelList])
        for shape in self.canvas.shapes:
            shape.selected = False

    # Callback functions:

    def newShape(self):

        items = self.uniqLabelList.selectedItems()
        text = None
        if items:
            text = items[0].data(Qt.UserRole)
        flags = {}
        group_id = None
        if self._config["display_label_popup"] or not text:
            previous_text = self.labelDialog.edit.text()
            if self._config["single_class"] and self._last_label:
                text = self._last_label
            else:
                text, flags, group_id = self.labelDialog.popUp(
                    text,
                    widget_size=self.size(),
                    class_type=self._classType,
                    shape_type=self.current_edit_shape
                )
            if not text:
                self.labelDialog.edit.setText(previous_text)

        if text and not self.validateLabel(text):
            self.errorMessage(
                self.tr("Invalid label"),
                self.tr("Invalid label '{}' with validation type '{}'").format(
                    text, self._config["validate_label"]
                ),
            )
            text = ""
        if text:
            self.labelList.clearSelection()
            shape = self.canvas.setLastLabel(text, flags)
            shape.group_id = group_id
            self.addLabel(shape)
            self.actions.editMode.setEnabled(True)
            self.actions.undoLastPoint.setEnabled(False)
            self.actions.undo.setEnabled(True)
            self.actions.redo.setEnabled(self.canvas.isShapeRedostorable)
            self.setDirty()
            self._last_label = text
        else:
            self.canvas.undoLastLine()
            self.canvas.shapesBackups.pop()

    def scrollRequest(self, delta, orientation):
        units = -delta * 0.1  # natural scroll
        bar = self.scrollBars[orientation]
        value = bar.value() + bar.singleStep() * units
        self.setScroll(orientation, value)

    def setScroll(self, orientation, value):
        self.scrollBars[orientation].setValue(int(value))
        self.scroll_values[orientation][self.filename] = int(value)

    def setZoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)
        self.zoom_values[self.filename] = (self.zoomMode, value)

    def addZoom(self, increment=1.1):
        zoom_value = self.zoomWidget.value() * increment
        if increment > 1:
            zoom_value = math.ceil(zoom_value)
        else:
            zoom_value = math.floor(zoom_value)
        self.setZoom(zoom_value)

    def zoomRequest(self, delta, pos):
        canvas_width_old = self.canvas.width()
        units = 1.1
        if delta < 0:
            units = 0.9
        self.addZoom(units)

        canvas_width_new = self.canvas.width()
        if canvas_width_old != canvas_width_new:
            canvas_scale_factor = canvas_width_new / canvas_width_old

            x_shift = round(pos.x() * canvas_scale_factor) - pos.x()
            y_shift = round(pos.y() * canvas_scale_factor) - pos.y()

            self.setScroll(
                Qt.Horizontal,
                self.scrollBars[Qt.Horizontal].value() + x_shift,
            )
            self.setScroll(
                Qt.Vertical,
                self.scrollBars[Qt.Vertical].value() + y_shift,
            )

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def enableKeepPrevScale(self, enabled):
        self._config["keep_prev_scale"] = enabled
        self.actions.keepPrevScale.setChecked(enabled)

    def onNewBrightnessContrast(self, qimage):
        self.canvas.loadPixmap(
            QtGui.QPixmap.fromImage(qimage), clear_shapes=False
        )

    def brightnessContrast(self, value):
        dialog = BrightnessContrastDialog(
            utils.img_data_to_pil(self.imageData),
            self.onNewBrightnessContrast,
            parent=self,
        )
        brightness, contrast = self.brightnessContrast_values.get(
            self.filename, (None, None)
        )
        self._prev_brightness_contrast = (brightness, contrast)
        if brightness is not None:
            dialog.slider_brightness.setValue(brightness)
        if contrast is not None:
            dialog.slider_contrast.setValue(contrast)
        dialog.exec_()

        brightness = dialog.slider_brightness.value()
        contrast = dialog.slider_contrast.value()
        self.brightnessContrast_values[self.filename] = (brightness, contrast)

    def prevBrightnessContrast(self):
        dialog = BrightnessContrastDialog(
            utils.img_data_to_pil(self.imageData),
            self.onNewBrightnessContrast,
            parent=self,
        )
        brightness, contrast = self.brightnessContrast_values.get(
            self.filename, (None, None)
        )
        prev_brightness, prev_contrast = self._prev_brightness_contrast
        if prev_brightness is None:
            prev_brightness = 50
        if prev_contrast is None:
            prev_contrast = 50
        dialog.slider_brightness.setValue(prev_brightness)
        dialog.slider_contrast.setValue(prev_contrast)

        dialog.onNewValue(None)

        self.brightnessContrast_values[self.filename] = (prev_brightness, prev_contrast)
        self._prev_brightness_contrast = (brightness, contrast)

    def togglePolygons(self, value):
        for item in self.labelList:
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)

    def toggleHideFlagAndToggleShapes(self, shape_type):
        if shape_type == 'polygon':
            self.hide_polygon_flag = not self.hide_polygon_flag
            self.toggleByShapeType(self.hide_polygon_flag, 'polygon')
        elif shape_type == 'rectangle':
            self.hide_rectangle_flag = not self.hide_rectangle_flag
            self.toggleByShapeType(self.hide_rectangle_flag, 'rectangle')

    def toggleByShapeType(self, hide_flag, shape_type):
        for item in self.labelList:
            shape = item.shape()
            if shape.shape_type == shape_type:
                item.setCheckState(Qt.Unchecked if hide_flag else Qt.Checked)

    def loadFile(self, filename=None):

        # changing fileListWidget loads file
        if filename in self.imageList and (
            self.fileListWidget.currentRow() != self.imageList.index(filename)
        ):
            self.fileListWidget.setCurrentRow(self.imageList.index(filename))
            self.fileListWidget.repaint()
            return

        self.resetState()
        self.canvas.setEnabled(False)
        if filename is None:
            filename = self.settings.value("filename", "")
        filename = str(filename)
        if not QtCore.QFile.exists(filename):
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr("No such file: <b>%s</b>") % filename,
            )
            return False
        # assumes same name, but json extension
        self.status(
            str(self.tr("Loading %s...")) % osp.basename(str(filename))
        )
        label_file = osp.splitext(filename)[0] + ".json"
        if self.output_dir:
            label_file_without_path = osp.basename(label_file)
            label_file = osp.join(self.output_dir, label_file_without_path)
        if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(
            label_file
        ):
            try:
                self.labelFile = LabelFile(label_file)
                size_weight = 30
                # if "outdoor" in self.labelFile.classType:
                if "EL" not in self.labelFile.classType or "indoor" not in self.labelFile.classType:
                    size_weight = 50
                    Shape.point_size = 8
                Shape.label_font_size = size_weight * self.labelFile.imageHeight / 2160
                if (self.labelFile.classType == "ELStateDetection" or
                        self.labelFile.classType == "indoor_detection-ev_state" or
                        self.labelFile.classType == "ELButtonStateClassification" or
                        self.labelFile.classType == "indoor_detection-ev_button"):
                    Shape.point_size = 3
                    self.labelDialog.default_completion_mode()
                self.canvas.updateType(self.labelFile.classType)

            except LabelFileError as e:
                self.errorMessage(
                    self.tr("Error opening file"),
                    self.tr(
                        "<p><b>%s</b></p>"
                        "<p>Make sure <i>%s</i> is a valid label file."
                    )
                    % (e, label_file),
                )
                self.status(self.tr("Error reading %s") % label_file)
                return False
            self.imageData = self.labelFile.imageData
            self.imagePath = osp.join(
                osp.dirname(label_file),
                self.labelFile.imagePath,
            )
            self.otherData = self.labelFile.otherData
        else:
            self.imageData = LabelFile.load_image_file(filename)
            if self.imageData:
                self.imagePath = filename
            self.labelFile = None
        image = QtGui.QImage.fromData(self.imageData)

        if image.isNull():
            formats = [
                "*.{}".format(fmt.data().decode())
                for fmt in QtGui.QImageReader.supportedImageFormats()
            ]
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr(
                    "<p>Make sure <i>{0}</i> is a valid image file.<br/>"
                    "Supported image formats: {1}</p>"
                ).format(filename, ",".join(formats)),
            )
            self.status(self.tr("Error reading %s") % filename)
            return False
        self.image = image
        self.filename = filename
        if self._config["keep_prev"]:
            prev_shapes = self.canvas.shapes
        self.canvas.loadPixmap(QtGui.QPixmap.fromImage(image))
        if self.labelFile:
            self._classType = self.labelFile.classType
            self.loadLabels(self.labelFile.shapes)
        else:
            self._classType = None
        # if 'ELButtonStateClassification' in self.labelFile.classType:
        #     if self._config["flags"]:
        #         if self.labelFile.flags == {}:
        #             self.loadFlags({k: v for k, v in self._config["flags"].items()})
        #         else:
        #             self.loadFlags({k: v for k, v in self.labelFile.flags.items()})
        #     self.flag_widget.itemChanged.connect(self.onItemChanged)
        # else:
        #     self.flag_widget.clear()
        if self._config["keep_prev"] and self.noShapes():
            self.loadShapes(prev_shapes, replace=False)
            self.setDirty()
        else:
            self.setClean()
        self.canvas.setEnabled(True)
        # set zoom values
        is_initial_load = not self.zoom_values
        if self.filename in self.zoom_values:
            self.zoomMode = self.zoom_values[self.filename][0]
            self.setZoom(self.zoom_values[self.filename][1])
        elif is_initial_load or not self._config["keep_prev_scale"]:
            self.adjustScale(initial=True)
        # set scroll values
        for orientation in self.scroll_values:
            if self.filename in self.scroll_values[orientation]:
                self.setScroll(
                    orientation, self.scroll_values[orientation][self.filename]
                )
        # set brightness contrast values
        dialog = BrightnessContrastDialog(
            utils.img_data_to_pil(self.imageData),
            self.onNewBrightnessContrast,
            parent=self,
        )
        brightness, contrast = self.brightnessContrast_values.get(
            self.filename, (None, None)
        )
        if self._config["keep_prev_brightness"] and self.recentFiles:
            brightness, _ = self.brightnessContrast_values.get(
                self.recentFiles[0], (None, None)
            )
        if self._config["keep_prev_contrast"] and self.recentFiles:
            _, contrast = self.brightnessContrast_values.get(
                self.recentFiles[0], (None, None)
            )
        if brightness is not None:
            dialog.slider_brightness.setValue(brightness)
        if contrast is not None:
            dialog.slider_contrast.setValue(contrast)
        self.brightnessContrast_values[self.filename] = (brightness, contrast)
        if brightness is not None or contrast is not None:
            dialog.onNewValue(None)
        self.paintCanvas()
        self.addRecentFile(self.filename)
        self.toggleActions(True)
        self.canvas.setFocus()

        # Cloud-Native: Pass current image path to CommentWidget (only in cloud-native mode)
        if self.is_cloud_native_mode:
            if hasattr(self, 'comment_widget') and self.comment_widget:
                self.comment_widget.set_image_path(self.filename)

            # Cloud-Native: Start timer (48-hour countdown)
            self._startDeadlineTimer(self.filename)

            # Cloud-Native: Save session info
            self._save_session_info(self.filename)

        self.status(str(self.tr("Loaded %s")) % osp.basename(str(filename)))
        return True

    def resizeEvent(self, event):
        if (
            self.canvas
            and not self.image.isNull()
            and self.zoomMode != self.MANUAL_ZOOM
        ):
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        value = int(100 * value)
        self.zoomWidget.setValue(value)
        self.zoom_values[self.filename] = (self.zoomMode, value)

    def scaleFitWindow(self):

        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def enableSaveImageWithData(self, enabled):
        self._config["store_data"] = enabled
        self.actions.saveWithImageData.setChecked(enabled)

    def closeEvent(self, event):
        # self.canvas.measureWorkingTime.measure_time()
        # self.canvas.measureWorkingTime.working_count += 1
        # self.canvas.measureWorkingTime.write_crypt_description(self.imagePath)
        if not self.mayContinue():
            event.ignore()
        self.settings.setValue(
            "filename", self.filename if self.filename else ""
        )
        self.settings.setValue("window/size", self.size())
        self.settings.setValue("window/position", self.pos())
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("recentFiles", self.recentFiles)
        # ask the use for where to save the labels
        # self.settings.setValue('window/geometry', self.saveGeometry())

    def dragEnterEvent(self, event):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        if event.mimeData().hasUrls():
            items = [i.toLocalFile() for i in event.mimeData().urls()]
            if any([i.lower().endswith(tuple(extensions)) for i in items]):
                event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self.mayContinue():
            event.ignore()
            return
        items = [i.toLocalFile() for i in event.mimeData().urls()]
        self.importDroppedImageFiles(items)

    # User Dialogs #

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def openPrevImg(self, _value=False):
        if self.canvas.drawing() and self.canvas.current:
            return
        self.resetHideFlags()
        # self.canvas.measureWorkingTime.measure_time()
        # self.canvas.measureWorkingTime.working_count += 1
        # self.canvas.measureWorkingTime.write_crypt_description(self.imagePath)
        keep_prev = self._config["keep_prev"]
        if QtWidgets.QApplication.keyboardModifiers() == (
            Qt.ControlModifier | Qt.ShiftModifier
        ):
            self._config["keep_prev"] = True

        if not self.mayContinue():
            return

        if len(self.imageList) <= 0:
            return

        if self.filename is None:
            return

        currIndex = self.imageList.index(self.filename)
        if currIndex - 1 >= 0:
            filename = self.imageList[currIndex - 1]
            if filename:
                self.loadFile(filename)

        self.ImagePopup.popUp(self.filename)

        self._config["keep_prev"] = keep_prev

    def openNextImg(self, _value=False, load=True):
        if self.canvas.drawing() and self.canvas.current:
            return
        self.resetHideFlags()
        if self.imagePath:
            # self.canvas.measureWorkingTime.measure_time()
            # self.canvas.measureWorkingTime.working_count += 1
            # self.canvas.measureWorkingTime.write_crypt_description(self.imagePath)
            if self._config["auto_save"] or self.actions.saveAuto.isChecked():
                label_file = osp.splitext(self.imagePath)[0] + ".json"
                if self.output_dir:
                    label_file_without_path = osp.basename(label_file)
                    label_file = osp.join(self.output_dir, label_file_without_path)
                if self._classType is not None:
                    self.saveLabels(label_file)

        keep_prev = self._config["keep_prev"]
        if QtWidgets.QApplication.keyboardModifiers() == (
            Qt.ControlModifier | Qt.ShiftModifier
        ):
            self._config["keep_prev"] = True

        if not self.mayContinue():
            return

        if len(self.imageList) <= 0:
            return

        filename = None
        if self.filename is None:
            filename = self.imageList[0]
        else:
            currIndex = self.imageList.index(self.filename)
            if currIndex + 1 < len(self.imageList):
                filename = self.imageList[currIndex + 1]
            else:
                filename = self.imageList[-1]
        self.filename = filename

        if self.filename and load:
            self.loadFile(self.filename)

        self.ImagePopup.popUp(self.filename)

        self._config["keep_prev"] = keep_prev

    def openFile(self, _value=False):
        if not self.mayContinue():
            return
        path = osp.dirname(str(self.filename)) if self.filename else "."
        formats = [
            "*.{}".format(fmt.data().decode())
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        filters = self.tr("Image & Label files (%s)") % " ".join(
            formats + ["*%s" % LabelFile.suffix]
        )
        fileDialog = FileDialogPreview(self)
        fileDialog.setFileMode(FileDialogPreview.ExistingFile)
        fileDialog.setNameFilter(filters)
        fileDialog.setWindowTitle(
            self.tr("%s - Choose Image or Label file") % __appname__,
        )
        fileDialog.setWindowFilePath(path)
        fileDialog.setViewMode(FileDialogPreview.Detail)
        if fileDialog.exec_():
            fileName = fileDialog.selectedFiles()[0]
            if fileName:
                self.loadFile(fileName)

                format_name = fileName.split('.')[-1]
                json_file = fileName[:-len(format_name)] + 'json'
                target_class = self.get_target_class(json_file)
                self.choose_labels_class(target_class)

    def changeOutputDirDialog(self, _value=False):
        default_output_dir = self.output_dir
        if default_output_dir is None and self.filename:
            default_output_dir = osp.dirname(self.filename)
        if default_output_dir is None:
            default_output_dir = self.currentPath()

        output_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self.tr("%s - Save/Load Annotations in Directory") % __appname__,
            default_output_dir,
            QtWidgets.QFileDialog.ShowDirsOnly
            | QtWidgets.QFileDialog.DontResolveSymlinks,
        )
        output_dir = str(output_dir)

        if not output_dir:
            return

        self.output_dir = output_dir

        self.statusBar().showMessage(
            self.tr("%s . Annotations will be saved/loaded in %s")
            % ("Change Annotations Dir", self.output_dir)
        )
        self.statusBar().show()

        current_filename = self.filename
        self.importDirImages(self.lastOpenDir, load=False)

        if current_filename in self.imageList:
            # retain currently selected file
            self.fileListWidget.setCurrentRow(
                self.imageList.index(current_filename)
            )
            self.fileListWidget.repaint()

    def saveFile(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        if self.labelFile:
            # DL20180323 - overwrite when in directory
            self._saveFile(self.labelFile.filename)
        elif self.output_file:
            self._saveFile(self.output_file)
            self.close()
        else:
            self._saveFile(self.saveFileDialog())

    def saveFileAs(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())

    def saveFileDialog(self):
        caption = self.tr("%s - Choose File") % __appname__
        filters = self.tr("Label files (*%s)") % LabelFile.suffix
        if self.output_dir:
            dlg = QtWidgets.QFileDialog(
                self, caption, self.output_dir, filters
            )
        else:
            dlg = QtWidgets.QFileDialog(
                self, caption, self.currentPath(), filters
            )
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dlg.setOption(QtWidgets.QFileDialog.DontConfirmOverwrite, False)
        dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, False)
        basename = osp.basename(osp.splitext(self.filename)[0])
        if self.output_dir:
            default_labelfile_name = osp.join(
                self.output_dir, basename + LabelFile.suffix
            )
        else:
            default_labelfile_name = osp.join(
                self.currentPath(), basename + LabelFile.suffix
            )
        filename = dlg.getSaveFileName(
            self,
            self.tr("Choose File"),
            default_labelfile_name,
            self.tr("Label files (*%s)") % LabelFile.suffix,
        )
        if isinstance(filename, tuple):
            filename, _ = filename
        return filename

    def _saveFile(self, filename):
        if filename and self.saveLabels(filename):
            self.addRecentFile(filename)
            self.setClean()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def getLabelFile(self):
        if self.filename.lower().endswith(".json"):
            label_file = self.filename
        else:
            label_file = osp.splitext(self.filename)[0] + ".json"

        return label_file

    def deleteFile(self):
        mb = QtWidgets.QMessageBox
        msg = self.tr(
            "You are about to permanently delete this label file, "
            "proceed anyway?"
        )
        answer = mb.warning(self, self.tr("Attention"), msg, mb.Yes | mb.No)
        if answer != mb.Yes:
            return

        label_file = self.getLabelFile()
        if osp.exists(label_file):
            os.remove(label_file)
            logger.info("Label file is removed: {}".format(label_file))

            item = self.fileListWidget.currentItem()
            item.setCheckState(Qt.Unchecked)

            self.resetState()

    # Message Dialogs. #
    def hasLabels(self):
        if self.noShapes():
            self.errorMessage(
                "No objects labeled",
                "You must label at least one object to save the file.",
            )
            return False
        return True

    def hasLabelFile(self):
        if self.filename is None:
            return False

        label_file = self.getLabelFile()
        return osp.exists(label_file)

    def mayContinue(self):
        if not self.dirty:
            return True
        mb = QtWidgets.QMessageBox
        msg = self.tr('Save annotations to "{}" before closing?').format(
            self.filename
        )
        answer = mb.question(
            self,
            self.tr("Save annotations?"),
            msg,
            mb.Save | mb.Discard | mb.Cancel,
            mb.Save,
        )
        if answer == mb.Discard:
            return True
        elif answer == mb.Save:
            self.saveFile()
            return True
        else:  # answer == mb.Cancel
            return False

    def errorMessage(self, title, message):
        return QtWidgets.QMessageBox.critical(
            self, title, "<p><b>%s</b></p>%s" % (title, message)
        )

    def currentPath(self):
        return osp.dirname(str(self.filename)) if self.filename else "."

    def toggleKeepPrevMode(self):
        self._config["keep_prev"] = not self._config["keep_prev"]

    def toggleAutoSaveMode(self):
        self._config["auto_save"] = not self._config["auto_save"]

    def toggleAddPointMode(self):
        self._config["add_point"] = not self._config["add_point"]
        self.canvas.addPointMode = self._config["add_point"]

    def toggleSingleClassMode(self):
        self._config["single_class"] = not self._config["single_class"]

    def toggle_delete_popup(self):
        self._config["delete_popup"] = not self._config["delete_popup"]

    def toggleKeepBrightnessContrast(self):
        self._config["keep_prev_brightness"] = not self._config["keep_prev_brightness"]
        self._config["keep_prev_contrast"] = not self._config["keep_prev_contrast"]

    def togglePaintLabelsOption(self):
        for shape in self.canvas.shapes:
            shape.paint_label = self.display_label_option.isChecked()

    def togglePaintProbabilityOption(self):
        for shape in self.canvas.shapes:
            shape.paint_probability = self.display_probability_option.isChecked()

    def removeSelectedPoint(self):
        self.canvas.removeSelectedPoint()
        self.canvas.update()
        if not self.canvas.hShape.points:
            self.canvas.deleteShape(self.canvas.hShape)
            self.remLabels([self.canvas.hShape])
            self.setDirty()
            if self.noShapes():
                for action in self.actions.onShapesPresent:
                    action.setEnabled(False)

    def deleteSelectedShape(self):
        if self._config["delete_popup"]:
            yes, no = QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
            msg = self.tr(
                "You are about to permanently delete {} polygons, "
                "proceed anyway?"
            ).format(len(self.canvas.selectedShapes))
            if yes == QtWidgets.QMessageBox.warning(
                self, self.tr("Attention"), msg, yes | no, yes
            ):
                self.remLabels(self.canvas.deleteSelected())
                self.setDirty()
                if self.noShapes():
                    for action in self.actions.onShapesPresent:
                        action.setEnabled(False)
        else:
            self.remLabels(self.canvas.deleteSelected())
            self.setDirty()
            if self.noShapes():
                for action in self.actions.onShapesPresent:
                    action.setEnabled(False)

    def copyShape(self):
        self.canvas.endMove(copy=True)
        for shape in self.canvas.selectedShapes:
            self.addLabel(shape)
        self.labelList.clearSelection()
        self.setDirty()

    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.setDirty()

    def openDirDialog(self, _value=False, dirpath=None):
        if not self.mayContinue():
            return
        if not self.canvas.measureWorkingTime.read_worker_name():
            popwin = WorkerNameWindow()
            popwin.setModal(True)
            popwin.exec_()
            if not self.canvas.measureWorkingTime.read_worker_name():
                return

        defaultOpenDirPath = dirpath if dirpath else "."
        if self.lastOpenDir and osp.exists(self.lastOpenDir):
            defaultOpenDirPath = self.lastOpenDir
        else:
            defaultOpenDirPath = (
                osp.dirname(self.filename) if self.filename else "."
            )

        targetDirPath = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Open Directory") % __appname__,
                defaultOpenDirPath,
                QtWidgets.QFileDialog.ShowDirsOnly
                | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )
        self.importDirImages(targetDirPath)
        self.canvas.measureWorkingTime.init_write_worker_name = True

        try:
            self.choose_labels_class(self._target_class)
        except BaseException:  # noqa: B902
            pass

        if targetDirPath != '':
            self.encrypt.run(targetDirPath)

    @property
    def imageList(self):
        lst = []
        for i in range(self.fileListWidget.count()):
            item = self.fileListWidget.item(i)
            lst.append(item.text())
        return lst

    def importDroppedImageFiles(self, imageFiles):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]

        self.filename = None
        for file in imageFiles:
            if file in self.imageList or not file.lower().endswith(
                tuple(extensions)
            ):
                continue
            label_file = osp.splitext(file)[0] + ".json"
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            item = QtWidgets.QListWidgetItem(file)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(
                label_file
            ):
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.fileListWidget.addItem(item)

        if len(self.imageList) > 1:
            self.actions.openNextImg.setEnabled(True)
            self.actions.openPrevImg.setEnabled(True)

        self.openNextImg()

    def importDirImages(self, dirpath, pattern=None, load=True):
        self.actions.openNextImg.setEnabled(True)
        self.actions.openPrevImg.setEnabled(True)

        if not self.mayContinue() or not dirpath:
            return

        self.lastOpenDir = dirpath
        self.filename = None
        self.fileListWidget.clear()
        self._target_class = None
        for filename in self.scanAllImages(dirpath):
            if pattern and pattern not in filename:
                continue
            label_file = osp.splitext(filename)[0] + ".json"
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            item = QtWidgets.QListWidgetItem(filename)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(
                label_file
            ):
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.fileListWidget.addItem(item)

            format_name = filename.split('.')[-1]
            json_file = filename[:-len(format_name)] + 'json'
            target_class = self.get_target_class(json_file)
            if target_class is not None:
                self._target_class = target_class
        self.openNextImg(load=load)

    def scanAllImages(self, folderPath):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]

        images = []
        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = osp.join(root, file)
                    if not ('masked_image' in relativePath or 'overlayed_image' in relativePath):
                        images.append(relativePath)
        images = natsort.os_sorted(images)

        self.ImagePopup = ImagePopup(
            parent=self,
            folder_path=folderPath
        )

        return images

    def choose_labels_class(self, target_class=None):
        if target_class is None:
            for label_class in self._config['labels_class']:
                for label_name in self._config['labels_class'][label_class]:
                    self.labelDialog.addLabelHistory(label_name)
        else:
            class_type = None
            service_area = None
            if '/' in target_class:
                class_type, service_area = target_class.split('/')
                if service_area not in self._config['labels_class'][class_type].keys():
                    service_area = 'default'
                current_label_names = self._config['labels_class'][class_type][service_area]
                self.labelDialog.update_prev_label_history()
                self.labelDialog.removeDuplicatedLabelHistory(self._last_label_names)
                for label_name in current_label_names:
                    if self._classType == 'ELButtonShapeSegmentation':
                        self.labelDialog.ELButtonShapeSegmentation_label = current_label_names
                        break
                    self.labelDialog.addLabelHistory(label_name)
                self._last_label_names = current_label_names

    def get_target_class(self, file_path):
        service_area = None
        target_class = None
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
            except Exception as e:
                raise LabelFileError(e)

            if 'classType' in data:
                class_type = data['classType']
                target_class = class_type
                if 'serviceArea' in data:
                    service_area = data['serviceArea']
                    target_class = class_type + '/' + service_area
                else:
                    target_class = class_type + '/default'
        return target_class

    def resetHideFlags(self):
        self.hide_polygon_flag = False
        self.hide_rectangle_flag = False

    def resetCursorFlag(self):
        self.measure_cursor_flag = False
        self.setCursor(Qt.ArrowCursor)

    # ============ Cloud-Native Methods ============

    def _showStartupDialogs(self):
        # Login dialog
        login_dialog = LoginDialog(self)
        if login_dialog.exec_() != QtWidgets.QDialog.Accepted:
            # Exit app if login cancelled
            self.close()
            return

        self.current_user_id = login_dialog.get_user_id()
        self.is_cloud_native_mode = True  # Enable Cloud-native mode
        logger.info(f"User logged in: {self.current_user_id}, Cloud-native mode enabled")

        # Check session restoration
        session_data = self._load_session_info()

        if session_data:
            # If there is an image in progress
            image_filename = session_data.get("image_filename")
            saved_mode = session_data.get("mode")
            saved_user_id = session_data.get("user_id")

            # Check User ID (Ignore if session belongs to another user)
            if saved_user_id == self.current_user_id:
                QtWidgets.QMessageBox.information(
                    self,
                    "Restore Task",
                    f"Work in progress found.\n"
                    f"Image: {image_filename}\nMode: {saved_mode}"
                )

                # Set to saved mode
                self.current_mode = saved_mode
                logger.info(
                    f"Session restored: mode={saved_mode}, "
                    f"image={image_filename}"
                )

                # Restore Firebase state
                self.current_doc_id = session_data.get("doc_id")
                self.current_task_status = session_data.get("task_status")

                # Apply mode settings
                self._applyModeSettings()

                # Find and load image from processing directory
                image_path = os.path.join(
                    self.processing_dir, image_filename
                )
                if os.path.exists(image_path):
                    self.loadFile(image_path)
                else:
                    logger.warning(f"Session image not found: {image_path}")
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Image Not Found",
                        f"Saved image not found: {image_filename}"
                    )
                    # Delete session info and proceed to mode selection
                    self._clear_session_info()
                    self._selectModeAndApply()
            else:
                logger.info(f"Session user mismatch: {saved_user_id} != {self.current_user_id}")
                self._selectModeAndApply()
        else:
            # Select mode if no session info
            self._selectModeAndApply()

    def _selectModeAndApply(self):
        mode_dialog = ModeSelectionDialog(self.current_user_id, self)
        if mode_dialog.exec_() != QtWidgets.QDialog.Accepted:
            # Exit app if mode selection cancelled
            self.close()
            return

        self.current_mode = mode_dialog.get_selected_mode()
        logger.info(f"Mode selected: {self.current_mode}")

        # Apply UI settings based on mode
        self._applyModeSettings()

    def _applyModeSettings(self):
        if self.current_mode == ModeSelectionDialog.MODE_LABELING:
            # Labeling Mode: Show Polygon Labels + Comment (read-only)
            self.shape_dock.setVisible(True)
            self.comment_dock.setVisible(True)
            self.comment_widget.set_read_only(True)
            self.setWindowTitle(f"{__appname__} - Labeling")

        elif self.current_mode == ModeSelectionDialog.MODE_REVIEW:
            # Review Mode: Show Polygon Labels + Comment
            self.shape_dock.setVisible(True)
            self.comment_dock.setVisible(True)
            self.comment_widget.set_read_only(False)
            self.setWindowTitle(f"{__appname__} - Review")

        elif self.current_mode == ModeSelectionDialog.MODE_FINAL_REVIEW:
            # Final Review Mode: Show Polygon Labels + Comment
            self.shape_dock.setVisible(True)
            self.comment_dock.setVisible(True)
            self.comment_widget.set_read_only(False)
            self.setWindowTitle(f"{__appname__} - Final Review")

        # Common: Keep unnecessary Docks hidden
        self.flag_dock.setVisible(False)
        self.label_dock.setVisible(False)
        self.file_dock.setVisible(False)

        # Set TaskInfoWidget mode
        if hasattr(self, 'task_info_widget') and self.task_info_widget:
            self.task_info_widget.set_mode(self.current_mode)

        # Set User ID in CommentWidget
        if hasattr(self, 'comment_widget') and self.comment_widget:
            self.comment_widget.set_user_id(self.current_user_id)

        # Button visibility per mode
        is_worker = (
            self.current_mode == ModeSelectionDialog.MODE_LABELING
        )
        is_reviewer = (
            self.current_mode == ModeSelectionDialog.MODE_REVIEW
        )
        is_supervisor = (
            self.current_mode == ModeSelectionDialog.MODE_FINAL_REVIEW
        )

        # Load Task: all modes
        self.actions.loadTask.setEnabled(True)
        # Load Modify: worker only
        self.actions.loadModifyTask.setVisible(is_worker)
        self.actions.loadModifyTask.setEnabled(is_worker)
        # Load Postpone: worker only
        self.actions.loadPostponeTask.setVisible(is_worker)
        self.actions.loadPostponeTask.setEnabled(is_worker)
        # Load Ready GT: supervisor only
        self.actions.loadReadyGtTask.setVisible(is_supervisor)
        self.actions.loadReadyGtTask.setEnabled(is_supervisor)
        # Submit: all modes (enabled when image loaded)
        # Postpone: worker only
        self.actions.postponeTask.setVisible(is_worker)
        # Drop: worker only
        self.actions.dropTask.setVisible(is_worker)
        # Discard: all modes
        self.actions.discardTask.setVisible(True)

    def changeModeAction(self):
        # Check if an image is currently loaded
        if self.filename is not None:
            QtWidgets.QMessageBox.warning(
                self,
                "Cannot Change Mode",
                "You have an image currently loaded.\n"
                "Please complete or submit the current task before changing modes."
            )
            return

        logger.info("Change Mode action triggered")

        # Show mode selection dialog
        mode_dialog = ModeSelectionDialog(self.current_user_id, self)
        if mode_dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_mode = mode_dialog.get_selected_mode()
            if new_mode != self.current_mode:
                self.current_mode = new_mode
                logger.info(f"Mode changed to: {self.current_mode}")
                self._applyModeSettings()

    def loadTaskAction(self):
        logger.info("Load Task action triggered")
        if self.filename is not None:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Load",
                "An image is already loaded. Submit or drop first."
            )
            return

        self._set_firebase_loading(True, "Loading task from Firebase...")
        worker = LoadTaskWorker(
            mode=self.current_mode,
            user_id=self.current_user_id,
            processing_dir=self.processing_dir,
            parent=self,
        )
        worker.finished.connect(self._on_load_task_finished)
        worker.error.connect(self._on_firebase_error)
        self._active_worker = worker
        worker.start()
        # worker.execute()

    def loadModifyTaskAction(self):
        logger.info("Load Modify action triggered")
        if self.filename is not None:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Load",
                "An image is already loaded. Submit or drop first."
            )
            return

        self._set_firebase_loading(True, "Loading modify task...")
        worker = LoadTaskWorker(
            mode=self.current_mode,
            user_id=self.current_user_id,
            processing_dir=self.processing_dir,
            source_statuses=[TaskStatus.MODIFY],
            user_filter_field='workerId',
            parent=self,
        )
        worker.finished.connect(self._on_load_task_finished)
        worker.error.connect(self._on_firebase_error)
        self._active_worker = worker
        worker.start()

    def loadPostponeTaskAction(self):
        logger.info("Load Postpone action triggered")
        if self.filename is not None:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Load",
                "An image is already loaded. Submit or drop first."
            )
            return

        self._set_firebase_loading(True, "Loading postponed tasks...")
        worker = LoadPostponeWorker(
            user_id=self.current_user_id,
            processing_dir=self.processing_dir,
            parent=self,
        )
        worker.finished.connect(self._on_load_postpone_list_finished)
        worker.error.connect(self._on_firebase_error)
        self._active_worker = worker
        worker.start()

    def loadReadyGtTaskAction(self):
        logger.info("Load Ready GT action triggered")
        if self.filename is not None:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Load",
                "An image is already loaded. Submit or drop first."
            )
            return

        self._set_firebase_loading(True, "Loading Ready GT task...")
        worker = LoadTaskWorker(
            mode=self.current_mode,
            user_id=self.current_user_id,
            processing_dir=self.processing_dir,
            source_statuses=[TaskStatus.READY_GT],
            parent=self,
        )
        worker.finished.connect(self._on_load_ready_gt_finished)
        worker.error.connect(self._on_firebase_error)
        self._active_worker = worker
        worker.start()

    def submitTaskAction(self):
        logger.info("Submit Task action triggered")

        if self.filename is None:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Submit", "No image loaded."
            )
            return

        if not self.current_doc_id:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Submit",
                "No Firebase document associated with this task."
            )
            return

        # Confirmation dialog
        if not len(self.labelList):
            reply = QtWidgets.QMessageBox.question(
                self,
                "Confirm Submission",
                "No annotations have been made on this image.\n"
                "Do you still want to submit?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
        else:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Confirm Submission",
                "Do you want to submit this task?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

        if reply == QtWidgets.QMessageBox.No:
            return

        # Save file locally first
        self.saveFile()

        # Delete load time file
        if self.filename:
            load_time_file = self._get_load_time_file_path(self.filename)
            if os.path.exists(load_time_file):
                try:
                    os.remove(load_time_file)
                except Exception as e:
                    logger.warning(f"Failed to delete load time file: {e}")

        basename = os.path.splitext(os.path.basename(self.filename))[0]

        self._set_firebase_loading(True, "Uploading and submitting task...")
        worker = SubmitTaskWorker(
            doc_id=self.current_doc_id,
            current_status=self.current_task_status,
            processing_dir=self.processing_dir,
            basename=basename,
            mode=self.current_mode,
            user_id=self.current_user_id or '',
            parent=self,
        )
        worker.finished.connect(self._on_submit_finished)
        worker.error.connect(self._on_firebase_error)
        self._active_worker = worker
        worker.start()

    def postponeTaskAction(self):
        logger.info("Postpone Task action triggered")

        if not self.current_doc_id:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Postpone",
                "No Firebase document associated with this task."
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Postpone Task",
            "Do you want to postpone this task?\n"
            "You can resume it later.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        # Save current file
        self.saveFile()
        basename = os.path.splitext(os.path.basename(self.filename))[0]

        self._set_firebase_loading(True, "Postponing task...")
        worker = PostponeTaskWorker(
            doc_id=self.current_doc_id,
            user_id=self.current_user_id,
            processing_dir=self.processing_dir,
            basename=basename,
            parent=self,
        )
        worker.finished.connect(self._on_postpone_finished)
        worker.error.connect(self._on_firebase_error)
        self._active_worker = worker
        worker.start()

    def dropTaskAction(self):
        logger.info("Drop Task action triggered")

        if not self.current_doc_id:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Drop",
                "No Firebase document associated with this task."
            )
            return

        # Check drop count limit
        drop_count = self._check_drop_count()
        if drop_count >= 3:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Drop Task",
                "You have exceeded the daily drop limit."
            )
            return

        reply = QtWidgets.QMessageBox.warning(
            self,
            "Drop Task",
            "Do you want to drop this task?\n"
            "Your work will not be saved and the task "
            "will be returned to the pool.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        self._set_firebase_loading(True, "Dropping task...")
        worker = DropTaskWorker(
            doc_id=self.current_doc_id,
            mode=self.current_mode,
            parent=self,
        )
        worker.finished.connect(self._on_drop_finished)
        worker.error.connect(self._on_firebase_error)
        self._active_worker = worker
        worker.start()

    def discardTaskAction(self):
        logger.info("Discard Task action triggered")

        if not self.current_doc_id:
            QtWidgets.QMessageBox.warning(
                self, "Cannot Discard",
                "No Firebase document associated with this task."
            )
            return

        discard_dialog = DiscardDialog(self)
        if discard_dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        reason = discard_dialog.get_discard_reason()
        logger.info(f"Discard reason: {reason}")

        self._set_firebase_loading(True, "Discarding task...")
        worker = DiscardTaskWorker(
            doc_id=self.current_doc_id,
            discard_reason=reason,
            parent=self,
        )
        worker.finished.connect(self._on_discard_finished)
        worker.error.connect(self._on_firebase_error)
        self._active_worker = worker
        worker.start()

    # ============ Firebase Callback Handlers ============

    def _on_load_task_finished(self, result):
        self._set_firebase_loading(False)

        if not result.get('found'):
            QtWidgets.QMessageBox.information(
                self, "No Task Available",
                "No tasks available for your current mode."
            )
            return

        self.current_doc_id = result.get('doc_id')
        self.current_task_status = result.get('next_status')
        self.current_document = result.get('document')

        local_image_path = result.get('local_image_path', '')
        if local_image_path and os.path.exists(local_image_path):
            self.loadFile(local_image_path)
            # Set labels for this classType
            json_path = os.path.splitext(local_image_path)[0] + '.json'
            target_class = self.get_target_class(json_path)
            if target_class:
                self.choose_labels_class(target_class)
            logger.info(
                f"Task loaded: doc_id={self.current_doc_id}, "
                f"status={self.current_task_status}"
            )
        else:
            QtWidgets.QMessageBox.warning(
                self, "Load Failed",
                "Downloaded image file not found."
            )
            self._reset_firebase_state()

    def _on_load_postpone_list_finished(self, result):
        self._set_firebase_loading(False)

        if not result.get('found'):
            QtWidgets.QMessageBox.information(
                self, "No Postponed Tasks",
                "No postponed tasks found."
            )
            return

        documents = result.get('documents', [])
        image_names = [d.get('imageName', '') for d in documents]

        # Show selection dialog with QListWidget
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Select Postponed Task")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)
        layout = QtWidgets.QVBoxLayout(dialog)

        label = QtWidgets.QLabel("Select a task to restore:")
        layout.addWidget(label)

        list_widget = QtWidgets.QListWidget()
        for name in image_names:
            list_widget.addItem(name)
        list_widget.setCurrentRow(0)
        list_widget.itemDoubleClicked.connect(dialog.accept)
        layout.addWidget(list_widget)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QtWidgets.QPushButton("Load")
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        current = list_widget.currentItem()
        if not current:
            return
        item = current.text()

        # Find matching document
        selected_doc = None
        for d in documents:
            if d.get('imageName') == item:
                selected_doc = d
                break

        if not selected_doc:
            return

        # Restore postponed task
        self._set_firebase_loading(True, "Restoring postponed task...")
        worker = RestorePostponeWorker(
            doc=selected_doc,
            user_id=self.current_user_id,
            processing_dir=self.processing_dir,
            parent=self,
        )
        worker.finished.connect(self._on_restore_postpone_finished)
        worker.error.connect(self._on_firebase_error)
        self._active_worker = worker
        worker.start()

    def _on_restore_postpone_finished(self, result):
        self._set_firebase_loading(False)

        if not result.get('found'):
            QtWidgets.QMessageBox.warning(
                self, "Restore Failed",
                "Failed to restore postponed task."
            )
            return

        self.current_doc_id = result.get('doc_id')
        self.current_task_status = TaskStatus.PROCESSING.value
        self.current_document = result.get('document')

        local_image_path = result.get('local_image_path', '')
        if local_image_path and os.path.exists(local_image_path):
            self.loadFile(local_image_path)
            # Set labels for this classType
            json_path = os.path.splitext(local_image_path)[0] + '.json'
            target_class = self.get_target_class(json_path)
            if target_class:
                self.choose_labels_class(target_class)
            logger.info(f"Postponed task restored: {self.current_doc_id}")
        else:
            QtWidgets.QMessageBox.warning(
                self, "Load Failed",
                "Restored image file not found."
            )
            self._reset_firebase_state()

    def _on_load_ready_gt_finished(self, result):
        self._set_firebase_loading(False)

        if not result.get('found'):
            QtWidgets.QMessageBox.information(
                self, "No Ready GT Task",
                "No Ready GT tasks available."
            )
            return

        self.current_doc_id = result.get('doc_id')
        self.current_task_status = result.get('next_status')
        self.current_document = result.get('document')

        local_image_path = result.get('local_image_path', '')
        if local_image_path and os.path.exists(local_image_path):
            self.loadFile(local_image_path)
            logger.info(
                f"Ready GT task loaded: doc_id={self.current_doc_id}"
            )
        else:
            QtWidgets.QMessageBox.warning(
                self, "Load Failed",
                "Downloaded image file not found."
            )
            self._reset_firebase_state()

    def _on_submit_finished(self, result):
        self._set_firebase_loading(False)

        QtWidgets.QMessageBox.information(
            self, "Submitted",
            f"Task submitted successfully.\n"
            f"Status: {result.get('next_status', 'unknown')}"
        )

        self._clear_session_info()
        self._cleanup_processing_files()
        self._reset_firebase_state()
        self.comment_widget.clear_comments()
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def _on_postpone_finished(self, result):
        self._set_firebase_loading(False)

        QtWidgets.QMessageBox.information(
            self, "Postponed", "Task postponed successfully."
        )

        self._clear_session_info()
        self._cleanup_processing_files()
        self._reset_firebase_state()
        self.resetState()

    def _on_drop_finished(self, result):
        self._set_firebase_loading(False)

        self._clear_session_info()
        self._cleanup_processing_files()
        self._reset_firebase_state()
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

        QtWidgets.QMessageBox.information(
            self, "Dropped",
            "Task dropped and returned to task pool."
        )

    def _on_discard_finished(self, result):
        self._set_firebase_loading(False)

        self._clear_session_info()
        self._cleanup_processing_files()
        self._reset_firebase_state()
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

        QtWidgets.QMessageBox.information(
            self, "Discarded",
            "Task discarded successfully."
        )

    # ============ Firebase Helper Methods ============

    def _set_firebase_loading(self, loading, message=""):
        if loading:
            QtWidgets.QApplication.setOverrideCursor(
                QtGui.QCursor(Qt.WaitCursor)
            )
            self.statusBar().showMessage(message)
            # Disable load/submit buttons during operation
            self.actions.loadTask.setEnabled(False)
            self.actions.loadModifyTask.setEnabled(False)
            self.actions.loadPostponeTask.setEnabled(False)
            self.actions.loadReadyGtTask.setEnabled(False)
            self.actions.submitTask.setEnabled(False)
        else:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.statusBar().showMessage("")
            self.actions.loadTask.setEnabled(True)
            self.actions.loadModifyTask.setEnabled(True)
            self.actions.loadPostponeTask.setEnabled(True)
            self.actions.loadReadyGtTask.setEnabled(True)

    def _on_firebase_error(self, msg):
        self._set_firebase_loading(False)
        logger.error(f"Firebase error: {msg}")
        QtWidgets.QMessageBox.critical(
            self, "Firebase Error",
            f"An error occurred:\n{msg}\n\nPlease try again."
        )

    def _reset_firebase_state(self):
        self.current_doc_id = None
        self.current_task_status = None
        self.current_document = None
        self._active_worker = None

    def _cleanup_processing_files(self):
        if not self.filename:
            return
        basename = os.path.splitext(os.path.basename(self.filename))[0]
        pattern = os.path.join(self.processing_dir, f"{basename}*")
        for f in glob.glob(pattern):
            try:
                os.remove(f)
                logger.info(f"Cleaned up: {f}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {f}: {e}")

        # Remove generated image directories
        for dirname in ("masked_image", "overlayed_image"):
            dirpath = os.path.join(self.processing_dir, dirname)
            if os.path.isdir(dirpath):
                try:
                    shutil.rmtree(dirpath)
                    logger.info(f"Cleaned up directory: {dirpath}")
                except Exception as e:
                    logger.warning(
                        f"Failed to cleanup {dirpath}: {e}"
                    )

    # ============ Timer Methods ============

    def _get_load_time_file_path(self, image_path: str) -> str:
        if not image_path:
            return ""
        base_path = os.path.splitext(image_path)[0]
        return base_path + "_load_time.txt"

    def _startDeadlineTimer(self, image_path: str):

        load_time_file = self._get_load_time_file_path(image_path)

        # Read existing load time file if exists (Persist after restart)
        if os.path.exists(load_time_file):
            try:
                with open(load_time_file, "r", encoding="utf-8") as f:
                    load_time_str = f.read().strip()
                    load_time = datetime.datetime.fromisoformat(load_time_str)
                    logger.info(f"Loaded existing load time: {load_time}")
            except Exception as e:
                logger.warning(f"Failed to read load time file: {e}")
                load_time = datetime.datetime.now()
        else:
            # Record current time in file if newly loaded
            load_time = datetime.datetime.now()
            try:
                with open(load_time_file, "w", encoding="utf-8") as f:
                    f.write(load_time.isoformat())
                logger.info(f"Saved load time: {load_time}")
            except Exception as e:
                logger.warning(f"Failed to write load time file: {e}")

        # Deadline = Load time + 48 hours
        self.deadline = load_time + datetime.timedelta(hours=48)

        # Start timer (Update every 1 second)
        self.deadline_timer.start(1000)
        self._updateDeadlineTimer()  # Update immediately once

    def _updateDeadlineTimer(self):
        if not self.deadline:
            return

        remaining = self.deadline - datetime.datetime.now()
        remaining_seconds = int(remaining.total_seconds())

        if hasattr(self, 'task_info_widget') and self.task_info_widget:
            self.task_info_widget.set_remaining_time(remaining_seconds)

    def _stopDeadlineTimer(self):
        self.deadline_timer.stop()
        self.deadline = None

        # Reset only timer in TaskInfoWidget (Keep mode badge)
        if hasattr(self, 'task_info_widget') and self.task_info_widget:
            # Reset timer to "--:--:--"
            self.task_info_widget.timer_label.setText("--:--:--")
            self.task_info_widget.timer_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #4CAF50;
                    padding: 4px 8px;
                }
            """)

    # ============ Session Management Methods ============

    def _get_session_file_path(self, image_filename: str) -> str:
        if not image_filename:
            return ""
        basename = os.path.splitext(os.path.basename(image_filename))[0]
        return os.path.join(self.processing_dir, f"{basename}_session.json")

    def _save_session_info(self, image_filename: str):
        session_file = self._get_session_file_path(image_filename)
        if not session_file:
            return

        session_data = {
            "image_filename": os.path.basename(image_filename),
            "load_time": datetime.datetime.now().isoformat(),
            "mode": self.current_mode,
            "user_id": self.current_user_id,
            "doc_id": self.current_doc_id,
            "task_status": self.current_task_status,
        }

        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Session info saved: {session_data}")
        except Exception as e:
            logger.warning(f"Failed to save session info: {e}")

    def _load_session_info(self):
        # Find all *_session.json files in processing directory
        session_pattern = os.path.join(self.processing_dir, "*_session.json")
        session_files = glob.glob(session_pattern)

        if not session_files:
            return None

        # Select latest session file (Based on modification time)
        latest_session_file = max(session_files, key=os.path.getmtime)

        try:
            with open(latest_session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            logger.info(f"Session info loaded from {latest_session_file}: {session_data}")
            return session_data
        except Exception as e:
            logger.warning(f"Failed to load session info: {e}")
            return None

    def _clear_session_info(self, image_filename=None):
        if image_filename is None:
            image_filename = self.filename

        if not image_filename:
            return

        session_file = self._get_session_file_path(image_filename)
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                logger.info(f"Session info cleared: {session_file}")
            except Exception as e:
                logger.warning(f"Failed to clear session info: {e}")

    def _move_files_to_postpone(self, image_filename: str):
        if not image_filename:
            return

        # Create user-specific postpone directory
        user_postpone_dir = os.path.join(self.postpone_dir, self.current_user_id)
        os.makedirs(user_postpone_dir, exist_ok=True)

        # Extract basename
        basename = os.path.splitext(os.path.basename(image_filename))[0]

        # Find all files with same basename in processing directory
        pattern = os.path.join(self.processing_dir, f"{basename}.*")
        files_to_move = glob.glob(pattern)

        # Include session file
        session_file = self._get_session_file_path(image_filename)
        if os.path.exists(session_file) and session_file not in files_to_move:
            files_to_move.append(session_file)

        moved_count = 0
        for file_path in files_to_move:
            try:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(user_postpone_dir, filename)

                # Move file
                shutil.move(file_path, dest_path)
                logger.info(f"Moved to postpone/{self.current_user_id}: {filename}")
                moved_count += 1
            except Exception as e:
                logger.warning(f"Failed to move file {file_path}: {e}")

        logger.info(f"Postpone completed: {moved_count} files moved to user directory")
    def _restore_postponed_files(self, image_filename: str):
        if not image_filename:
            return

        # User-specific postpone directory
        user_postpone_dir = os.path.join(self.postpone_dir, self.current_user_id)

        # Extract basename
        basename = os.path.splitext(image_filename)[0]

        # Find all files with same basename in postpone directory
        pattern = os.path.join(user_postpone_dir, f"{basename}.*")
        files_to_restore = glob.glob(pattern)

        if not files_to_restore:
            QtWidgets.QMessageBox.warning(
                self,
                "File Not Found",
                f"Postponed file not found: {image_filename}"
            )
            return

        restored_count = 0
        restored_image_path = None

        for file_path in files_to_restore:
            try:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(self.processing_dir, filename)

                # Move file (Restore)
                shutil.move(file_path, dest_path)
                logger.info(f"Restored from postpone: {filename}")
                restored_count += 1

                # Save image file path
                if filename == image_filename:
                    restored_image_path = dest_path

            except Exception as e:
                logger.warning(f"Failed to restore file {file_path}: {e}")

        logger.info(f"Restore completed: {restored_count} files restored")

        # Load restored image
        if restored_image_path and os.path.exists(restored_image_path):
            self.loadFile(restored_image_path)
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Load Failed",
                "Image file not found."
            )

    def _check_drop_count(self) -> int:
        # Mock implementation: Always return 0 (Can be changed for testing)
        # TODO: Replace with code below after Firebase integration
        # from firebase_admin import firestore
        # db = firestore.client()
        # user_ref = db.collection('users').document(self.current_user_id)
        # user_doc = user_ref.get()
        # if user_doc.exists:
        #     return user_doc.to_dict().get('drop_count', 0)
        # return 0
        
        logger.info(f"Checking drop count for user: {self.current_user_id}")
        return 0  # Mock: Return 0 until actual Firebase integration
