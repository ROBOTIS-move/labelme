import copy
import math
import sys

from qtpy import QtCore
from qtpy import QtGui

import labelme.utils


# TODO(unknown):
# - [opt] Store paths instead of creating new ones at each paint.


DEFAULT_LINE_COLOR = QtGui.QColor(0, 255, 0, 128)  # bf hovering
DEFAULT_FILL_COLOR = QtGui.QColor(0, 255, 0, 128)  # hovering
DEFAULT_SELECT_LINE_COLOR = QtGui.QColor(255, 255, 255)  # selected
DEFAULT_SELECT_FILL_COLOR = QtGui.QColor(0, 255, 0, 155)  # selected
DEFAULT_VERTEX_FILL_COLOR = QtGui.QColor(0, 255, 0, 255)  # hovering
DEFAULT_HVERTEX_FILL_COLOR = QtGui.QColor(255, 255, 255, 255)  # hovering


class Shape(object):

    # Render handles as squares
    P_SQUARE = 0

    # Render handles as circles
    P_ROUND = 1

    # Flag for the handles we would move if dragging
    MOVE_VERTEX = 0

    # Flag for all other handles on the curent shape
    NEAR_VERTEX = 1

    # The following class variables influence the drawing of all shape objects.
    line_color = DEFAULT_LINE_COLOR
    fill_color = DEFAULT_FILL_COLOR
    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR
    point_type = P_ROUND
    point_size = 8
    scale = 1.0
    label_font_size = 10

    def __init__(
        self,
        label=None,
        line_color=None,
        probability=None,
        shape_type=None,
        flags=None,
        group_id=None,
        paint_label=False,
        paint_probability=False,
    ):
        self.label = label
        self.group_id = group_id
        self.points = []
        self.corners = [QtCore.QPointF(0, 0), QtCore.QPointF(0, 0)]
        self.fill = False
        self.selected = False
        self.probability = probability
        self.shape_type = shape_type
        self.flags = flags
        self.other_data = {}
        self.paint_label = paint_label
        self.paint_probability = paint_probability

        self._highlightIndex = None
        self._highlightMode = self.NEAR_VERTEX
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (1.5, self.P_SQUARE),
        }

        self._closed = False

        if line_color is not None:
            # Override the class line_color attribute
            # with an object attribute. Currently this
            # is used for drawing the pending line a different color.
            self.line_color = line_color

        self.shape_type = shape_type

    @property
    def shape_type(self):
        return self._shape_type

    @shape_type.setter
    def shape_type(self, value):
        if value is None:
            value = "polygon"
        if value not in [
            "polygon",
            "rectangle",
            "point",
            "line",
            "circle",
            "linestrip",
        ]:
            raise ValueError("Unexpected shape_type: {}".format(value))
        self._shape_type = value

    def close(self):
        self._closed = True

    def addPoint(self, point):
        if self.points and point == self.points[0]:
            self.close()
        else:
            self.points.append(point)

    def updateCorners(self):
        if len(self.points) == 2:
            x1 = self.points[0].x()
            y1 = self.points[0].y()
            x2 = self.points[1].x()
            y2 = self.points[1].y()
            x2y1 = QtCore.QPointF(x2, y1)
            x1y2 = QtCore.QPointF(x1, y2)
            self.corners[0] = x2y1
            self.corners[1] = x1y2

    def updatePoints(self):
        x2 = self.corners[0].x()
        y1 = self.corners[0].y()
        x1 = self.corners[1].x()
        y2 = self.corners[1].y()
        x1y1 = QtCore.QPointF(x1, y1)
        x2y2 = QtCore.QPointF(x2, y2)
        self.points[0] = (x1y1)
        self.points[1] = x2y2

    def align_points(self):
        if len(self.points) == 2:
            x1y1, x2y2 = self.points
            x1 = x1y1.x()
            y1 = x1y1.y()
            x2 = x2y2.x()
            y2 = x2y2.y()

            if x2 < x1:
                aligned_x1 = x2
                aligned_x2 = x1
            else:
                aligned_x1 = x1
                aligned_x2 = x2

            if y2 < y1:
                aligned_y1 = y2
                aligned_y2 = y1
            else:
                aligned_y1 = y1
                aligned_y2 = y2
            self.points[0] = QtCore.QPointF(aligned_x1, aligned_y1)
            self.points[1] = QtCore.QPointF(aligned_x2, aligned_y2)

    def canAddPoint(self):
        return self.shape_type in ["polygon", "linestrip"]

    def popPoint(self):
        if self.points:
            return self.points.pop()
        return None

    def insertPoint(self, i, point):
        self.points.insert(i, point)

    def removePoint(self, i):
        self.points.pop(i)

    def isClosed(self):
        return self._closed

    def setOpen(self):
        self._closed = False

    def getRectFromLine(self, pt1, pt2):
        x1, y1 = pt1.x(), pt1.y()
        x2, y2 = pt2.x(), pt2.y()
        return QtCore.QRectF(x1, y1, x2 - x1, y2 - y1)

    def paint(self, painter):
        if self.points:
            color = (
                self.select_line_color if self.selected else self.line_color
            )
            pen = QtGui.QPen(color)
            # Try using integer sizes for smoother drawing(?)
            pen.setWidth(max(1, int(round(2.0 / self.scale))))
            painter.setPen(pen)

            line_path = QtGui.QPainterPath()
            vrtx_path = QtGui.QPainterPath()

            if self.shape_type == "rectangle":
                assert len(self.points) in [1, 2]
                if len(self.points) == 2:
                    rectangle = self.getRectFromLine(*self.points)
                    line_path.addRect(rectangle)
                for i in range(len(self.points)):
                    self.drawVertex(vrtx_path, i, self.points[i])
                for i in range(len(self.corners)):
                    self.drawVertex(vrtx_path, i + 2, self.corners[i])

                # Draw text at the top-left
                if self.paint_label:
                    min_x = sys.maxsize
                    min_y = sys.maxsize
                    min_y_label = int(1.25 * self.label_font_size)
                    for point in self.points:
                        min_x = min(min_x, point.x())
                        min_y = min(min_y, point.y())
                    if min_x != sys.maxsize and min_y != sys.maxsize:
                        font = QtGui.QFont()
                        font.setPointSize(int(self.label_font_size))
                        font.setBold(True)
                        painter.setFont(font)
                        if self.label is None:
                            self.label = ""
                        if min_y < min_y_label:
                            min_y += min_y_label
                        painter.drawText(int(min_x), int(min_y), self.label)

                # Draw text at the right-bottom
                if self.paint_probability and self.probability is not None:
                    min_x = 0
                    min_y = 0
                    min_y_label = int(1.25 * self.label_font_size)
                    for point in self.points:
                        min_x = max(min_x, point.x())
                        min_y = max(min_y, point.y())
                    if min_x != sys.maxsize and min_y != sys.maxsize:
                        font = QtGui.QFont()
                        font.setPointSize(self.label_font_size)
                        font.setBold(True)
                        painter.setFont(font)
                        min_x_label = int(7.5 * len(str(self.probability)))
                        if min_y < min_y_label:
                            min_y += min_y_label
                        min_x -= min_x_label
                        painter.drawText(int(min_x), int(min_y), str(self.probability))
            elif self.shape_type == "circle":
                assert len(self.points) in [1, 2]
                if len(self.points) == 2:
                    rectangle = self.getCircleRectFromLine(self.points)
                    line_path.addEllipse(rectangle)
                for i in range(len(self.points)):
                    self.drawVertex(vrtx_path, i, self.points[i])
            elif self.shape_type == "linestrip":
                line_path.moveTo(self.points[0])
                for i, p in enumerate(self.points):
                    line_path.lineTo(p)
                    self.drawVertex(vrtx_path, i, self.points[i])
            else:
                line_path.moveTo(self.points[0])
                # Uncommenting the following line will draw 2 paths
                # for the 1st vertex, and make it non-filled, which
                # may be desirable.
                # self.drawVertex(vrtx_path, 0)
                # Draw text at the top-left
                if self.paint_label:
                    min_y_label = int(1.0 * self.label_font_size)
                    (center_x, center_y) = self.calculate_polygon_center(self.points)
                    if center_x != sys.maxsize and center_y != sys.maxsize:
                        font = QtGui.QFont()
                        font.setPointSize(int(self.label_font_size))
                        font.setBold(True)
                        painter.setFont(font)
                        if self.label is None:
                            self.label = ""
                        if center_y < min_y_label:
                            center_y += min_y_label
                        center_ratio = 0.5
                        width_ratio = 0.8
                        x_offset = int(
                            len(self.label) * center_ratio * self.label_font_size * width_ratio)
                        painter.drawText(int(center_x) - x_offset, int(center_y), self.label)

                for i, p in enumerate(self.points):
                    line_path.lineTo(p)
                    self.drawVertex(vrtx_path, i, self.points[i])
                if self.isClosed():
                    line_path.lineTo(self.points[0])

            painter.drawPath(line_path)
            painter.drawPath(vrtx_path)
            painter.fillPath(vrtx_path, self._vertex_fill_color)
            if self.fill:
                color = (
                    self.select_fill_color
                    if self.selected
                    else self.fill_color
                )
                painter.fillPath(line_path, color)

    def calculate_polygon_center(self, qt_points):
        # Polygon 데이터의 center를계산
        points = [(point.x(), point.y()) for point in qt_points]
        n = len(points)
        area = 0.0001
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            area += x0 * y1 - x1 * y0
        area *= 0.5
        cx = 0
        cy = 0
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            factor = (x0 * y1 - x1 * y0)
            cx += (x0 + x1) * factor
            cy += (y0 + y1) * factor
        cx /= (6 * area)
        cy /= (6 * area)
        return (cx, cy)

    def drawVertex(self, path, i, point):
        d = self.point_size / self.scale
        shape = self.point_type
        if i == self._highlightIndex:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        if self._highlightIndex is not None:
            self._vertex_fill_color = self.hvertex_fill_color
        else:
            self._vertex_fill_color = self.vertex_fill_color
        if shape == self.P_SQUARE:
            if len(self.points) == 2 and self.shape_type == "rectangle":
                self.updateCorners()
            path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
        elif shape == self.P_ROUND:
            if self.shape_type == "rectangle":
                self.updateCorners()
            path.addEllipse(point, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"

    def nearestVertex(self, point, epsilon):
        min_distance = float("inf")
        min_i = None
        for i, p in enumerate(self.points + self.corners):
            dist = labelme.utils.distance(p - point)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                min_i = i
        return min_i

    def nearestEdge(self, point, epsilon):
        min_distance = float("inf")
        post_i = None
        for i in range(len(self.points)):
            if self.points[i - 1] == self.points[i]:
                continue
            line = [self.points[i - 1], self.points[i]]
            dist = labelme.utils.distancetoline(point, line)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                post_i = i
        return post_i

    def containsPoint(self, point):
        return self.makePath().contains(point)

    def getCircleRectFromLine(self, line):
        """Computes parameters to draw with `QPainterPath::addEllipse`"""
        if len(line) != 2:
            return None
        (c, point) = line
        r = line[0] - line[1]
        d = math.sqrt(math.pow(r.x(), 2) + math.pow(r.y(), 2))
        rectangle = QtCore.QRectF(c.x() - d, c.y() - d, 2 * d, 2 * d)
        return rectangle

    def makePath(self):
        if self.shape_type == "rectangle":
            path = QtGui.QPainterPath()
            if len(self.points) == 2:
                rectangle = self.getRectFromLine(*self.points)
                path.addRect(rectangle)
        elif self.shape_type == "circle":
            path = QtGui.QPainterPath()
            if len(self.points) == 2:
                rectangle = self.getCircleRectFromLine(self.points)
                path.addEllipse(rectangle)
        else:
            path = QtGui.QPainterPath(self.points[0])
            for p in self.points[1:]:
                path.lineTo(p)
        return path

    def boundingRect(self):
        return self.makePath().boundingRect()

    def moveBy(self, offset, pixmap):
        points = []
        for p in self.points:
            point = p + offset
            correct_x = point.x() >= 0 and point.x() < pixmap.width()
            correct_y = point.y() >= 0 and point.y() < pixmap.height()
            if correct_x and correct_y:
                points.append(point)
            else:
                return
        self.points = points
        if self.shape_type == "rectangle":
            self.align_points()
            self.updateCorners()

    def moveVertexBy(self, i, offset):
        if self.shape_type == "rectangle":
            if i < 2:
                self.points[i] = self.points[i] + offset
                self.updateCorners()
            else:
                self.corners[i - 2] = self.corners[i - 2] + offset
                self.updatePoints()
        else:
            self.points[i] = self.points[i] + offset

    def highlightVertex(self, i, action):
        """Highlight a vertex appropriately based on the current action

        Args:
            i (int): The vertex index
            action (int): The action
            (see Shape.NEAR_VERTEX and Shape.MOVE_VERTEX)
        """
        self._highlightIndex = i
        self._highlightMode = action

    def highlightClear(self):
        """Clear the highlighted point"""
        self._highlightIndex = None

    def copy(self):
        return copy.deepcopy(self)

    def __len__(self):
        return len(self.points)

    def __getitem__(self, key):
        return self.points[key]

    def __setitem__(self, key, value):
        self.points[key] = value
