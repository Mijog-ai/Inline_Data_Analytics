from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt


class SheetSelectionDialog(QDialog):
    """Dialog for selecting Excel sheet to load."""

    def __init__(self, sheet_names, parent=None):
        super().__init__(parent)
        self.selected_sheet = None
        self.sheet_names = sheet_names
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Select Excel Sheet")
        self.setModal(True)
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        # Info label
        info_label = QLabel("This Excel file contains multiple sheets.\nPlease select which sheet to load:")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Sheet selection combo box
        self.sheet_combo = QComboBox()
        self.sheet_combo.addItems(self.sheet_names)
        layout.addWidget(QLabel("Sheet:"))
        layout.addWidget(self.sheet_combo)

        # Buttons
        button_layout = QHBoxLayout()

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_selection)
        self.ok_button.setDefault(True)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def accept_selection(self):
        self.selected_sheet = self.sheet_combo.currentText()
        self.accept()

    def get_selected_sheet(self):
        return self.selected_sheet