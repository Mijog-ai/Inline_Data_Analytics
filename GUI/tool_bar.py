from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtGui import QIcon

class ToolBar(QToolBar):
    def __init__(self, parent):
        super().__init__('Main', parent)
        self.setup_toolbar()

    def setup_toolbar(self):
        load_action = QAction(QIcon('icons/load.png'), 'Load File', self)
        load_action.triggered.connect(self.parent().load_file)
        self.addAction(load_action)

        save_data_action = QAction(QIcon('icons/save_data.png'), 'Save Data', self)
        save_data_action.triggered.connect(self.parent().save_data)
        self.addAction(save_data_action)

        save_plot_action = QAction(QIcon('icons/save_plot.png'), 'Save Plot', self)
        save_plot_action.triggered.connect(self.parent().save_plot)
        self.addAction(save_plot_action)
