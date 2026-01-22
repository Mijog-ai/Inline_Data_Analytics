import logging
import traceback
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.asc_utils import apply_smoothing
import numpy as np
import tempfile
import os


class PlotArea(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.show_cursor = True
        self.show_legend = True
        self.yaxis_approx_value_highlighter = True
        self.show_original_data = True
        self.setup_ui()

        # Store plot state
        self.vertical_lines = []
        self.annotations_list = []
        self.current_title = ""
        self.current_figure = None

    def setup_ui(self):
        # Add title input and buttons
        title_layout = QHBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter plot title")
        self.set_title_button = QPushButton("Set Title")
        self.set_title_button.clicked.connect(self.set_title)
        title_layout.addWidget(self.title_input)
        title_layout.addWidget(self.set_title_button)
        self.layout.addLayout(title_layout)

        # Create web view for Plotly
        self.web_view = QWebEngineView()

        # Add checkboxes for control
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
        self.layout.addWidget(self.web_view)
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
        if hasattr(self, 'last_plot_params'):
            self.plot_data(**self.last_plot_params)

    def plot_data(self, df, x_column, y_columns, smoothing_params, limit_lines=[], title=None):
        try:
            if title is not None:
                self.current_title = title
            else:
                title = self.current_title

            logging.info(f"Plotting data: x={x_column}, y={y_columns}, title={title}")

            # Generate distinct colors
            n_colors = len(y_columns)
            colors = self._generate_colors(n_colors)

            # Create figure with secondary y-axes
            fig = go.Figure()

            # Track which traces belong to which y-axis
            self.trace_info = []

            # Plot each y-column
            for i, (y_column, color) in enumerate(zip(y_columns, colors)):
                logging.debug(f"Plotting column: {y_column}")

                x_data = df[x_column].values
                y_data = df[y_column].values

                # Determine which y-axis to use
                yaxis_name = 'y' if i == 0 else f'y{i+1}'

                # Plot original data
                if smoothing_params['apply']:
                    # Original data with transparency
                    fig.add_trace(go.Scatter(
                        x=x_data,
                        y=y_data,
                        mode='lines',
                        name=f'{y_column} (Original)',
                        line=dict(color=color, width=1),
                        opacity=0.3,
                        yaxis=yaxis_name,
                        visible=self.show_original_data,
                        showlegend=self.show_legend,
                        hovertemplate=f'{x_column}: %{{x:.2f}}<br>{y_column}: %{{y:.2f}}<extra></extra>'
                    ))
                    self.trace_info.append({'type': 'original', 'y_column': y_column, 'yaxis': yaxis_name})

                    # Smoothed data
                    y_smoothed = apply_smoothing(
                        y_data,
                        method=smoothing_params['method'],
                        window_length=smoothing_params['window_length'],
                        poly_order=smoothing_params['poly_order'],
                        sigma=smoothing_params['sigma']
                    )
                    fig.add_trace(go.Scatter(
                        x=x_data,
                        y=y_smoothed,
                        mode='lines',
                        name=f'{y_column} (Smoothed)',
                        line=dict(color=color, width=2),
                        yaxis=yaxis_name,
                        showlegend=self.show_legend,
                        hovertemplate=f'{x_column}: %{{x:.2f}}<br>{y_column} (Smoothed): %{{y:.2f}}<extra></extra>'
                    ))
                    self.trace_info.append({'type': 'smoothed', 'y_column': y_column, 'yaxis': yaxis_name})
                else:
                    # Only original data
                    fig.add_trace(go.Scatter(
                        x=x_data,
                        y=y_data,
                        mode='lines',
                        name=y_column,
                        line=dict(color=color, width=2),
                        yaxis=yaxis_name,
                        showlegend=self.show_legend,
                        hovertemplate=f'{x_column}: %{{x:.2f}}<br>{y_column}: %{{y:.2f}}<extra></extra>'
                    ))
                    self.trace_info.append({'type': 'data', 'y_column': y_column, 'yaxis': yaxis_name})

            # Configure layout with multiple y-axes
            layout_config = {
                'title': title,
                'xaxis': {'title': x_column},
                'hovermode': 'closest' if self.show_cursor else False,
                'showlegend': self.show_legend,
                'height': 600,
            }

            # Add y-axes configuration
            for i, (y_column, color) in enumerate(zip(y_columns, colors)):
                if i == 0:
                    layout_config['yaxis'] = {
                        'title': {'text': y_column, 'font': {'color': color}},
                        'tickfont': {'color': color}
                    }
                else:
                    yaxis_key = f'yaxis{i+1}'
                    if i % 2 == 1:  # Odd indices on the right
                        layout_config[yaxis_key] = {
                            'title': {'text': y_column, 'font': {'color': color}},
                            'tickfont': {'color': color},
                            'anchor': 'free' if i > 1 else 'x',
                            'overlaying': 'y',
                            'side': 'right',
                            'position': 1.0 if i == 1 else 1.0 + 0.1 * ((i - 1) // 2)
                        }
                    else:  # Even indices on the left
                        layout_config[yaxis_key] = {
                            'title': {'text': y_column, 'font': {'color': color}},
                            'tickfont': {'color': color},
                            'anchor': 'free',
                            'overlaying': 'y',
                            'side': 'left',
                            'position': 0.0 - 0.1 * (i // 2)
                        }

            fig.update_layout(**layout_config)

            # Add limit lines (shapes)
            shapes = []
            for line in limit_lines:
                if line['type'] == 'vertical':
                    shapes.append({
                        'type': 'line',
                        'x0': line['value'],
                        'x1': line['value'],
                        'y0': 0,
                        'y1': 1,
                        'yref': 'paper',
                        'line': {'color': 'black', 'width': 2, 'dash': 'dash'}
                    })
                else:
                    shapes.append({
                        'type': 'line',
                        'x0': 0,
                        'x1': 1,
                        'xref': 'paper',
                        'y0': line['value'],
                        'y1': line['value'],
                        'line': {'color': 'black', 'width': 2, 'dash': 'dash'}
                    })

            if shapes:
                fig.update_layout(shapes=shapes)

            # Configure interactivity
            config = {
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
                'modeBarButtonsToRemove': [],
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'plot',
                    'height': 800,
                    'width': 1200,
                    'scale': 2
                }
            }

            # Add click event handling if highlighting is enabled
            if self.yaxis_approx_value_highlighter:
                # Add JavaScript for click handling
                fig.update_layout(
                    clickmode='event+select'
                )

            # Store the figure
            self.current_figure = fig

            # Create temporary HTML file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w')
            fig.write_html(temp_file.name, config=config)
            temp_file.close()

            # Load in web view
            self.web_view.setUrl(QUrl.fromLocalFile(temp_file.name))

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

    def _generate_colors(self, n):
        """Generate n distinct colors using jet colormap"""
        import matplotlib.cm as cm
        import matplotlib.colors as mcolors

        # Use the new API to avoid deprecation warning
        cmap = cm.colormaps.get_cmap('jet')
        colors_rgba = [cmap(i / (n - 1) if n > 1 else 0.5) for i in range(n)]
        colors_hex = [mcolors.rgb2hex(c[:3]) for c in colors_rgba]
        return colors_hex

    def apply_curve_fitting(self, x_data, y_data, fit_func, equation, fit_type, x_label, y_label):
        try:
            logging.info(f"Applying {fit_type} curve fitting to plot")

            if not self.current_figure or not hasattr(self, 'last_plot_params'):
                logging.warning("No existing plot to apply curve fitting")
                return

            # Generate fitted curve
            x_fit = np.linspace(np.min(x_data), np.max(x_data), 500)
            y_fit = fit_func(x_fit)

            # Find the corresponding y-axis for this y_label
            yaxis_name = 'y'
            for info in self.trace_info:
                if info['y_column'] == y_label:
                    yaxis_name = info['yaxis']
                    break

            # Get color for this y_column
            y_columns = self.last_plot_params['y_columns']
            if y_label in y_columns:
                idx = y_columns.index(y_label)
                colors = self._generate_colors(len(y_columns))
                color = colors[idx]
            else:
                color = 'red'

            # Add fitted curve as a new trace
            self.current_figure.add_trace(go.Scatter(
                x=x_fit,
                y=y_fit,
                mode='lines',
                name=f'{y_label} ({fit_type} Fit)',
                line=dict(color=color, width=2, dash='dot'),
                yaxis=yaxis_name,
                showlegend=self.show_legend,
                hovertemplate=f'{fit_type} Fit<br>Equation: {equation}<br>x: %{{x:.2f}}<br>y: %{{y:.2f}}<extra></extra>'
            ))

            # Update the plot
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w')
            config = {
                'displayModeBar': True,
                'displaylogo': False,
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'plot',
                    'height': 800,
                    'width': 1200,
                    'scale': 2
                }
            }
            self.current_figure.write_html(temp_file.name, config=config)
            temp_file.close()
            self.web_view.setUrl(QUrl.fromLocalFile(temp_file.name))

            logging.info(f"{fit_type} curve fitting applied successfully")

        except Exception as e:
            logging.error(f"Error in apply_curve_fitting: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while applying curve fit: {str(e)}")

    def remove_curve_fitting(self, y_label=None):
        """Remove curve fitting and restore original data"""
        try:
            if not self.current_figure:
                return

            # Rebuild the plot without fitted curves
            if hasattr(self, 'last_plot_params'):
                self.plot_data(**self.last_plot_params)

            logging.info("Curve fitting removed successfully")

        except Exception as e:
            logging.error(f"Error removing curve fitting: {str(e)}")

    def clear(self):
        """Clear the plot area"""
        self.clear_plot()

    def add_highlight(self, x):
        """Add vertical line and highlight points at x position"""
        if not self.current_figure:
            return

        # Add vertical line as shape
        self.current_figure.add_shape(
            type='line',
            x0=x,
            x1=x,
            y0=0,
            y1=1,
            yref='paper',
            line=dict(color='gray', width=2, dash='dash')
        )

        # Store the x position
        self.vertical_lines.append(x)

        # Redraw
        self._redraw_plot()

    def remove_nearest_highlight(self, x):
        """Remove the nearest vertical line to x position"""
        if not self.vertical_lines:
            return

        # Find nearest line
        distances = [abs(vx - x) for vx in self.vertical_lines]
        nearest_idx = np.argmin(distances)

        # Remove from list
        self.vertical_lines.pop(nearest_idx)

        # Rebuild plot with remaining lines
        if hasattr(self, 'last_plot_params'):
            self.plot_data(**self.last_plot_params)

    def _redraw_plot(self):
        """Redraw the current plot"""
        if not self.current_figure:
            return

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w')
        config = {
            'displayModeBar': True,
            'displaylogo': False,
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'plot',
                'height': 800,
                'width': 1200,
                'scale': 2
            }
        }
        self.current_figure.write_html(temp_file.name, config=config)
        temp_file.close()
        self.web_view.setUrl(QUrl.fromLocalFile(temp_file.name))

    def set_title(self):
        title = self.title_input.text()
        self.current_title = title
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = title
            self.update_plot()

    def toggle_original_data(self):
        self.show_original_data = self.show_original_checkbox.isChecked()
        logging.info(f"Toggling original data visibility: {self.show_original_data}")
        self.update_plot()

    def get_show_original_state(self):
        return self.show_original_checkbox.isChecked()

    def set_show_original_state(self, state):
        self.show_original_checkbox.setChecked(state)
        self.toggle_original_data()

    def clear_plot(self):
        logging.info("Clearing plot in PlotArea")

        # Create empty figure
        fig = go.Figure()
        fig.update_layout(
            title="No data to display",
            xaxis_title="X-axis",
            yaxis_title="Y-axis"
        )

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w')
        fig.write_html(temp_file.name)
        temp_file.close()
        self.web_view.setUrl(QUrl.fromLocalFile(temp_file.name))

        self.reset_title()
        self.vertical_lines = []
        self.annotations_list = []
        self.current_figure = None

    def reset_title(self):
        self.current_title = ""
        self.title_input.clear()
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = ""

    def highlight_point(self, x):
        """Compatibility method for backward compatibility"""
        self.add_highlight(x)
