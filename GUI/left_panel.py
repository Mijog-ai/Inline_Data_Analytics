# left_panel.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from GUI.components.axis_selection import AxisSelection
from GUI.components.smoothing_options import SmoothingOptions
from GUI.components.limit_lines import LimitLines
from GUI.components.data_filter import DataFilter
from GUI.components.curve_fitting import CurveFitting
from GUI.components.comment_box import CommentBox

class LeftPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        self.axis_selection = AxisSelection(self)
        self.smoothing_options = SmoothingOptions(self)
        self.limit_lines = LimitLines(self)
        self.data_filter = DataFilter(self)
        self.curve_fitting = CurveFitting(self)
        self.comment_box = CommentBox(self)

        self.layout.addWidget(self.axis_selection)
        self.layout.addWidget(self.data_filter)
        self.layout.addWidget(self.curve_fitting)
        self.layout.addWidget(self.smoothing_options)
        self.layout.addWidget(self.limit_lines)
        self.layout.addWidget(self.comment_box)
        self.layout.addStretch(1)

        # Initialize components as hidden
        self.smoothing_options.hide()
        self.limit_lines.hide()
        self.comment_box.hide()
        self.data_filter.hide()
        self.curve_fitting.hide()
