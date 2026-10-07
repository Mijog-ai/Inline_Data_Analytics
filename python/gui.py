import sys
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
                             QTableWidget, QTableWidgetItem, QSplitter, QMessageBox,
                             QAction, QToolBar, QFormLayout, QPushButton, QInputDialog,
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QLabel, QMenu, QGroupBox, QListWidget, QLineEdit, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import MultiCursor
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit

from utils.asc_utils import load_and_process_asc_file, load_and_process_csv_file, load_and_process_tdms_file, apply_smoothing


class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MatplotlibCanvas, self).__init__(fig)
        self.setParent(parent)


class DataVisualizationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Format Data Visualization Tool")
        self.setGeometry(100, 100, 1600, 900)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.df = None
        self.x_column = None
        self.y_columns = []
        self.limit_lines = []

        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()

    def setup_ui(self):
        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self.setup_axis_selection())
        left_layout.addWidget(self.setup_smoothing_options())
        left_layout.addWidget(self.setup_limit_lines())
        left_layout.addWidget(self.setup_data_filter())
        left_layout.addWidget(self.setup_curve_fitting())
        left_layout.addWidget(self.setup_comment_box())
        left_layout.addStretch(1)

        # Right panel (plot and stats)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.plot_canvas = MatplotlibCanvas(self, width=5, height=4, dpi=100)
        self.toolbar = NavigationToolbar(self.plot_canvas, self)
        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.plot_canvas)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Statistic", "Value"])

        splitter = QSplitter(Qt.Vertical)
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.addWidget(self.plot_canvas)
        splitter.addWidget(plot_widget)
        splitter.addWidget(self.stats_table)
        splitter.setSizes([700, 200])

        right_layout.addWidget(splitter)

        # Add panels to main layout
        self.layout.addWidget(left_panel, 1)
        self.layout.addWidget(right_panel, 4)

    def setup_axis_selection(self):
        group_box = QGroupBox("Axis Selection")
        layout = QFormLayout()

        self.x_combo = QComboBox()
        layout.addRow("X-axis:", self.x_combo)

        self.y_list = QListWidget()
        self.y_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addRow("Y-axis (select up to 3):", self.y_list)

        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self.update_plot)
        layout.addRow(self.plot_button)

        group_box.setLayout(layout)
        return group_box

    def setup_smoothing_options(self):
        group_box = QGroupBox("Smoothing Options")
        layout = QFormLayout()

        self.smooth_check = QCheckBox("Apply Smoothing")
        layout.addRow(self.smooth_check)

        self.smooth_method = QComboBox()
        self.smooth_method.addItems(['Mean Line', 'Savitzky-Golay', 'Gaussian Filter'])
        layout.addRow("Smoothing Method:", self.smooth_method)

        self.window_size = QSpinBox()
        self.window_size.setRange(5, 500)
        self.window_size.setValue(51)
        layout.addRow("Window Size:", self.window_size)

        self.poly_order = QSpinBox()
        self.poly_order.setRange(1, 5)
        self.poly_order.setValue(3)
        layout.addRow("Polynomial Order:", self.poly_order)

        self.sigma = QDoubleSpinBox()
        self.sigma.setRange(0.1, 10.0)
        self.sigma.setValue(2.0)
        self.sigma.setSingleStep(0.1)
        layout.addRow("Gaussian Sigma:", self.sigma)

        group_box.setLayout(layout)
        return group_box

    def setup_limit_lines(self):
        group_box = QGroupBox("Limit Lines")
        layout = QFormLayout()

        self.add_vline_button = QPushButton("Add Vertical Line")
        self.add_vline_button.clicked.connect(lambda: self.add_limit_line('vertical'))
        layout.addRow(self.add_vline_button)

        self.add_hline_button = QPushButton("Add Horizontal Line")
        self.add_hline_button.clicked.connect(lambda: self.add_limit_line('horizontal'))
        layout.addRow(self.add_hline_button)

        self.clear_lines_button = QPushButton("Clear All Lines")
        self.clear_lines_button.clicked.connect(self.clear_limit_lines)
        layout.addRow(self.clear_lines_button)

        group_box.setLayout(layout)
        return group_box

    def setup_data_filter(self):
        group_box = QGroupBox("Data Filter")
        layout = QFormLayout()

        self.filter_column = QComboBox()
        layout.addRow("Column:", self.filter_column)

        self.filter_condition = QComboBox()
        self.filter_condition.addItems(['>', '<', '==', '>=', '<=', '!='])
        layout.addRow("Condition:", self.filter_condition)

        self.filter_value = QLineEdit()
        layout.addRow("Value:", self.filter_value)

        self.apply_filter_button = QPushButton("Apply Filter")
        self.apply_filter_button.clicked.connect(self.apply_filter)
        layout.addRow(self.apply_filter_button)

        group_box.setLayout(layout)
        return group_box

    def setup_curve_fitting(self):
        group_box = QGroupBox("Curve Fitting")
        layout = QFormLayout()

        self.fit_type = QComboBox()
        self.fit_type.addItems(['Linear', 'Quadratic', 'Exponential'])
        layout.addRow("Fit Type:", self.fit_type)

        self.apply_fit_button = QPushButton("Apply Fit")
        self.apply_fit_button.clicked.connect(self.apply_fit)
        layout.addRow(self.apply_fit_button)

        group_box.setLayout(layout)
        return group_box

    def setup_comment_box(self):
        group_box = QGroupBox("Comments")
        layout = QVBoxLayout()

        self.comment_box = QTextEdit()
        layout.addWidget(self.comment_box)

        group_box.setLayout(layout)
        return group_box

    def setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('File')

        load_action = QAction('Load File', self)
        load_action.triggered.connect(self.load_file)
        file_menu.addAction(load_action)

        save_data_action = QAction('Save Data', self)
        save_data_action.triggered.connect(self.save_data)
        file_menu.addAction(save_data_action)

        save_plot_action = QAction('Save Plot', self)
        save_plot_action.triggered.connect(self.save_plot)
        file_menu.addAction(save_plot_action)

        export_table_action = QAction('Export Table to Excel', self)
        export_table_action.triggered.connect(self.export_table_to_excel)
        file_menu.addAction(export_table_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def setup_toolbar(self):
        self.toolbar = self.addToolBar('Main')

        load_action = QAction(QIcon('icons/load.png'), 'Load File', self)
        load_action.triggered.connect(self.load_file)
        self.toolbar.addAction(load_action)

        save_data_action = QAction(QIcon('icons/save_data.png'), 'Save Data', self)
        save_data_action.triggered.connect(self.save_data)
        self.toolbar.addAction(save_data_action)

        save_plot_action = QAction(QIcon('icons/save_plot.png'), 'Save Plot', self)
        save_plot_action.triggered.connect(self.save_plot)
        self.toolbar.addAction(save_plot_action)

    def load_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "",
                                                   "All Files (*);;ASC Files (*.asc);;CSV Files (*.csv);;TDMS Files (*.tdms)")
        if file_name:
            try:
                file_extension = file_name.split('.')[-1].lower()
                if file_extension == 'asc':
                    self.df = load_and_process_asc_file(file_name)
                elif file_extension == 'csv':
                    self.df = load_and_process_csv_file(file_name)
                elif file_extension == 'tdms':
                    self.df = load_and_process_tdms_file(file_name)
                else:
                    raise ValueError(f"Unsupported file type: {file_extension}")

                self.update_stats_table()
                self.update_axis_selection()
                QMessageBox.information(self, "Success", "File loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while loading the file: {str(e)}")

    def update_axis_selection(self):
        self.x_combo.clear()
        self.y_list.clear()
        self.filter_column.clear()
        if self.df is not None:
            self.x_combo.addItems(self.df.columns)
            self.y_list.addItems(self.df.columns)
            self.filter_column.addItems(self.df.columns)

    def save_data(self):
        if self.df is None:
            QMessageBox.warning(self, "Warning", "No data to save. Please load a file first.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save Data", "", "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if file_name:
            try:
                if file_name.endswith('.csv'):
                    self.df.to_csv(file_name, index=False)
                elif file_name.endswith('.xlsx'):
                    self.df.to_excel(file_name, index=False)
                QMessageBox.information(self, "Success", "Data saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while saving the data: {str(e)}")

    def save_plot(self):
        if self.plot_canvas.figure.axes[0].lines == []:
            QMessageBox.warning(self, "Warning", "No plot to save. Please create a plot first.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save Plot", "", "PNG Files (*.png);;PDF Files (*.pdf)")
        if file_name:
            try:
                # Add comments to the plot
                comments = self.comment_box.toPlainText()
                if comments:
                    self.plot_canvas.figure.text(0.1, 0.01, comments, wrap=True, fontsize=8, va='bottom')

                self.plot_canvas.figure.savefig(file_name, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", "Plot saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while saving the plot: {str(e)}")

    def export_table_to_excel(self):
        if self.df is None:
            QMessageBox.warning(self, "Warning", "No data to export. Please load a file first.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Export Table to Excel", "", "Excel Files (*.xlsx)")
        if file_name:
            try:
                with pd.ExcelWriter(file_name) as writer:
                    self.df.to_excel(writer, sheet_name='Data', index=False)
                    stats = self.df.describe().transpose()
                    stats.to_excel(writer, sheet_name='Statistics')
                QMessageBox.information(self, "Success", "Table exported to Excel successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while exporting the table: {str(e)}")

    def apply_filter(self):
        if self.df is None:
            QMessageBox.warning(self, "Warning", "Please load a file first.")
            return

        column = self.filter_column.currentText()
        condition = self.filter_condition.currentText()
        value = self.filter_value.text()

        try:
            value = float(value)
        except ValueError:
            QMessageBox.warning(self, "Warning", "Please enter a valid numeric value for filtering.")
            return

        try:
            filter_expr = f"{column} {condition} {value}"
            filtered_df = self.df.query(filter_expr)

            if filtered_df.empty:
                QMessageBox.warning(self, "Warning",
                                    "The filter resulted in an empty dataset. Please adjust your filter criteria.")
                return

            self.df = filtered_df
            self.update_plot()
            self.update_stats_table()
            QMessageBox.information(self, "Success", "Filter applied successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while applying the filter: {str(e)}")

    def apply_fit(self):
        if self.df is None or not hasattr(self, 'x_column') or not self.y_columns:
            QMessageBox.warning(self, "Warning", "Please load data and create a plot first.")
            return

        fit_type = self.fit_type.currentText()
        x_data = self.df[self.x_column]

        try:
            for y_column in self.y_columns:
                y_data = self.df[y_column]

                if fit_type == 'Linear':
                    z = np.polyfit(x_data, y_data, 1)
                    p = np.poly1d(z)
                    self.plot_canvas.axes.plot(x_data, p(x_data), '--', label=f'Linear fit: y={z[0]:.2f}x + {z[1]:.2f}')
                elif fit_type == 'Quadratic':
                    z = np.polyfit(x_data, y_data, 2)
                    p = np.poly1d(z)
                    self.plot_canvas.axes.plot(x_data, p(x_data), '--',
                                               label=f'Quadratic fit: y={z[0]:.2f}x² + {z[1]:.2f}x + {z[2]:.2f}')
                elif fit_type == 'Exponential':
                    popt, _ = curve_fit(lambda t, a, b: a * np.exp(b * t), x_data, y_data)
                    self.plot_canvas.axes.plot(x_data, popt[0] * np.exp(popt[1] * x_data), '--',
                                               label=f'Exponential fit: y={popt[0]:.2f}e^({popt[1]:.2f}x)')

            self.plot_canvas.axes.legend()
            self.plot_canvas.draw()
            QMessageBox.information(self, "Success", "Curve fitting applied successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while applying curve fitting: {str(e)}")

    def update_plot(self):
        if self.df is None:
            QMessageBox.warning(self, "Warning", "Please load a file first.")
            return

        self.x_column = self.x_combo.currentText()
        self.y_columns = [item.text() for item in self.y_list.selectedItems()]

        if not self.x_column or not self.y_columns:
            QMessageBox.warning(self, "Warning", "Please select X and Y axes.")
            return

        try:
            smoothing_params = {
                'apply': self.smooth_check.isChecked(),
                'method': self.smooth_method.currentText().lower().replace(' ', '_'),
                'window_length': self.window_size.value(),
                'poly_order': self.poly_order.value(),
                'sigma': self.sigma.value()
            }

            self.plot_data(self.df, self.x_column, self.y_columns, smoothing_params)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while updating the plot: {str(e)}")

    def plot_data(self, df, x_column, y_columns, smoothing_params):
        try:
            self.plot_canvas.figure.clear()

            ax = self.plot_canvas.figure.add_subplot(111)
            axes = [ax]

            for i, y_column in enumerate(y_columns):
                if i > 0:
                    ax = ax.twinx()
                    ax.spines['right'].set_position(('axes', 1 + 0.1 * i))
                    axes.append(ax)

                x_data = df[x_column]
                y_data = df[y_column]

                ax.plot(x_data, y_data, label=f'{y_column} (Original)')

                if smoothing_params['apply']:
                    y_smoothed = apply_smoothing(
                        y_data,
                        method=smoothing_params['method'],
                        window_length=smoothing_params['window_length'],
                        poly_order=smoothing_params['poly_order'],
                        sigma=smoothing_params['sigma']
                    )
                    ax.plot(x_data, y_smoothed, label=f'{y_column} (Smoothed)')

                ax.set_ylabel(y_column)
                ax.legend()

            axes[0].set_xlabel(x_column)
            axes[0].set_title('Multi-column plot')

            # Add limit lines
            for line in self.limit_lines:
                if line['type'] == 'vertical':
                    axes[0].axvline(x=line['value'], color='r', linestyle='--',
                                    label=f'Vertical Line at x={line["value"]}')
                else:
                    axes[0].axhline(y=line['value'], color='r', linestyle='--',
                                    label=f'Horizontal Line at y={line["value"]}')

            # Add cursor
            self.multi_cursor = MultiCursor(self.plot_canvas, axes, color='r', lw=1, horizOn=True, vertOn=True)

            self.plot_canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while plotting data: {str(e)}")


    def add_limit_line(self, line_type):
        value, ok = QInputDialog.getDouble(self, f"Add {line_type.capitalize()} Line", "Enter value:")
        if ok:
            self.limit_lines.append({'type': line_type, 'value': value})
            self.update_plot()


    def clear_limit_lines(self):
        self.limit_lines.clear()
        self.update_plot()


    def apply_filter(self):
        if self.df is None:
            QMessageBox.warning(self, "Warning", "Please load a file first.")
            return

        column = self.filter_column.currentText()
        condition = self.filter_condition.currentText()
        value = self.filter_value.text()

        try:
            value = float(value)
        except ValueError:
            QMessageBox.warning(self, "Warning", "Please enter a valid numeric value for filtering.")
            return

        filter_expr = f"{column} {condition} {value}"
        self.df = self.df.query(filter_expr)
        self.update_plot()
        self.update_stats_table()


    def apply_fit(self):
        if self.df is None or not hasattr(self, 'x_column') or not self.y_columns:
            QMessageBox.warning(self, "Warning", "Please load data and create a plot first.")
            return

        fit_type = self.fit_type.currentText()
        x_data = self.df[self.x_column]

        for y_column in self.y_columns:
            y_data = self.df[y_column]

            if fit_type == 'Linear':
                z = np.polyfit(x_data, y_data, 1)
                p = np.poly1d(z)
                self.plot_canvas.axes.plot(x_data, p(x_data), '--', label=f'Linear fit: y={z[0]:.2f}x + {z[1]:.2f}')
            elif fit_type == 'Quadratic':
                z = np.polyfit(x_data, y_data, 2)
                p = np.poly1d(z)
                self.plot_canvas.axes.plot(x_data, p(x_data), '--',
                                           label=f'Quadratic fit: y={z[0]:.2f}x² + {z[1]:.2f}x + {z[2]:.2f}')
            elif fit_type == 'Exponential':
                popt, _ = curve_fit(lambda t, a, b: a * np.exp(b * t), x_data, y_data)
                self.plot_canvas.axes.plot(x_data, popt[0] * np.exp(popt[1] * x_data), '--',
                                           label=f'Exponential fit: y={popt[0]:.2f}e^({popt[1]:.2f}x)')

        self.plot_canvas.axes.legend()
        self.plot_canvas.draw()


    def update_stats_table(self):
        if self.df is not None:
            stats = self.df.describe().transpose()
            self.stats_table.setRowCount(len(stats))
            for i, (index, row) in enumerate(stats.iterrows()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(str(index)))
                self.stats_table.setItem(i, 1, QTableWidgetItem(str(row['mean'])))
            self.stats_table.resizeColumnsToContents()