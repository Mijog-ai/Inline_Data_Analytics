from PyQt5.QtWidgets import QGroupBox, QFormLayout, QComboBox, QPushButton

class CurveFitting(QGroupBox):
    def __init__(self, parent):
        super().__init__("Curve Fitting", parent)
        self.layout = QFormLayout()
        self.setup_ui()

    def setup_ui(self):
        self.fit_type = QComboBox()
        self.fit_type.addItems(['Linear', 'Quadratic', 'Exponential'])
        self.layout.addRow("Fit Type:", self.fit_type)

        self.apply_fit_button = QPushButton("Apply Fit")
        self.apply_fit_button.clicked.connect(self.apply_fit)
        self.layout.addRow(self.apply_fit_button)

        self.setLayout(self.layout)

    def apply_fit(self):
        main_window = self.parent().parent()
        fit_type = self.fit_type.currentText()
        main_window.right_panel.plot_area.apply_curve_fitting(fit_type)