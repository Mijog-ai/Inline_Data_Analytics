from PyQt5.QtWidgets import QGroupBox, QFormLayout, QComboBox, QListWidget, QPushButton, QMessageBox


class AxisSelection(QGroupBox):
    def __init__(self, parent):
        super().__init__("Axis Selection", parent)
        self.layout = QFormLayout()
        self.setup_ui()

    def setup_ui(self):
        self.x_combo = QComboBox()
        self.layout.addRow("X-axis:", self.x_combo)

        self.y_list = QListWidget()
        self.y_list.setSelectionMode(QListWidget.MultiSelection)
        self.layout.addRow("Y-axis (select up to 3):", self.y_list)

        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self.plot)
        self.layout.addRow(self.plot_button)

        self.setLayout(self.layout)

    def update_options(self, columns):
        self.x_combo.clear()
        self.y_list.clear()
        self.x_combo.addItems(columns)
        self.y_list.addItems(columns)

    def plot(self):
        main_window = self.parent().parent()
        x_column = self.x_combo.currentText()
        y_columns = [item.text() for item in self.y_list.selectedItems()]

        if not x_column or not y_columns:
            QMessageBox.warning(main_window, "Warning", "Please select X and Y axes.")
            return

        smoothing_params = main_window.left_panel.smoothing_options.get_params()
        main_window.right_panel.plot_area.plot_data(main_window.df, x_column, y_columns, smoothing_params)