from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
import hashlib
import pickle

class StatisticsArea(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self._stats_cache = {}  # Cache for computed statistics
        self._last_df_hash = None  # Hash of last dataframe to detect changes
        self.setup_ui()

    def setup_ui(self):
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(["Statistic", "Max", "Mean", "Min", "Std"])
        self.layout.addWidget(self.stats_table)

    def update_stats(self, df):
        """Update statistics with caching to avoid redundant calculations"""
        if df is not None:
            # Create a hash of the dataframe to detect if it has changed
            df_hash = hashlib.md5(pickle.dumps(df.values.tobytes())).hexdigest()

            # Check if we already computed stats for this exact dataframe
            if df_hash == self._last_df_hash and self._stats_cache:
                # Use cached statistics
                return

            # Compute statistics (only if data changed)
            stats = df.describe().transpose()
            self._last_df_hash = df_hash
            self._stats_cache = stats

            # Update table
            self.stats_table.setRowCount(len(stats))
            for i, (index, row) in enumerate(stats.iterrows()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(str(index)))
                self.stats_table.setItem(i, 1, QTableWidgetItem(f"{row['max']:.4f}"))
                self.stats_table.setItem(i, 2, QTableWidgetItem(f"{row['mean']:.4f}"))
                self.stats_table.setItem(i, 3, QTableWidgetItem(f"{row['min']:.4f}"))
                self.stats_table.setItem(i, 4, QTableWidgetItem(f"{row['std']:.4f}"))
            self.stats_table.resizeColumnsToContents()

    def get_stats(self):
        stats = {}
        for i in range(self.stats_table.rowCount()):
            statistic = self.stats_table.item(i, 0).text()
            stats[statistic] = {
                'mean': self.stats_table.item(i, 1).text(),
                'max': self.stats_table.item(i, 2).text(),
                'min': self.stats_table.item(i, 3).text(),
                'std': self.stats_table.item(i, 4).text()
            }
        return stats

    def set_stats(self, stats):
        self.stats_table.setRowCount(len(stats))
        for i, (statistic, values) in enumerate(stats.items()):
            self.stats_table.setItem(i, 0, QTableWidgetItem(str(statistic)))
            self.stats_table.setItem(i, 1, QTableWidgetItem(str(values['mean'])))
            self.stats_table.setItem(i, 2, QTableWidgetItem(str(values['max'])))
            self.stats_table.setItem(i, 3, QTableWidgetItem(str(values['min'])))
            self.stats_table.setItem(i, 4, QTableWidgetItem(str(values['std'])))
        self.stats_table.resizeColumnsToContents()

    def clear_stats(self):
        """Clear statistics and cache"""
        self.stats_table.setRowCount(0)
        self._stats_cache = {}
        self._last_df_hash = None