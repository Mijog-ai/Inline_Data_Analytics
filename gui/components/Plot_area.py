import logging
import traceback
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QMessageBox, QCheckBox,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QToolBar, QAction, QGroupBox)
from PyQt5.QtCore import Qt, QPointF, QSize
from PyQt5.QtGui import QColor, QFont, QIcon
import pyqtgraph as pg
from pyqtgraph import PlotWidget, InfiniteLine, TextItem, mkPen, mkBrush
from utils.asc_utils import apply_smoothing
import numpy as np


class PlotArea(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.show_cursor = True
        self.show_legend = True
        self.yaxis_approx_value_highlighter = True
        self.setup_ui()
        self.vertical_lines = []

        self.original_lines = []
        self.smoothed_lines = []
        self.current_title = ""
        self.plot_items = []
        self.y_axes = []
        self.annotations = []
        self.highlight_points = []

        # Zoom region control
        self.zoom_region_lines = []
        self.original_x_range = None
        self.zoom_mode_active = False

        # Text insertion control - ADD THESE
        self.floating_text_items = []
        self.text_insertion_mode = False
        self.text_removal_mode = False  # ADD THIS
        self.pending_text = ""

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

        self.create_toolbar()
        self.layout.addWidget(self.toolbar)

        # Create PyQtGraph PlotWidget
        self.plot_widget = PlotWidget()
        self.plot_widget.setBackground('w')  # White background
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Enable antialiasing for smoother lines
        pg.setConfigOptions(antialias=True)
        self.plot_widget.setMouseEnabled(x=False, y=False)

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

        self.zoom_region_checkbox = QCheckBox("Zoom Region Mode")
        self.zoom_region_checkbox.setChecked(False)
        self.zoom_region_checkbox.stateChanged.connect(self.toggle_zoom_region_mode)

        checkbox_layout.addWidget(self.cursor_checkbox)
        checkbox_layout.addWidget(self.legend_checkbox)
        checkbox_layout.addWidget(self.highlighter_checkbox)
        checkbox_layout.addWidget(self.show_original_checkbox)
        checkbox_layout.addWidget(self.zoom_region_checkbox)

        self.layout.addLayout(checkbox_layout)
        self.layout.addWidget(self.plot_widget)

        self.setLayout(self.layout)

        # Setup mouse click event
        self.plot_widget.scene().sigMouseClicked.connect(self.on_click)

        # Setup crosshair cursor
        self.crosshair_v = InfiniteLine(angle=90, movable=False,
                                        pen=pg.mkPen('k', width=1, style=Qt.DashLine))
        self.crosshair_h = InfiniteLine(angle=0, movable=False,
                                        pen=pg.mkPen('k', width=1, style=Qt.DashLine))
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_h, ignoreBounds=True)

        # Cursor text label
        self.cursor_label = TextItem(anchor=(0, 1), color='k',
                                     fill=pg.mkBrush(255, 255, 255, 200))
        self.plot_widget.addItem(self.cursor_label, ignoreBounds=True)

        # Connect mouse move event for cursor
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved,
                                    rateLimit=60, slot=self.on_mouse_moved)

        self.plot_widget.wheelEvent = lambda event: None
        # Legend
        self.legend = self.plot_widget.addLegend()

    def create_toolbar(self):
        self.toolbar= QToolBar("Plot Tools")
        self.toolbar.setIconSize(QSize(24,24))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Insert Text Box Action
        self.insert_text_action= QAction("Text", self)
        self.insert_text_action.setCheckable(True)  # Makes it toggle on/off
        self.insert_text_action.setToolTip("Click to enable text insertion mode, then click on plot to place text")
        self.insert_text_action.triggered.connect(self.toggle_text_insertion_mode)
        self.toolbar.addAction(self.insert_text_action)

        self.toolbar.addSeparator()

        self.remove_text_action = QAction("Remove Text Box", self)
        self.remove_text_action.setCheckable(True)
        self.remove_text_action.setToolTip("Click to enable text removal mode, then click on text to remove it")
        self.remove_text_action.triggered.connect(self.toggle_text_removal_mode)
        self.toolbar.addAction(self.remove_text_action)

        self.toolbar.addSeparator()

        # Clear All Texts Action
        self.clear_texts_action = QAction("Clear All Texts", self)
        self.clear_texts_action.setToolTip("Remove all floating text boxes from plot")
        self.clear_texts_action.triggered.connect(self.clear_all_floating_texts)
        self.toolbar.addAction(self.clear_texts_action)

    def clear_all_floating_texts(self):
        """Remove all floating text items from plot"""
        if not self.floating_text_items:
            QMessageBox.information(self, "No Texts", "There are no text boxes to clear.")
            return

        reply = QMessageBox.question(
            self,
            "Clear All Texts",
            f"Are you sure you want to remove all {len(self.floating_text_items)} text boxes?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for text_data in self.floating_text_items:
                self.plot_widget.removeItem(text_data['item'])
            self.floating_text_items = []

            # Uncheck removal mode if active
            if hasattr(self, 'remove_text_action'):
                self.remove_text_action.setChecked(False)
            self.text_removal_mode = False

            logging.info("Cleared all floating texts")
            QMessageBox.information(self, "Cleared", "All text boxes have been removed.")

    def toggle_highlighter(self, state):
        self.yaxis_approx_value_highlighter = bool(state)
        self.update_plot()

    def toggle_cursor(self, state):
        self.show_cursor = bool(state)
        self.crosshair_v.setVisible(self.show_cursor)
        self.crosshair_h.setVisible(self.show_cursor)
        self.cursor_label.setVisible(self.show_cursor)

    def toggle_legend(self, state):
        self.show_legend = bool(state)
        if self.legend is not None:
            self.legend.setVisible(self.show_legend)

    def update_plot(self):
        # This method should be called whenever the plot needs to be updated
        if hasattr(self, 'last_plot_params'):
            self.plot_data(**self.last_plot_params)

    def get_distinct_colors(self, n):
        """Generate N visually distinct colors"""
        if n == 0:
            return []
        # Use HSV color space for better color distribution
        colors = []
        for i in range(n):
            hue = int(255 * i / n)
            color = QColor.fromHsv(hue, 255, 200)
            colors.append(color)
        return colors

    def plot_data(self, df, x_column, y_columns, smoothing_params, limit_lines=[], title=None):
        try:
            if title is not None:
                self.current_title = title
            else:
                title = self.current_title
            logging.info(f"Plotting data: x={x_column}, y={y_columns}, title={title}")

            self.clear_all_axes()

            # Clear previous plot
            self.plot_widget.clear()
            self.plot_items = []
            self.original_lines = []
            self.smoothed_lines = []
            self.y_axes = []

            # Re-add legend if needed
            if self.show_legend:
                self.legend = self.plot_widget.addLegend()

            # Re-add crosshair
            self.plot_widget.addItem(self.crosshair_v)
            self.plot_widget.addItem(self.crosshair_h)
            self.plot_widget.addItem(self.cursor_label)

            # Set title
            self.plot_widget.setTitle(title)

            # Set X-axis label
            self.plot_widget.setLabel('bottom', x_column)

            # Generate distinct colors
            colors = self.get_distinct_colors(len(y_columns))

            # Get the main view box
            main_viewbox = self.plot_widget.getViewBox()

            for i, (y_column, color) in enumerate(zip(y_columns, colors)):
                logging.debug(f"Plotting column: {y_column}")

                x_data = df[x_column].values
                y_data = df[y_column].values

                # Create ViewBox for additional Y axes (except the first one)
                if i == 0:
                    # First plot uses the main axis
                    viewbox = main_viewbox
                    self.plot_widget.setLabel('left', y_column, color=color.name())
                else:
                    # Create additional Y axis
                    viewbox = pg.ViewBox()
                    self.y_axes.append(viewbox)

                    # Link X axis to main plot
                    viewbox.setXLink(main_viewbox)

                    # Add the viewbox to the scene
                    self.plot_widget.scene().addItem(viewbox)


                    ###---------------------------------------

                    # Create axis item with proper spacing
                    if i % 2 == 1:  # Right side for odd indices
                        axis = pg.AxisItem('right')
                        axis_col_position = 4 + (i - 1)  # More spacing: 4, 5, 6, 7...
                    else:  # Left side for even indices
                        axis = pg.AxisItem('left')
                        axis_col_position = -i  # More spacing: -2, -4, -6...

                    axis.setLabel(y_column, color=color.name())
                    axis.linkToView(viewbox)

                    # Set axis colors
                    axis.setPen(color)
                    axis.setTextPen(color)

                    # Add axis to layout
                    self.plot_widget.plotItem.layout.addItem(axis, 2, axis_col_position)

                    # Set minimum width for better spacing
                    self.plot_widget.plotItem.layout.setColumnMinimumWidth(axis_col_position, 80)
                    ###-----------------------------------------

                    # Update views when main view changes
                    def update_views():
                        for vb in self.y_axes:
                            vb.setGeometry(main_viewbox.sceneBoundingRect())
                            vb.linkedViewChanged(main_viewbox, vb.XAxis)

                    main_viewbox.sigResized.connect(update_views)
                    update_views()

                # Set opacity based on smoothing
                if smoothing_params['apply']:
                    original_alpha = 80  # ~0.3 * 255
                    smoothed_alpha = 255
                else:
                    original_alpha = 255

                # Create pen for original line
                original_color = QColor(color)
                original_color.setAlpha(original_alpha)
                original_pen = mkPen(color=original_color, width=2)

                # Plot original data
                original_curve = pg.PlotDataItem(
                    x_data, y_data,
                    pen=original_pen,
                    name=f'{y_column} (Original)'
                )

                if i == 0:
                    self.plot_widget.addItem(original_curve)
                else:
                    viewbox.addItem(original_curve)

                self.original_lines.append(original_curve)
                self.plot_items.append({
                    'curve': original_curve,
                    'x_data': x_data,
                    'y_data': y_data,
                    'label': y_column,
                    'viewbox': viewbox
                })

                # Apply smoothing if requested
                if smoothing_params['apply']:
                    logging.debug(f"Applying smoothing: {smoothing_params}")
                    y_smoothed = apply_smoothing(
                        y_data,
                        method=smoothing_params['method'],
                        window_length=smoothing_params['window_length'],
                        poly_order=smoothing_params['poly_order'],
                        sigma=smoothing_params['sigma']
                    )

                    smoothed_color = QColor(color)
                    smoothed_color.setAlpha(smoothed_alpha)
                    smoothed_pen = mkPen(color=smoothed_color, width=2)

                    smoothed_curve = pg.PlotDataItem(
                        x_data, y_smoothed,
                        pen=smoothed_pen,
                        name=f'{y_column} (Smoothed)'
                    )

                    if i == 0:
                        self.plot_widget.addItem(smoothed_curve)
                    else:
                        viewbox.addItem(smoothed_curve)

                    self.smoothed_lines.append(smoothed_curve)
                    self.plot_items.append({
                        'curve': smoothed_curve,
                        'x_data': x_data,
                        'y_data': y_smoothed,
                        'label': y_column,
                        'viewbox': viewbox
                    })

            # Add limit lines
            for line in limit_lines:
                if line['type'] == 'vertical':
                    vline = InfiniteLine(
                        pos=line['value'],
                        angle=90,
                        pen=mkPen('k', width=2, style=Qt.DashLine),
                        label=f"x={line['value']}"
                    )
                    self.plot_widget.addItem(vline)
                else:
                    hline = InfiniteLine(
                        pos=line['value'],
                        angle=0,
                        pen=mkPen('k', width=2, style=Qt.DashLine),
                        label=f"y={line['value']}"
                    )
                    self.plot_widget.addItem(hline)

            # Toggle cursor visibility
            self.toggle_cursor(self.cursor_checkbox.isChecked())

            # Disable auto-range and store original data range
            self.plot_widget.getViewBox().enableAutoRange(enable=False)

            # Store original X range from data (use the x_column from dataframe)
            all_x_data = df[x_column].values
            if len(all_x_data) > 0:
                self.original_x_range = (float(np.min(all_x_data)), float(np.max(all_x_data)))
                # Set to original range
                self.plot_widget.setXRange(self.original_x_range[0], self.original_x_range[1], padding=0.02)

            # Apply the current state of the show_original_checkbox
            if smoothing_params['apply']:
                self.toggle_original_data()
            else:
                for line in self.original_lines:
                    line.setVisible(True)

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

    def on_mouse_moved(self, evt):
        """Handle mouse movement for crosshair cursor"""
        if not self.show_cursor:
            return

        pos = evt[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.getViewBox().mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()

            # Update crosshair position
            self.crosshair_v.setPos(x)
            self.crosshair_h.setPos(y)

            # Get x-axis label
            xlabel = self.last_plot_params.get('x_column', 'X') if hasattr(self, 'last_plot_params') else 'X'

            # Find nearest data points
            cursor_text = f"{xlabel}: {x:.2f}\n"

            for item in self.plot_items:
                if item['curve'].isVisible():
                    x_data = item['x_data']
                    y_data = item['y_data']

                    if len(x_data) > 0:
                        idx = np.argmin(np.abs(x_data - x))
                        nearest_y = y_data[idx]
                        cursor_text += f"{item['label']}: {nearest_y:.2f}\n"

            # Update label position and text
            self.cursor_label.setPos(x, y)
            self.cursor_label.setText(cursor_text.strip())

    def on_click(self, event):
        """Handle mouse click events for highlighting, zoom region, or text operations"""
        pos = event.scenePos()
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return

        mouse_point = self.plot_widget.getViewBox().mapSceneToView(pos)
        x = mouse_point.x()
        y = mouse_point.y()

        if event.button() == Qt.LeftButton:
            # Priority: Text operations > Zoom > Highlights
            if self.text_insertion_mode:
                self.insert_floating_text_at_position(x, y)
            elif self.text_removal_mode:
                # Try to remove text at this position
                if self.remove_floating_text_at_position(x, y):
                    QMessageBox.information(
                        self,
                        "Text Removed",
                        "Text box has been removed."
                    )
                else:
                    QMessageBox.information(
                        self,
                        "No Text Found",
                        "No text box found at this location."
                    )
            elif self.zoom_mode_active:
                self.add_zoom_region_line(x)
            elif self.yaxis_approx_value_highlighter:
                self.add_highlight(x)

        elif event.button() == Qt.RightButton:
            # Right-click cancels active modes
            if self.text_insertion_mode:
                self.cancel_text_insertion()
            elif self.text_removal_mode:
                self.remove_text_action.setChecked(False)
                self.toggle_text_removal_mode(False)
            elif self.zoom_mode_active:
                self.remove_zoom_region_line(x)
            elif self.yaxis_approx_value_highlighter:
                self.remove_nearest_highlight(x)

    def add_highlight(self, x):
        """Add vertical line and highlight points at x position"""
        # Get x-axis label
        xlabel = self.last_plot_params.get('x_column', 'X') if hasattr(self, 'last_plot_params') else 'X'

        # Collect all items for this highlight
        points_group = []

        # Get the main viewbox
        main_viewbox = self.plot_widget.getViewBox()

        # Create separate annotation for each line at its intersection point
        for item in self.plot_items:
            if item['curve'].isVisible():
                x_data = item['x_data']
                y_data = item['y_data']

                if len(x_data) > 0:
                    # Find nearest point
                    idx = np.argmin(np.abs(x_data - x))
                    nearest_x = x_data[idx]
                    nearest_y = y_data[idx]

                    # Get the viewbox for this item
                    viewbox = item['viewbox']

                    # Get Y range for THIS specific viewbox
                    y_range = viewbox.viewRange()[1]
                    y_min = y_range[0]

                    # Create vertical line from bottom to the point
                    vertical_line_segment = pg.PlotDataItem(
                        [nearest_x, nearest_x],
                        [y_min, nearest_y],
                        pen=mkPen('gray', width=2, style=Qt.DashLine)
                    )

                    # Add vertical line to the SAME viewbox as the data
                    viewbox.addItem(vertical_line_segment)
                    points_group.append((vertical_line_segment, viewbox))

                    # Get X range from main viewbox (all share same X axis)
                    x_range = main_viewbox.viewRange()[0]
                    x_min = x_range[0]

                    # Create horizontal line from left to the point
                    horizontal_line_segment = pg.PlotDataItem(
                        [x_min, nearest_x],
                        [nearest_y, nearest_y],
                        pen=mkPen('gray', width=2, style=Qt.DashLine)
                    )

                    # Add horizontal line to the SAME viewbox as the data
                    viewbox.addItem(horizontal_line_segment)
                    points_group.append((horizontal_line_segment, viewbox))

                    # Create highlight point
                    scatter = pg.ScatterPlotItem(
                        [nearest_x], [nearest_y],
                        pen=mkPen('r', width=2),
                        brush=mkBrush('r'),
                        size=10,
                        symbol='o'
                    )

                    # Add to the SAME viewbox as the data
                    viewbox.addItem(scatter)
                    points_group.append((scatter, viewbox))

                    # Create individual annotation at the intersection point
                    annotation_text = f"{xlabel}: {nearest_x:.2f}\n{item['label']}: {nearest_y:.2f}"

                    annotation = TextItem(
                        annotation_text,
                        anchor=(0, 0.5),
                        color='k',
                        fill=pg.mkBrush(255, 255, 255, 200),
                        border=pg.mkPen('k', width=1)
                    )

                    # Position annotation right at the data point
                    annotation.setPos(nearest_x, nearest_y)

                    # Add to the SAME viewbox as the data
                    viewbox.addItem(annotation)
                    points_group.append((annotation, viewbox))

        # Store all items with their viewboxes for this highlight
        self.vertical_lines.append((x, points_group))


    def insert_floating_text_at_position(self, x, y):
        """Insert floating text box at specified position"""
        try:
            # Create text item
            text_item = pg.TextItem(
                self.pending_text,
                anchor=(0.5, 0.5),
                color='k',
                fill=pg.mkBrush(255, 255, 200, 220),
                border=pg.mkPen('k', width=2)
            )

            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            text_item.setFont(font)

            text_item.setPos(x, y)
            self.plot_widget.addItem(text_item)

            self.floating_text_items.append({
                'item': text_item,
                'text': self.pending_text,
                'position': (x, y)
            })

            logging.info(f"Inserted floating text at ({x:.2f}, {y:.2f}): {self.pending_text}")

            # Exit text insertion mode and uncheck button
            self.text_insertion_mode = False
            self.pending_text = ""
            self.plot_widget.setCursor(Qt.ArrowCursor)

            if hasattr(self, 'insert_text_action'):
                self.insert_text_action.setChecked(False)

        except Exception as e:
            logging.error(f"Error inserting floating text: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to insert text: {str(e)}")

    def remove_nearest_highlight(self, x):
        """Remove the nearest vertical line, points, and annotation"""
        if not self.vertical_lines:
            return

        # Find nearest vertical line
        distances = [abs(vline[0] - x) for vline in self.vertical_lines]
        nearest_index = np.argmin(distances)

        # Remove all items with their correct viewboxes
        _, points_group = self.vertical_lines[nearest_index]

        for item, viewbox in points_group:
            try:
                viewbox.removeItem(item)
            except Exception as e:
                logging.warning(f"Could not remove item from viewbox: {e}")
                # Fallback: try removing from plot widget
                try:
                    self.plot_widget.removeItem(item)
                except:
                    pass

        # Remove from list
        self.vertical_lines.pop(nearest_index)
        logging.info(f"Removed highlight at x={x:.2f}")

    def apply_curve_fitting(self, x_data, y_data, fit_func, equation, fit_type, x_label, y_label):
        """Apply curve fitting to the plot"""
        try:
            logging.info(f"Applying {fit_type} curve fitting to plot")

            # Find and update the existing line for this y_column
            line_found = False
            for item in self.plot_items:
                if item['label'] == y_label:
                    # Generate fitted data
                    x_fit = np.linspace(np.min(x_data), np.max(x_data), len(x_data))
                    y_fit = fit_func(x_fit)

                    # Update the curve
                    item['curve'].setData(x_fit, y_fit)

                    # Store fitting info
                    item['is_fitted'] = True
                    item['fit_type'] = fit_type
                    item['fit_equation'] = equation

                    line_found = True
                    logging.info(f"Updated existing line with {fit_type} fit")
                    break

            if not line_found:
                logging.warning(f"No existing line found for {y_label}")

            # Update title
            current_title = self.plot_widget.plotItem.titleLabel.text
            self.plot_widget.setTitle(f'{current_title} - {fit_type} Fit Applied')

            logging.info(f"{fit_type} curve fitting applied successfully")

        except Exception as e:
            logging.error(f"Error in apply_curve_fitting: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while applying curve fit: {str(e)}")

    def remove_curve_fitting(self, y_label=None):
        """Remove curve fitting and restore original data"""
        try:
            main_window = self.window()
            x_column = main_window.left_panel.axis_selection.x_combo.currentText()
            x_data = main_window.filtered_df[x_column].values

            for item in self.plot_items:
                if item.get('is_fitted', False):
                    if y_label is None or item['label'] == y_label:
                        # Restore original data
                        y_column = item['label']
                        y_data = main_window.filtered_df[y_column].values

                        item['curve'].setData(x_data, y_data)
                        item['is_fitted'] = False

            logging.info("Curve fitting removed successfully")

        except Exception as e:
            logging.error(f"Error removing curve fitting: {str(e)}")

    def set_title(self):
        """Set the plot title"""
        title = self.title_input.text()
        self.current_title = title
        self.plot_widget.setTitle(title)
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = title

    def toggle_original_data(self):
        """Toggle visibility of original data lines"""
        show_original = self.show_original_checkbox.isChecked()
        logging.info(f"Toggling original data visibility: {show_original}")
        for line in self.original_lines:
            line.setVisible(show_original)
        logging.info("Original data visibility toggled")

    def get_show_original_state(self):
        """Get the state of show original checkbox"""
        return self.show_original_checkbox.isChecked()

    def set_show_original_state(self, state):
        """Set the state of show original checkbox"""
        self.show_original_checkbox.setChecked(state)
        self.toggle_original_data()

    def toggle_zoom_region_mode(self, state):
        """Toggle zoom region mode on/off"""
        self.zoom_mode_active = bool(state)
        if self.zoom_mode_active:
            logging.info("Zoom region mode activated")
        else:
            logging.info("Zoom region mode deactivated")
            # When disabling, clear any existing zoom region lines
            if len(self.zoom_region_lines) > 0:
                self.clear_zoom_region()

    def add_zoom_region_line(self, x):
        """Add a zoom region boundary line"""
        if len(self.zoom_region_lines) >= 2:
            QMessageBox.information(
                self,
                "Zoom Region",
                "Maximum 2 zoom region lines allowed. Right-click to remove existing lines."
            )
            return

        # Create a distinctive blue dashed line for zoom region
        zoom_line = InfiniteLine(
            pos=x,
            angle=90,
            pen=mkPen('b', width=3, style=Qt.DashLine),
            movable=True  # Make it draggable
        )

        # Connect signal for when line is moved
        zoom_line.sigPositionChanged.connect(self.update_zoom_region)

        self.plot_widget.addItem(zoom_line)
        self.zoom_region_lines.append((x, zoom_line))

        logging.info(f"Added zoom region line at x={x:.2f}")

        # If we now have 2 lines, apply zoom
        if len(self.zoom_region_lines) == 2:
            self.update_zoom_region()

    def remove_zoom_region_line(self, x):
        """Remove the nearest zoom region line"""
        if not self.zoom_region_lines:
            return

        # Find nearest zoom region line
        distances = [abs(line[0] - x) for line in self.zoom_region_lines]
        nearest_index = np.argmin(distances)

        # Remove the line
        _, zoom_line = self.zoom_region_lines[nearest_index]
        self.plot_widget.removeItem(zoom_line)
        self.zoom_region_lines.pop(nearest_index)

        logging.info(f"Removed zoom region line at x={x:.2f}")

        # If we now have less than 2 lines, restore original range
        if len(self.zoom_region_lines) < 2:
            self.restore_original_range()

    def update_zoom_region(self):
        """Update the plot zoom based on the two region lines"""
        if len(self.zoom_region_lines) != 2:
            return

        # Get x positions of both lines
        x1 = self.zoom_region_lines[0][1].value()
        x2 = self.zoom_region_lines[1][1].value()

        # Determine min and max
        x_min = min(x1, x2)
        x_max = max(x1, x2)

        # Apply zoom with small padding
        self.plot_widget.setXRange(x_min, x_max, padding=0.02)

        logging.info(f"Zoomed to region: {x_min:.2f} to {x_max:.2f}")

    def restore_original_range(self):
        """Restore the plot to its original data range"""
        if self.original_x_range is not None:
            self.plot_widget.setXRange(
                self.original_x_range[0],
                self.original_x_range[1],
                padding=0.02
            )
            logging.info(f"Restored original range: {self.original_x_range}")

    def clear_zoom_region(self):
        """Clear all zoom region lines and restore original range"""
        for _, zoom_line in self.zoom_region_lines:
            self.plot_widget.removeItem(zoom_line)
        self.zoom_region_lines = []
        self.restore_original_range()
        logging.info("Cleared all zoom region lines")

    def clear_plot(self):
        """Clear the plot"""
        logging.info("Clearing plot in PlotArea")
        self.plot_widget.clear()
        self.plot_items = []
        self.original_lines = []
        self.smoothed_lines = []
        self.y_axes = []
        self.vertical_lines = []
        self.annotations = []
        self.zoom_region_lines = []
        self.original_x_range = None

        # Re-add basic items
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_h, ignoreBounds=True)
        self.plot_widget.addItem(self.cursor_label, ignoreBounds=True)

        self.plot_widget.setTitle("No data to display")
        self.plot_widget.setLabel('bottom', "X-axis")
        self.plot_widget.setLabel('left', "Y-axis")
        self.reset_title()

    def reset_title(self):
        """Reset the title"""
        self.current_title = ""
        self.title_input.clear()
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = ""
        self.plot_widget.setTitle("")

    def enable_insertion(self, text):
        self.text_insertion_mode = True
        self.pending_text= text
        self.plot_widget.setCursor(Qt.CrossCursor)

        # Show message to user
        QMessageBox.information(
            self,
            "Text Insertion Mode",
            "Click anywhere on the plot to place the text.\nRight-click to cancel."
        )

    def toggle_text_insertion_mode(self, checked):
        """Toggle text insertion mode on/off"""
        if checked:
            # Get text from comment box
            comment_box = self.get_comment_box()
            if comment_box:
                text = comment_box.get_comments()
                if text.strip():
                    self.text_insertion_mode = True
                    self.pending_text = text
                    self.plot_widget.setCursor(Qt.CrossCursor)
                    logging.info("Text insertion mode enabled")

                    # Uncheck other modes
                    if hasattr(self, 'remove_text_action'):
                        self.remove_text_action.setChecked(False)
                    if hasattr(self, 'zoom_region_checkbox'):
                        self.zoom_region_checkbox.setChecked(False)
                        self.zoom_mode_active = False
                else:
                    QMessageBox.warning(
                        self,
                        "No Text",
                        "Please enter text in the Comments box first."
                    )
                    self.insert_text_action.setChecked(False)
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Comment box not found. Please ensure the application is properly initialized."
                )
                self.insert_text_action.setChecked(False)
        else:
            self.cancel_text_insertion()

    def get_comment_box(self):
        """Get reference to comment box from main window"""
        main_window = self.window()
        # Adjust this path based on your actual widget hierarchy
        # Common patterns:
        if hasattr(main_window, 'comment_box'):
            return main_window.comment_box
        elif hasattr(main_window, 'right_panel') and hasattr(main_window.right_panel, 'comment_box'):
            return main_window.right_panel.comment_box
        elif hasattr(main_window, 'left_panel') and hasattr(main_window.left_panel, 'comment_box'):
            return main_window.left_panel.comment_box
        else:
            # Try to find it in children
            for child in main_window.findChildren(QGroupBox):
                if child.title() == "Comments":
                    return child
        return None

    def toggle_text_removal_mode(self, checked):
        """Toggle text removal mode on/off"""
        if checked:
            if not self.floating_text_items:
                QMessageBox.information(
                    self,
                    "No Texts",
                    "There are no text boxes to remove."
                )
                self.remove_text_action.setChecked(False)
                return

            self.text_removal_mode = True
            self.plot_widget.setCursor(Qt.PointingHandCursor)
            logging.info("Text removal mode enabled")

            # Uncheck other modes
            if hasattr(self, 'insert_text_action'):
                self.insert_text_action.setChecked(False)
            if hasattr(self, 'zoom_region_checkbox'):
                self.zoom_region_checkbox.setChecked(False)
                self.zoom_mode_active = False

            QMessageBox.information(
                self,
                "Text Removal Mode",
                "Click on a text box to remove it.\nClick toolbar button again to exit this mode."
            )
        else:
            self.text_removal_mode = False
            self.plot_widget.setCursor(Qt.ArrowCursor)
            logging.info("Text removal mode disabled")

    def cancel_text_insertion(self):
        """Cancel text insertion mode"""
        self.text_insertion_mode = False
        self.pending_text = ""
        self.plot_widget.setCursor(Qt.ArrowCursor)

        if hasattr(self, 'insert_text_action'):
            self.insert_text_action.setChecked(False)

        logging.info("Text insertion mode cancelled")

    def clear_all_axes(self):
        """Completely clear all plot items and axes"""
        logging.info("Clearing all axes and plot items")

        # Clear the plot widget
        self.plot_widget.clear()

        # Remove all additional Y-axes viewboxes from scene
        if hasattr(self, 'y_axes'):
            for viewbox in self.y_axes:
                try:
                    if viewbox.scene() is not None:
                        self.plot_widget.scene().removeItem(viewbox)
                except Exception as e:
                    logging.warning(f"Error removing viewbox: {e}")

        # Remove all axis items from layout
        layout = self.plot_widget.plotItem.layout
        for i in range(20):  # Check many positions
            # Right side
            try:
                item = layout.itemAt(2, 3 + i)
                if item is not None:
                    layout.removeItem(item)
            except:
                pass
            # Left side (skip position 1 which is the main axis)
            if i > 0:
                try:
                    item = layout.itemAt(2, 1 - i)
                    if item is not None:
                        layout.removeItem(item)
                except:
                    pass

        # Reset storage
        self.plot_items = []
        self.original_lines = []
        self.smoothed_lines = []
        self.y_axes = []

        logging.info("All axes cleared successfully")