import logging
import traceback
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QCheckBox, QHBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from utils.asc_utils import apply_smoothing
import mplcursors
import matplotlib.colors as mcolors
import numpy as np

class PlotArea(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.cursor = None
        self.show_cursor = True
        self.show_legend = True
        self.setup_ui()

    def setup_ui(self):
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Add checkboxes for cursor and legend toggle
        checkbox_layout = QHBoxLayout()
        self.cursor_checkbox = QCheckBox("Show Cursor")
        self.cursor_checkbox.setChecked(True)
        self.cursor_checkbox.stateChanged.connect(self.toggle_cursor)
        self.legend_checkbox = QCheckBox("Show Legend")
        self.legend_checkbox.setChecked(True)
        self.legend_checkbox.stateChanged.connect(self.toggle_legend)
        checkbox_layout.addWidget(self.cursor_checkbox)
        checkbox_layout.addWidget(self.legend_checkbox)

        self.layout.addLayout(checkbox_layout)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)

    def toggle_cursor(self, state):
        self.show_cursor = bool(state)
        self.update_plot()

    def toggle_legend(self, state):
        self.show_legend = bool(state)
        self.update_plot()

    def update_plot(self):
        # This method should be called whenever the plot needs to be updated
        # It will use the current state of show_cursor and show_legend
        if hasattr(self, 'last_plot_params'):
            self.plot_data(**self.last_plot_params)

    def plot_data(self, df, x_column, y_columns, smoothing_params, limit_lines=[]):
        try:
            logging.info(f"Plotting data: x={x_column}, y={y_columns}")
            self.figure.clear()

            ax = self.figure.add_subplot(111)
            axes = [ax]

            base_colors = ['blue', 'red', 'green']
            y_columns = y_columns[:3]  # Limit to max 3 Y-axes

            lines = []  # Store line objects for cursor

            for i, (y_column, base_color) in enumerate(zip(y_columns, base_colors)):
                logging.debug(f"Plotting column: {y_column}")
                if i > 0:
                    new_ax = ax.twinx()
                    new_ax.spines['right'].set_position(('axes', 1 + 0.1 * (i-1)))
                    axes.append(new_ax)
                else:
                    new_ax = ax

                x_data = df[x_column]
                y_data = df[y_column]

                if smoothing_params['apply']:
                    original_color = mcolors.to_rgba(base_color, alpha=0.3)
                    smoothed_color = mcolors.to_rgba(base_color, alpha=1.0)
                else:
                    original_color = base_color

                line, = new_ax.plot(x_data, y_data, color=original_color, label=y_column)
                lines.append(line)

                if smoothing_params['apply']:
                    logging.debug(f"Applying smoothing: {smoothing_params}")
                    y_smoothed = apply_smoothing(
                        y_data,
                        method=smoothing_params['method'],
                        window_length=smoothing_params['window_length'],
                        poly_order=smoothing_params['poly_order'],
                        sigma=smoothing_params['sigma']
                    )
                    smooth_line, = new_ax.plot(x_data, y_smoothed, color=smoothed_color, label=f'{y_column} (Smoothed)')
                    lines.append(smooth_line)

                new_ax.set_ylabel(y_column, color=base_color)
                new_ax.tick_params(axis='y', colors=base_color)
                if self.show_legend:
                    new_ax.legend(loc='upper left')

            ax.set_xlabel(x_column)
            ax.set_title('Multi-column plot')

            # Add limit lines
            for line in limit_lines:
                if line['type'] == 'vertical':
                    ax.axvline(x=line['value'], color='black', linestyle='--', label=f'Vertical Line at x={line["value"]}')
                else:
                    ax.axhline(y=line['value'], color='black', linestyle='--', label=f'Horizontal Line at y={line["value"]}')

            self.figure.tight_layout()

            # Add snapping cursor if enabled
            if self.show_cursor:
                self.cursor = mplcursors.cursor(lines, hover=True)

                @self.cursor.connect("add")
                def on_add(sel):
                    x, y = sel.target
                    ax = sel.artist.axes
                    xlabel = ax.get_xlabel()
                    ylabel = ax.get_ylabel()
                    sel.annotation.set_text(f"{xlabel}: {x:.2f}\n{ylabel}: {y:.2f}")
                    sel.annotation.get_bbox_patch().set(fc="white", alpha=0.8)
            else:
                if self.cursor:
                    self.cursor.remove()
                    self.cursor = None

            self.canvas.draw()
            logging.info("Plot completed successfully")

            # Store the last plot parameters for later updates
            self.last_plot_params = {
                'df': df,
                'x_column': x_column,
                'y_columns': y_columns,
                'smoothing_params': smoothing_params,
                'limit_lines': limit_lines
            }

        except Exception as e:
            logging.error(f"Error in plot_data: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while plotting: {str(e)}")

    def apply_curve_fitting(self, x_data, y_data, fit_func, equation, fit_type):
        try:
            logging.info(f"Applying {fit_type} curve fitting to plot")
            ax = self.figure.gca()

            # Clear previous plots
            ax.clear()

            # Plot the original data
            ax.plot(x_data, y_data, 'b-', label='Original Data')

            # Generate points for the fitted curve
            x_fit = np.linspace(np.min(x_data), np.max(x_data), 500)
            y_fit = fit_func(x_fit)

            # Plot the fitted curve
            ax.plot(x_fit, y_fit, 'r-', label=f'Fitted Curve: {equation}')

            ax.legend()
            ax.set_title(f'Data with {fit_type} Fit')
            ax.set_xlabel('X')
            ax.set_ylabel('Y')

            self.canvas.draw()
            logging.info(f"{fit_type} curve fitting applied to plot successfully")
        except Exception as e:
            logging.error(f"Error in apply_curve_fitting: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while applying curve fit: {str(e)}")

    def clear(self):
        self.text_edit.clear()