from PyQt5.QtWidgets import QGroupBox, QFormLayout, QComboBox, QLineEdit, QPushButton, QMessageBox

class DataFilter(QGroupBox):
    def __init__(self, parent):
        super().__init__("Data Filter", parent)
        self.layout = QFormLayout()
        self.setup_ui()

    def setup_ui(self):
        self.filter_column = QComboBox()
        self.layout.addRow("Column:", self.filter_column)

        self.filter_condition = QComboBox()
        self.filter_condition.addItems(['>', '<', '==', '>=', '<=', '!='])
        self.layout.addRow("Condition:", self.filter_condition)

        self.filter_value = QLineEdit()
        self.layout.addRow("Value:", self.filter_value)

        self.apply_filter_button = QPushButton("Apply Filter")
        self.apply_filter_button.clicked.connect(self.apply_filter)
        self.layout.addRow(self.apply_filter_button)

        self.setLayout(self.layout)

    def update_columns(self, columns):
        self.filter_column.clear()
        self.filter_column.addItems(columns)

    def apply_filter(self):
        main_window = self.parent().parent()
        column = self.filter_column.currentText()
        condition = self.filter_condition.currentText()
        value = self.filter_value.text()

        try:
            value = float(value)
        except ValueError:
            QMessageBox.warning(main_window, "Warning", "Please enter a valid numeric value for filtering.")
            return

        filter_expr = f"{column} {condition} {value}"
        main_window.df = main_window.df.query(filter_expr)
        main_window.update_ui_after_load()