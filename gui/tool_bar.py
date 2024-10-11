# tool_bar.py
import logging
from PyQt5.QtWidgets import QToolBar, QAction, QLabel
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

class ToolBar(QToolBar):
    def __init__(self, parent):
        super().__init__('Main', parent)
        self.setup_toolbar()

    def setup_toolbar(self):
        load_action = QAction(QIcon('icons/load.png'), 'Load Data', self)
        load_action.triggered.connect(self.load_file_triggered)
        self.addAction(load_action)

        save_data_action = QAction(QIcon('icons/save_data.png'), 'Save Data', self)
        save_data_action.triggered.connect(self.parent().save_data)
        self.addAction(save_data_action)

        save_plot_action = QAction(QIcon('icons/save_plot.png'), 'Save Plot', self)
        save_plot_action.triggered.connect(self.parent().save_plot)
        self.addAction(save_plot_action)

        # Add a label to indicate drag and drop functionality
        self.addSeparator()
        drag_drop_label = QLabel("Drag and drop files here")
        drag_drop_label.setAlignment(Qt.AlignCenter)
        self.addWidget(drag_drop_label)

    def load_file_triggered(self):
        print("Load File menu item clicked")
        logging.info("Load File menu item clicked")
        if hasattr(self.parent(), 'load_file'):
            self.parent().load_file()
        else:
            print("MainWindow does not have load_file method")
            logging.error("MainWindow does not have load_file method")
