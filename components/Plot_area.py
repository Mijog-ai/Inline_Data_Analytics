from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import MultiCursor
from utils.asc_utils import apply_smoothing

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

    def plot_data(self, df, x_column, y_columns, smoothing_params):
        self.figure.clear()

        ax = self.figure.add_subplot(111)
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

        # Add cursor
        self.multi_cursor = MultiCursor(self.canvas, axes, color='r', lw=1, horizOn=True, vertOn=True)

        self.canvas.draw()