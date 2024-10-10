from PyQt5.QtWidgets import QMenuBar, QAction

class MenuBar(QMenuBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_menu()

    def setup_menu(self):
        file_menu = self.addMenu('File')

        load_action = QAction('Load File', self)
        load_action.triggered.connect(self.parent().load_file)
        file_menu.addAction(load_action)

        save_data_action = QAction('Save Data', self)
        save_data_action.triggered.connect(self.parent().save_data)
        file_menu.addAction(save_data_action)

        save_plot_action = QAction('Save Plot', self)
        save_plot_action.triggered.connect(self.parent().save_plot)
        file_menu.addAction(save_plot_action)

        export_table_action = QAction('Export Table to Excel', self)
        export_table_action.triggered.connect(self.parent().export_table_to_excel)
        file_menu.addAction(export_table_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.parent().close)
        file_menu.addAction(exit_action)

