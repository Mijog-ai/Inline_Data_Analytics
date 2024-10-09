from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QInputDialog

class LimitLines(QGroupBox):
    def __init__(self, parent):
        super().__init__("Limit Lines", parent)
        self.layout = QVBoxLayout()
        self.limit_lines = []
        self.setup_ui()

    def setup_ui(self):
        self.add_vline_button = QPushButton("Add Vertical Line")
        self.add_vline_button.clicked.connect(lambda: self.add_limit_line('vertical'))
        self.layout.addWidget(self.add_vline_button)

        self.add_hline_button = QPushButton("Add Horizontal Line")
        self.add_hline_button.clicked.connect(lambda: self.add_limit_line('horizontal'))
        self.layout.addWidget(self.add_hline_button)

        self.clear_lines_button = QPushButton("Clear All Lines")
        self.clear_lines_button.clicked.connect(self.clear_limit_lines)
        self.layout.addWidget(self.clear_lines_button)

        self.setLayout(self.layout)

    def add_limit_line(self, line_type):
        value, ok = QInputDialog.getDouble(self, f"Add {line_type.capitalize()} Line", "Enter value:")
        if ok:
            self.limit_lines.append({'type': line_type, 'value': value})
            self.parent().parent().right_panel.plot_area.update_plot()

    def clear_limit_lines(self):
        self.limit_lines.clear()
        self.parent().parent().right_panel.plot_area.update_plot()

    def get_limit_lines(self):
        return self.limit_lines