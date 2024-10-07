import sys
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QFileDialog,
                             QComboBox, QCheckBox, QSlider, QLabel, QTableWidget, QTableWidgetItem, QSplitter,
                             QMessageBox,
                             QListWidget, QAbstractItemView)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
from nptdms import TdmsFile


class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MatplotlibCanvas, self).__init__(fig)
        self.setParent(parent)

        self.figure.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.figure.canvas.mpl_connect('button_press_event', self.on_click)

    def on_hover(self, event):
        if event.inaxes == self.axes:
            x, y = event.xdata, event.ydata
            self.axes.format_coord = lambda x, y: f'x={x:.2f}, y={y:.2f}'
            self.draw()

    def on_click(self, event):
        if event.inaxes == self.axes:
            x, y = event.xdata, event.ydata
            if hasattr(self, 'parent') and hasattr(self.parent, 'show_coordinates'):
                self.parent.show_coordinates(x, y)


class DataVisualizationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Format Data Visualization Tool")
        self.setGeometry(100, 100, 1600, 900)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.setup_ui()

    def setup_ui(self):
        # Left panel for controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems([".asc", ".csv", ".tdms"])
        left_layout.addWidget(QLabel("File Type:"))
        left_layout.addWidget(self.file_type_combo)

        self.load_button = QPushButton("Load File")
        self.load_button.clicked.connect(self.load_file)
        left_layout.addWidget(self.load_button)

        self.x_combo = QComboBox()
        left_layout.addWidget(QLabel("X-axis:"))
        left_layout.addWidget(self.x_combo)

        self.y_list = QListWidget()
        self.y_list.setSelectionMode(QAbstractItemView.MultiSelection)
        left_layout.addWidget(QLabel("Y-axis (select up to 3):"))
        left_layout.addWidget(self.y_list)

        self.smooth_check = QCheckBox("Apply Smoothing")
        left_layout.addWidget(self.smooth_check)

        self.smooth_method = QComboBox()
        self.smooth_method.addItems(['Mean Line', 'Savitzky-Golay', 'Gaussian Filter'])
        left_layout.addWidget(QLabel("Smoothing Method:"))
        left_layout.addWidget(self.smooth_method)

        self.window_slider = QSlider(Qt.Horizontal)
        self.window_slider.setRange(5, 500)
        self.window_slider.setValue(51)
        self.window_label = QLabel("Smoothing Window Size: 51")
        left_layout.addWidget(self.window_label)
        left_layout.addWidget(self.window_slider)
        self.window_slider.valueChanged.connect(self.update_window_label)

        self.poly_order_slider = QSlider(Qt.Horizontal)
        self.poly_order_slider.setRange(1, 5)
        self.poly_order_slider.setValue(3)
        self.poly_order_label = QLabel("Polynomial Order: 3")
        left_layout.addWidget(self.poly_order_label)
        left_layout.addWidget(self.poly_order_slider)
        self.poly_order_slider.valueChanged.connect(self.update_poly_order_label)

        self.sigma_slider = QSlider(Qt.Horizontal)
        self.sigma_slider.setRange(1, 100)
        self.sigma_slider.setValue(20)
        self.sigma_label = QLabel("Gaussian Sigma: 2.0")
        left_layout.addWidget(self.sigma_label)
        left_layout.addWidget(self.sigma_slider)
        self.sigma_slider.valueChanged.connect(self.update_sigma_label)

        self.update_button = QPushButton("Update Plot")
        self.update_button.clicked.connect(self.update_plot)
        left_layout.addWidget(self.update_button)

        left_layout.addStretch()

        # Right panel for plot and statistics
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.coordinate_label = QLabel("Click on the plot to show coordinates")
        right_layout.addWidget(self.coordinate_label)


        # Plot view
        self.plot_canvas = MatplotlibCanvas(self, width=5, height=4, dpi=100)
        self.toolbar = NavigationToolbar(self.plot_canvas, self)

        # Statistics table
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Statistic", "Value"])

        # Use QSplitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.plot_canvas)
        splitter.addWidget(plot_widget)
        splitter.addWidget(self.stats_table)
        splitter.setSizes([700, 200])  # Set initial sizes

        right_layout.addWidget(splitter)

        # Add panels to main layout
        self.layout.addWidget(left_panel, 1)
        self.layout.addWidget(right_panel, 4)

        # Set up the rectangle selector for zooming
        self.rect_selector = RectangleSelector(
            self.plot_canvas.axes,
            self.on_select,
            props=dict(facecolor='red', edgecolor='black', alpha=0.2, fill=True),
            button=[1],  # Left mouse button
            minspanx=5,
            minspany=5,
            spancoords='pixels',
            interactive=True
        )

    def on_select(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        self.plot_canvas.axes.set_xlim(min(x1, x2), max(x1, x2))
        self.plot_canvas.axes.set_ylim(min(y1, y2), max(y1, y2))
        self.plot_canvas.draw()

    def update_window_label(self, value):
        self.window_label.setText(f"Smoothing Window Size: {value}")

    def update_poly_order_label(self, value):
        self.poly_order_label.setText(f"Polynomial Order: {value}")

    def update_sigma_label(self, value):
        sigma = value / 10.0
        self.sigma_label.setText(f"Gaussian Sigma: {sigma:.1f}")

    def show_coordinates(self, x, y):
        self.coordinate_label.setText(f"Coordinates: x={x:.4f}, y={y:.4f}")


    def load_file(self):
        file_type = self.file_type_combo.currentText()
        file_name, _ = QFileDialog.getOpenFileName(self, f"Open {file_type} File", "",
                                                   f"{file_type[1:].upper()} Files (*{file_type})")
        if file_name:
            try:
                if file_type == ".asc":
                    self.df = self.load_and_process_asc_file(file_name)
                elif file_type == ".csv":
                    self.df = self.load_and_process_csv_file(file_name)
                elif file_type == ".tdms":
                    self.df = self.load_and_process_tdms_file(file_name)
                self.update_column_selectors()
                self.update_stats_table()
                QMessageBox.information(self, "Success", "File loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while loading the file: {str(e)}")

    def load_and_process_asc_file(self, file_name):
        with open(file_name, 'r') as file:
            content = file.read()

        lines = content.split('\n')

        # Find the start of the data
        data_start = 0
        for i, line in enumerate(lines):
            if line.startswith("Messzeit[s]"):
                data_start = i + 1
                break

        # Extract header and data
        header = lines[data_start - 1].split('\t')
        data = [line.split('\t') for line in lines[data_start:] if line.strip()]

        # Rename duplicate columns
        new_header = []
        seen = {}
        for i, item in enumerate(header):
            if item in seen:
                seen[item] += 1
                new_header.append(f"{item}_{seen[item]}")
            else:
                seen[item] = 0
                new_header.append(item)

        df = pd.DataFrame(data, columns=new_header)

        # Convert columns to appropriate types
        for col in df.columns:
            df[col] = df[col].apply(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def load_and_process_csv_file(self, file_name):
        df = pd.read_csv(file_name)
        return df

    def load_and_process_tdms_file(self, file_name):
        with TdmsFile.open(file_name) as tdms_file:
            # Get all groups in the file
            groups = tdms_file.groups()

            # Create a dictionary to store data from all groups
            data_dict = {}

            for group in groups:
                for channel in group.channels():
                    channel_name = f"{group.name}/{channel.name}"
                    data = channel[:]
                    data_dict[channel_name] = data

            # Find the maximum length of data
        max_length = max(len(data) for data in data_dict.values())

        # Pad shorter arrays with NaN
        for key in data_dict:
            if len(data_dict[key]) < max_length:
                pad_length = max_length - len(data_dict[key])
                data_dict[key] = np.pad(data_dict[key], (0, pad_length), 'constant', constant_values=np.nan)

        # Create DataFrame
        df = pd.DataFrame(data_dict)
        return df

    def update_column_selectors(self):
        if hasattr(self, 'df'):
            self.x_combo.clear()
            self.y_list.clear()
            self.x_combo.addItems(self.df.columns)
            self.y_list.addItems(self.df.columns)

    def update_stats_table(self):
        if hasattr(self, 'df'):
            stats = self.df.describe().transpose()
            self.stats_table.setRowCount(len(stats))
            for i, (index, row) in enumerate(stats.iterrows()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(str(index)))
                self.stats_table.setItem(i, 1, QTableWidgetItem(str(row['mean'])))
        self.stats_table.resizeColumnsToContents()

    def update_plot(self):
        if hasattr(self, 'df'):
            try:
                x_column = self.x_combo.currentText()
                y_columns = [item.text() for item in self.y_list.selectedItems()]

                if len(y_columns) > 3:
                    QMessageBox.warning(self, "Warning", "Please select up to 3 columns for Y-axis.")
                    return

                if not y_columns:
                    QMessageBox.warning(self, "Warning", "Please select at least one column for Y-axis.")
                    return

                smoothing_params = {
                    'apply': self.smooth_check.isChecked(),
                    'method': self.smooth_method.currentText().lower().replace(' ', '_'),
                    'window_length': self.window_slider.value(),
                    'poly_order': self.poly_order_slider.value(),
                    'sigma': self.sigma_slider.value() / 10.0
                }

                self.plot_data(self.df, x_column, y_columns, smoothing_params)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while updating the plot: {str(e)}")

    def plot_data(self, df, x_column, y_columns, smoothing_params):
        self.plot_canvas.figure.clear()

        # Create main axis
        ax1 = self.plot_canvas.figure.add_subplot(111)

        # Create list to hold all axes
        axes = [ax1]

        # Create additional y-axes if needed
        for i in range(1, len(y_columns)):
            ax = ax1.twinx()
            ax.spines['left'].set_position(('axes', -0.1 * i))  # Move spine to the left
            ax.yaxis.set_label_position('left')
            ax.yaxis.tick_left()
            axes.append(ax)

        colors = ['red', 'blue', 'green']

        for i, (y_column, ax, color) in enumerate(zip(y_columns, axes, colors)):
            x_data = df[x_column]
            y_data = df[y_column]

            # Plot original data
            ax.plot(x_data, y_data, label=f'{y_column} (Original)', color=color, alpha=0.3)

            if smoothing_params['apply']:
                y_smoothed = self.apply_smoothing(
                    y_data,
                    method=smoothing_params['method'],
                    window_length=smoothing_params['window_length'],
                    poly_order=smoothing_params['poly_order'],
                    sigma=smoothing_params['sigma']
                )
                ax.plot(x_data, y_smoothed, label=f'{y_column} (Smoothed)', color=color)

            ax.set_ylabel(y_column, color=color)
            ax.tick_params(axis='y', labelcolor=color)
            ax.legend(loc='upper left')

        # Adjust the layout to prevent overlapping
        self.plot_canvas.figure.tight_layout()

        # Move left spine back to original position for the main axis
        ax1.spines['left'].set_position(('axes', 0))

        ax1.set_xlabel(x_column)
        ax1.set_title(f'Multi-column plot')

        self.plot_canvas.draw()

    def apply_smoothing(self, data, method='savgol', window_length=21, poly_order=3, sigma=2):
        if window_length >= len(data):
            window_length = len(data) - 1
        if window_length % 2 == 0:
            window_length -= 1

        if method == 'mean_line':
            return data.rolling(window=window_length, center=True).mean()
        elif method == 'savitzky-golay':
            return savgol_filter(data, window_length, poly_order)
        elif method == 'gaussian_filter':
            return gaussian_filter1d(data, sigma=sigma)

def main():
    app = QApplication(sys.argv)
    window = DataVisualizationApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()