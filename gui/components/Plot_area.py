import logging
import traceback
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from utils.asc_utils import apply_smoothing
import mplcursors
import matplotlib.colors as mcolors
import numpy as np
import matplotlib.pyplot as plt


class PlotArea(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.cursor = None
        self.show_cursor = True
        self.show_legend = True
        self.yaxis_approx_value_highlighter = True
        self.setup_ui()
        self.vertical_lines = []  # Changed to list to store multiple lines

        self.original_lines = []
        self.smoothed_lines = []
        self.current_title = ""

    def setup_ui(self):

        # Add title input and buttons
        title_layout = QHBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter plot title")
        self.set_title_button = QPushButton("Set Title")
        self.set_title_button.clicked.connect(self.set_title)
        # self.update_title_button = QPushButton("Update Title")
        # self.update_title_button.clicked.connect(self.update_title)
        title_layout.addWidget(self.title_input)
        title_layout.addWidget(self.set_title_button)
        # title_layout.addWidget(self.update_title_button)
        self.layout.addLayout(title_layout)

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

        self.highlighter_checkbox = QCheckBox("Highlight yaxis_values")
        self.highlighter_checkbox.setChecked(True)
        self.highlighter_checkbox.stateChanged.connect(self.toggle_highlighter)

        self.show_original_checkbox = QCheckBox("Show Original Data")
        self.show_original_checkbox.setChecked(True)
        self.show_original_checkbox.stateChanged.connect(self.toggle_original_data)

        checkbox_layout.addWidget(self.cursor_checkbox)
        checkbox_layout.addWidget(self.legend_checkbox)
        checkbox_layout.addWidget(self.highlighter_checkbox)
        checkbox_layout.addWidget(self.show_original_checkbox)

        self.layout.addLayout(checkbox_layout)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)

    def toggle_highlighter(self, state):
        self.yaxis_approx_value_highlighter = bool(state)
        self.update_plot()

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

    def plot_data(self, df, x_column, y_columns, smoothing_params, limit_lines=[], title=None):
        try:
            if title is not None:
                self.current_title = title
            else:
                title = self.current_title
            logging.info(f"Plotting data: x={x_column}, y={y_columns}, title= {title}")
            self.figure.clear()

            ax = self.figure.add_subplot(111)
            axes = [ax]

            # Generate a color map with distinct colors
            n_colors = len(y_columns)
            color_map = plt.cm.get_cmap('jet')(np.linspace(0, 1, n_colors))

            self.original_lines = []
            self.smoothed_lines = []

            lines = []  # Store line objects for cursor

            for i, (y_column, base_color) in enumerate(zip(y_columns, color_map)):
                logging.debug(f"Plotting column: {y_column}")
                if i > 0:
                    new_ax = ax.twinx()
                    new_ax.spines['right'].set_visible(True)
                    if i % 2 == 0:  # Even indices (2, 4, 6, ...) go to the left side
                        new_ax.spines['right'].set_visible(False)
                        new_ax.spines['left'].set_position(('axes', -0.1 * (i // 2)))
                        new_ax.yaxis.set_label_position('left')
                        new_ax.yaxis.set_ticks_position('left')
                    else:  # Odd indices (1, 3, 5, ...) go to the right side
                        new_ax.spines['left'].set_visible(False)
                        new_ax.spines['right'].set_position(('axes', 1 + 0.1 * ((i - 1) // 2)))
                        new_ax.yaxis.set_label_position('right')
                        new_ax.yaxis.set_ticks_position('right')
                    axes.append(new_ax)
                else:
                    new_ax = ax

                x_data = df[x_column]
                y_data = df[y_column]

                # Set the opacity based on whether smoothing is applied
                if smoothing_params['apply']:
                    original_color = mcolors.to_rgba(base_color, alpha=0.3)
                    smoothed_color = mcolors.to_rgba(base_color, alpha=1.0)
                else:
                    original_color = mcolors.to_rgba(base_color, alpha=1.0)

                original_line, = new_ax.plot(x_data, y_data, color=original_color, label=f'{y_column} (Original)')
                self.original_lines.append(original_line)
                lines.append(original_line)

                if smoothing_params['apply']:
                    logging.debug(f"Applying smoothing: {smoothing_params}")
                    y_smoothed = apply_smoothing(
                        y_data,
                        method=smoothing_params['method'],
                        window_length=smoothing_params['window_length'],
                        poly_order=smoothing_params['poly_order'],
                        sigma=smoothing_params['sigma']
                    )
                    smoothed_line, = new_ax.plot(x_data, y_smoothed, color=smoothed_color,
                                                 label=f'{y_column} (Smoothed)')
                    self.smoothed_lines.append(smoothed_line)
                    lines.append(smoothed_line)

                new_ax.set_ylabel(y_column, color=base_color)
                new_ax.tick_params(axis='y', colors=base_color)
                if self.show_legend:
                    new_ax.legend(loc='upper left')

            ax.set_xlabel(x_column)
            ax.set_title(title)

            # Add limit lines
            for line in limit_lines:
                if line['type'] == 'vertical':
                    ax.axvline(x=line['value'], color='black', linestyle='--',
                               label=f'Vertical Line at x={line["value"]}')
                else:
                    ax.axhline(y=line['value'], color='black', linestyle='--',
                               label=f'Horizontal Line at y={line["value"]}')

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
                if hasattr(self, 'cursor') and self.cursor:
                    self.cursor.remove()
                    self.cursor = None

            if self.yaxis_approx_value_highlighter:
                self.canvas.mpl_connect('button_press_event', self.on_click)

            # Apply the current state of the show_original_checkbox only if smoothing is applied
            if smoothing_params['apply']:
                self.toggle_original_data()
            else:
                # If smoothing is not applied, ensure all original lines are visible
                for line in self.original_lines:
                    line.set_visible(True)

            self.canvas.draw()
            logging.info("Plot completed successfully")

            # Store the last plot parameters for later updates
            self.last_plot_params = {
                'df': df,
                'x_column': x_column,
                'y_columns': y_columns,
                'smoothing_params': smoothing_params,
                'limit_lines': limit_lines,
                'title': title
            }

        except Exception as e:
            logging.error(f"Error in plot_data: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while plotting: {str(e)}")

    # def apply_curve_fitting(self, x_data, y_data, fit_func, equation, fit_type, x_label, y_label):
    #     try:
    #         logging.info(f"Applying {fit_type} curve fitting to plot")
    #         ax = self.figure.gca()
    #
    #         # Clear previous plots
    #         ax.clear()
    #
    #         # Plot the original data
    #         ax.plot(x_data, y_data, 'b-', label='Original Data')
    #
    #         # Generate points for the fitted curve
    #         x_fit = np.linspace(np.min(x_data), np.max(x_data), 500)
    #         y_fit = fit_func(x_fit)
    #
    #         # Plot the fitted curve
    #         ax.plot(x_fit, y_fit, 'r-', label=f'Fitted Curve: {equation}')
    #
    #         ax.legend()
    #         ax.set_title(f'Data with {fit_type} Fit')
    #         ax.set_xlabel(x_label)
    #         ax.set_ylabel(y_label)
    #
    #         # Toggeling original data on smoothing
    #         self.toggle_original_data()
    #
    #         self.canvas.draw()
    #         logging.info(f"{fit_type} curve fitting applied to plot successfully")
    #     except Exception as e:
    #         logging.error(f"Error in apply_curve_fitting: {str(e)}")
    #         logging.error(traceback.format_exc())
    #         QMessageBox.critical(self, "Error", f"An error occurred while applying curve fit: {str(e)}")

    def apply_curve_fitting(self, x_data, y_data, fit_func, equation, fit_type, x_label, y_label):
        try:
            logging.info(f"Applying {fit_type} curve fitting to plot")
            ax = self.figure.gca()

            # Find and update the existing line for this y_column
            line_found = False
            for line in ax.get_lines():
                # Check if this line corresponds to the y_column we're fitting
                if hasattr(line, '_y_column') and line._y_column == y_label:
                    # Update the existing line with fitted data
                    x_fit = np.linspace(np.min(x_data), np.max(x_data), len(x_data))
                    y_fit = fit_func(x_fit)

                    line.set_xdata(x_fit)
                    line.set_ydata(y_fit)
                    line.set_label(f'{y_label} ({fit_type} Fit)')
                    line._is_fitted = True
                    line._fit_type = fit_type
                    line._fit_equation = equation

                    line_found = True
                    logging.info(f"Updated existing line with {fit_type} fit")
                    break

            if not line_found:
                logging.warning(f"No existing line found for {y_label}")

            # Update legend and redraw
            ax.legend()
            ax.set_title(f'{ax.get_title()} - {fit_type} Fit Applied')

            self.canvas.draw()
            logging.info(f"{fit_type} curve fitting applied successfully")

        except Exception as e:
            logging.error(f"Error in apply_curve_fitting: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while applying curve fit: {str(e)}")

    def remove_curve_fitting(self, y_label=None):
        """Remove curve fitting and restore original data"""
        try:
            ax = self.figure.gca()
            main_window = self.window()

            # Get original data from filtered_df
            x_column = main_window.left_panel.axis_selection.x_combo.currentText()
            x_data = main_window.filtered_df[x_column].values

            for line in ax.get_lines():
                if hasattr(line, '_is_fitted') and line._is_fitted:
                    if y_label is None or (hasattr(line, '_y_column') and line._y_column == y_label):
                        # Restore original data
                        y_column = line._y_column
                        y_data = main_window.filtered_df[y_column].values

                        line.set_xdata(x_data)
                        line.set_ydata(y_data)
                        line.set_label(y_column)
                        line._is_fitted = False

            ax.legend()
            self.canvas.draw()

        except Exception as e:
            logging.error(f"Error removing curve fitting: {str(e)}")

    def clear(self):
        self.text_edit.clear()

    def on_click(self, event):
        if event.inaxes:
            x = event.xdata

            if event.button == 1:  # Left click - add line and points
                self.add_highlight(x)

                # Get x-axis label - use multiple fallback options
                xlabel = event.inaxes.get_xlabel()
                if not xlabel:  # If xlabel is empty, try to get it from stored params
                    xlabel = self.last_plot_params.get('x_column', 'X')

                # Collect all Y values from visible lines at this X position
                annotation_text = f"{xlabel}: {x:.2f}\n"

                for line in self.original_lines + self.smoothed_lines:
                    if line.get_visible():
                        xdata = line.get_xdata()
                        ydata = line.get_ydata()

                        # Find nearest X value
                        idx = np.argmin(np.abs(xdata - x))
                        nearest_x = xdata[idx]
                        nearest_y = ydata[idx]

                        if line.axes is not None:
                            ylabel = line.axes.get_ylabel()

                            # If ylabel is empty, try to get it from the line's label or other sources
                            if not ylabel or ylabel.strip() == "":
                                # Option 1: Use the line's label
                                ylabel = line.get_label()

                                # Option 2: If line label is also empty or default, use a fallback
                                if not ylabel or ylabel.startswith('_'):
                                    # Try to get from the data column name stored elsewhere
                                    # or use a generic label
                                    ylabel = "Y-axis"
                        else:
                            ylabel = "Unknown"


                        annotation_text += f"{ylabel}: {nearest_y:.2f}\n"

                # Add persistent annotation box
                annotation = event.inaxes.annotate(
                    annotation_text.strip(),
                    xy=(x, event.ydata),
                    xytext=(10, 10),
                    textcoords='offset points',
                    bbox=dict(boxstyle='round', fc='white', alpha=0.8, edgecolor='black'),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
                )

                # Store annotation for later removal if needed
                if not hasattr(self, 'annotations'):
                    self.annotations = []
                self.annotations.append(annotation)
                self.canvas.draw()

            elif event.button == 3:  # Right click - remove nearest line, points, and annotation
                self.remove_nearest_highlight(x)

                # Remove the nearest annotation
                if hasattr(self, 'annotations') and self.annotations:
                    # Find and remove the nearest annotation to the click
                    min_dist = float('inf')
                    nearest_annotation = None

                    for ann in self.annotations:
                        ann_x = ann.xy[0]
                        dist = abs(ann_x - x)
                        if dist < min_dist:
                            min_dist = dist
                            nearest_annotation = ann

                    if nearest_annotation:
                        nearest_annotation.remove()
                        self.annotations.remove(nearest_annotation)
                        self.canvas.draw()

    def add_highlight(self, x):
        # Add new vertical line
        vertical_line = self.figure.axes[0].axvline(x, color='gray', linestyle='--')

        # Create list to store highlight points for this vertical line
        points_group = []

        # Highlight points on each axis
        for ax in self.figure.axes:
            for line in ax.lines:
                # Only process lines that are actual data (not vertical lines, not markers)
                # Data lines typically have linestyle '-' and no marker or empty marker
                linestyle = line.get_linestyle()
                marker = line.get_marker()

                # Skip vertical/horizontal reference lines (dashed lines)
                if linestyle in ['--', '-.', ':']:
                    continue

                # Skip if this is already a highlight point (has 'o' marker)
                if marker == 'o':
                    continue

                xdata = line.get_xdata()
                ydata = line.get_ydata()

                # Check if xdata and ydata have valid lengths
                if len(xdata) == 0 or len(ydata) == 0:
                    continue

                # Find the closest point to the clicked x position
                index = np.argmin(np.abs(xdata - x))

                # Plot the highlight point at the actual data point location
                highlight = ax.plot(xdata[index], ydata[index], 'o', color='red', markersize=8, zorder=10)[0]
                points_group.append(highlight)

        # Store the vertical line and its associated points as a tuple
        self.vertical_lines.append((x, vertical_line, points_group))

        self.canvas.draw()

    def remove_nearest_highlight(self, x):
        # Find and remove the nearest vertical line and its points
        if not self.vertical_lines:
            return

        # Find the nearest vertical line
        distances = [abs(vline[0] - x) for vline in self.vertical_lines]
        nearest_index = np.argmin(distances)

        # Remove the line and points
        _, vertical_line, points_group = self.vertical_lines[nearest_index]
        vertical_line.remove()
        for point in points_group:
            point.remove()

        # Remove from the list
        self.vertical_lines.pop(nearest_index)

        self.canvas.draw()

    def highlight_point(self, x):
        # This method is kept for backward compatibility if needed elsewhere
        # It now calls add_highlight instead
        self.add_highlight(x)

    # def update_title(self):
    #     if hasattr(self, 'figure') and self.figure.axes:
    #         title = self.title_input.text()
    #         self.figure.axes[0].set_title(title)
    #         self.canvas.draw()
    #         self.current_title = title
    #         if hasattr(self, 'last_plot_params'):
    #             self.last_plot_params['title'] = title

    def set_title(self):
        title = self.title_input.text()
        self.current_title = title
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = title
            self.update_plot()

    def toggle_original_data(self):
        show_original = self.show_original_checkbox.isChecked()
        logging.info(f"Toggling original data visibility: {show_original}")
        for line in self.original_lines:
            line.set_visible(show_original)
        self.canvas.draw_idle()  # Use draw_idle() instead of draw() for better performance
        logging.info("Original data visibility toggled")

    def get_show_original_state(self):
        return self.show_original_checkbox.isChecked()

    def set_show_original_state(self, state):
        self.show_original_checkbox.setChecked(state)
        self.toggle_original_data()

    def clear_plot(self):
        logging.info("Clearing plot in PlotArea")
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_title("No data to display")
        ax.set_xlabel("X-axis")
        ax.set_ylabel("Y-axis")
        self.canvas.draw()
        self.reset_title()
        # Clear vertical lines list when plot is cleared
        self.vertical_lines = []

    def reset_title(self):
        self.current_title = ""
        self.title_input.clear()  # Clear the title input field
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = ""

        # Clear the plot title if there's an existing plot
        if hasattr(self, 'figure') and self.figure.axes:
            self.figure.axes[0].set_title("")
            self.canvas.draw()