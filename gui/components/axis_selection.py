import traceback

from PyQt5.QtWidgets import QGroupBox, QFormLayout, QComboBox, QListWidget, QPushButton, QMessageBox, QMainWindow
import logging


class AxisSelection(QGroupBox):
    def __init__(self, parent):
        super().__init__("Axis Selection", parent)
        self.layout = QFormLayout()
        self.setup_ui()

    def setup_ui(self):
        self.x_combo = QComboBox()
        self.x_combo.currentIndexChanged.connect(self.on_selection_changed)
        self.layout.addRow("X-axis:", self.x_combo)

        self.y_list = QListWidget()
        self.y_list.setSelectionMode(QListWidget.MultiSelection)
        self.y_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.layout.addRow("Y-axis (select up to 3):", self.y_list)

        self.setLayout(self.layout)

    def update_options(self, columns):
        self.x_combo.clear()
        self.y_list.clear()
        self.x_combo.addItems(columns)
        self.y_list.addItems(columns)

    def on_selection_changed(self):
        """Automatically plot when axis selection changes"""
        try:
            # Traverse up the widget hierarchy to find the MainWindow
            main_window = self.get_main_window()
            if not main_window:
                logging.error("Could not find MainWindow")
                return

            # Check if data is loaded
            if not hasattr(main_window, 'df') or main_window.df is None:
                return

            x_column = self.x_combo.currentText()
            y_columns = [item.text() for item in self.y_list.selectedItems()]

            # Only plot if both X and at least one Y column are selected
            if not x_column or not y_columns:
                logging.debug("Insufficient axes selected, skipping plot")
                return

            # Limit to 3 Y columns
            if len(y_columns) > 3:
                y_columns = y_columns[:3]
                logging.warning(f"Limited Y columns to 3: {y_columns}")

            logging.info(f"Auto-plotting - X: {x_column}, Y: {y_columns}")
            smoothing_params = main_window.left_panel.smoothing_options.get_params()
            logging.debug(f"Smoothing params: {smoothing_params}")

            main_window.right_panel.plot_area.plot_data(
                main_window.df,
                x_column,
                y_columns,
                smoothing_params
            )
        except Exception as e:
            logging.error(f"Error in on_selection_changed: {str(e)}")
            logging.error(traceback.format_exc())

    def get_main_window(self):
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QMainWindow):
                return parent
            parent = parent.parent()
        return None

    def reset(self):
        self.x_combo.setCurrentIndex(0)
        self.y_list.clearSelection()