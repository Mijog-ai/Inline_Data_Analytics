import logging
import traceback
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from utils.asc_utils import apply_smoothing
import mplcursors
import matplotlib.colors as mcolors


class PlotArea(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)

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
                    new_ax.spines['right'].set_visible(False)
                    new_ax.spines['left'].set_position(('axes', -0.1 * i))
                    new_ax.yaxis.set_label_position('left')
                    new_ax.yaxis.set_ticks_position('left')
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

                line, = new_ax.plot(x_data, y_data, color=original_color, label=f'{y_column} (Original)')
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

            # Add snapping cursor
            cursor = mplcursors.cursor(lines, hover=True)

            @cursor.connect("add")
            def on_add(sel):
                x, y = sel.target
                ax = sel.artist.axes
                xlabel = ax.get_xlabel()
                ylabel = ax.get_ylabel()
                sel.annotation.set_text(f"{xlabel}: {x:.2f}\n{ylabel}: {y:.2f}")
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.8)

            self.canvas.draw()
            logging.info("Plot completed successfully")
        except Exception as e:
            logging.error(f"Error in plot_data: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while plotting: {str(e)}")