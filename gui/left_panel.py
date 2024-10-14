# left_panel.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
from gui.components.axis_selection import AxisSelection
from gui.components.smoothing_options import SmoothingOptions
from gui.components.limit_lines import LimitLines
from gui.components.data_filter import DataFilter
from gui.components.curve_fitting import CurveFitting
from gui.components.comment_box import CommentBox
import logging
from PyQt5.QtCore import pyqtSignal, QObject

class LeftPanel(QWidget):
    title_changed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        self.axis_selection = AxisSelection(self)
        # self.sampling_options = SamplingOptions(self)
        self.smoothing_options = SmoothingOptions(self)
        self.limit_lines = LimitLines(self)
        self.data_filter = DataFilter(self)
        self.curve_fitting = CurveFitting(self)
        self.comment_box = CommentBox(self)

        self.layout.addWidget(self.axis_selection)
        # self.layout.addWidget(self.sampling_options)
        self.layout.addWidget(self.data_filter)
        self.layout.addWidget(self.smoothing_options)
        self.layout.addWidget(self.limit_lines)
        self.layout.addWidget(self.curve_fitting)
        self.layout.addWidget(self.comment_box)
        self.layout.addStretch(1)

        # Add title input
        title_layout = QHBoxLayout()
        title_label = QLabel("Plot Title:")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter plot title")
        self.title_input.textChanged.connect(self.on_title_changed)
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_input)
        self.layout.addLayout(title_layout)

        # Initialize components as hidden
        self.smoothing_options.hide()
        self.limit_lines.hide()
        self.comment_box.hide()
        self.data_filter.hide()
        self.curve_fitting.hide()
        # Connect sampling options to main window
        # self.sampling_options.enable_sampling.stateChanged.connect(self.parent().update_sampling)
        # self.sampling_options.sampling_rate.valueChanged.connect(self.parent().update_sampling)

    def update_options(self, columns):
        self.axis_selection.update_options(columns)
        self.data_filter.update_columns(columns)

    def on_title_changed(self, text):
        logging.debug(f"Title changed to: {text}")
        try:
            self.title_changed.emit(text)
        except Exception as e:
            logging.error(f"Error emitting title_changed signal: {str(e)}")

    def get_plot_title(self):
        return self.title_input.text()

    def set_plot_title(self, title):
        self.title_input.setText(title)

