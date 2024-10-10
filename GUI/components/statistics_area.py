from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem

class StatisticsArea(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(["Statistic", "Mean", "Max", "Min", "Standard Deviation"])
        self.layout.addWidget(self.stats_table)

    def update_stats(self, df):
        if df is not None:
            stats = df.describe().transpose()
            self.stats_table.setRowCount(len(stats))
            for i, (index, row) in enumerate(stats.iterrows()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(str(index)))
                self.stats_table.setItem(i, 1, QTableWidgetItem(str(row['mean'])))
                self.stats_table.setItem(i, 2, QTableWidgetItem(str(row['max'])))
                self.stats_table.setItem(i, 3, QTableWidgetItem(str(row['min'])))
                self.stats_table.setItem(i, 4, QTableWidgetItem(str(row['std'])))
            self.stats_table.resizeColumnsToContents()