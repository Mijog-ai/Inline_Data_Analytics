import logging
import traceback
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QMessageBox,
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

        # Enable antialiasing for smoother lines and performance optimizations
        pg.setConfigOptions(
            antialias=True,
            useOpenGL=True,  # Enable OpenGL for better performance
            enableExperimental=True  # Enable experimental optimizations
        )
        self.plot_widget.setMouseEnabled(x=False, y=False)

        self.layout.addWidget(self.plot_widget)
        
        # Create custom legend area below the plot (Excel-style)
        self.legend_widget = QWidget()
        self.legend_layout = QHBoxLayout(self.legend_widget)
        self.legend_layout.setContentsMargins(10, 5, 10, 5)
        self.legend_layout.setSpacing(15)
        self.legend_widget.setStyleSheet("background-color: white; border-top: 1px solid #ccc;")
        self.legend_widget.setMaximumHeight(60)
        self.legend_items = []  # Store legend items
        self.layout.addWidget(self.legend_widget)

        self.setLayout(self.layout)

        # Setup mouse click event
        self.plot_widget.scene().sigMouseClicked.connect(self.on_click)
        
        # Setup double-click event
        self.plot_widget.scene().sigMouseClicked.connect(self.on_double_click)

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
        # Remove default legend - we'll use custom legend below
        self.legend = None

    def create_toolbar(self):
        self.toolbar = QToolBar("Plot Tools")
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Show Cursor Action
        self.cursor_action = QAction("Show Cursor", self)
        self.cursor_action.setCheckable(True)
        self.cursor_action.setChecked(False)
        self.cursor_action.setToolTip("Toggle crosshair cursor on/off")
        self.cursor_action.triggered.connect(self.toggle_cursor)
        self.toolbar.addAction(self.cursor_action)

        self.toolbar.addSeparator()

        # Show Legend Action
        self.legend_action = QAction("Show Legend", self)
        self.legend_action.setCheckable(True)
        self.legend_action.setChecked(True)
        self.legend_action.setToolTip("Toggle legend visibility")
        self.legend_action.triggered.connect(self.toggle_legend)
        self.toolbar.addAction(self.legend_action)

        self.toolbar.addSeparator()

        # Highlight Mode Action
        self.highlighter_action = QAction("Highlight Mode", self)
        self.highlighter_action.setCheckable(True)
        self.highlighter_action.setChecked(False)
        self.highlighter_action.setToolTip("Enable highlight mode - right click to add highlights, double click to remove")
        self.highlighter_action.triggered.connect(self.toggle_highlighter)
        self.toolbar.addAction(self.highlighter_action)

        self.toolbar.addSeparator()

        # Zoom Region Mode Action
        self.zoom_region_action = QAction("Zoom Region", self)
        self.zoom_region_action.setCheckable(True)
        self.zoom_region_action.setChecked(False)
        self.zoom_region_action.setToolTip("Enable zoom region mode - left click to add boundary lines (max 2), right click to remove")
        self.zoom_region_action.triggered.connect(self.toggle_zoom_region_mode)
        self.toolbar.addAction(self.zoom_region_action)

        self.toolbar.addSeparator()

        # Insert Text Action
        self.insert_text_action = QAction("Insert Text", self)
        self.insert_text_action.setCheckable(True)
        self.insert_text_action.setToolTip("Enable text insertion mode - left click on plot to place text")
        self.insert_text_action.triggered.connect(self.toggle_text_insertion_mode)
        self.toolbar.addAction(self.insert_text_action)

        self.toolbar.addSeparator()

        # Remove Text Action
        self.remove_text_action = QAction("Remove Text", self)
        self.remove_text_action.setCheckable(True)
        self.remove_text_action.setToolTip("Enable text removal mode - left click on text to remove it")
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
            # Batch removal with signal blocking for better performance
            self.plot_widget.blockSignals(True)
            for text_data in self.floating_text_items:
                self.plot_widget.removeItem(text_data['item'])
            self.plot_widget.blockSignals(False)
            self.floating_text_items = []

            # Uncheck removal mode if active
            if hasattr(self, 'remove_text_action'):
                self.remove_text_action.setChecked(False)
            self.text_removal_mode = False

            logging.info("Cleared all floating texts")
            QMessageBox.information(self, "Cleared", "All text boxes have been removed.")

    def toggle_highlighter(self, state):
        self.yaxis_approx_value_highlighter = bool(state)
        # Uncheck other exclusive modes
        if state:
            if hasattr(self, 'zoom_region_action'):
                self.zoom_region_action.setChecked(False)
            if hasattr(self, 'insert_text_action'):
                self.insert_text_action.setChecked(False)
            if hasattr(self, 'remove_text_action'):
                self.remove_text_action.setChecked(False)
            self.zoom_mode_active = False
            self.text_insertion_mode = False
            self.text_removal_mode = False
            self.plot_widget.setCursor(Qt.ArrowCursor)
        logging.info(f"Highlight mode: {state}")

    def toggle_cursor(self, state):
        self.show_cursor = bool(state)
        self.crosshair_v.setVisible(self.show_cursor)
        self.crosshair_h.setVisible(self.show_cursor)
        self.cursor_label.setVisible(self.show_cursor)

    def toggle_legend(self, state):
        self.show_legend = bool(state)
        if hasattr(self, 'legend_widget'):
            self.legend_widget.setVisible(self.show_legend)

    def clear_custom_legend(self):
        """Clear all items from the custom legend"""
        if hasattr(self, 'legend_layout'):
            # Remove all widgets from legend layout
            while self.legend_layout.count():
                item = self.legend_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.legend_items = []

    def populate_custom_legend(self, y_columns, colors, has_smoothing):
        """Populate the custom legend below the plot (Excel-style)"""
        self.clear_custom_legend()
        
        # Add stretch at the beginning to center the legend items
        self.legend_layout.addStretch()
        
        for y_column, color in zip(y_columns, colors):
            # Create legend item container
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(5)
            
            # Color indicator (line)
            color_label = QLabel()
            color_label.setFixedSize(30, 3)
            color_label.setStyleSheet(f"background-color: {color.name()}; border: none;")
            item_layout.addWidget(color_label)
            
            # Text label
            text_label = QLabel(y_column)
            text_label.setStyleSheet("font-size: 10pt; color: black;")
            item_layout.addWidget(text_label)
            
            self.legend_layout.addWidget(item_widget)
            self.legend_items.append(item_widget)
            
            # If smoothing is applied, add smoothed version
            if has_smoothing:
                # Add some spacing
                spacer = QLabel("  ")
                self.legend_layout.addWidget(spacer)
                
                # Create smoothed legend item
                smoothed_widget = QWidget()
                smoothed_layout = QHBoxLayout(smoothed_widget)
                smoothed_layout.setContentsMargins(0, 0, 0, 0)
                smoothed_layout.setSpacing(5)
                
                # Color indicator (solid line for smoothed)
                smoothed_color_label = QLabel()
                smoothed_color_label.setFixedSize(30, 3)
                smoothed_color_label.setStyleSheet(f"background-color: {color.name()}; border: none;")
                smoothed_layout.addWidget(smoothed_color_label)
                
                # Text label
                smoothed_text_label = QLabel(f"{y_column} (Smoothed)")
                smoothed_text_label.setStyleSheet("font-size: 10pt; color: black;")
                smoothed_layout.addWidget(smoothed_text_label)
                
                self.legend_layout.addWidget(smoothed_widget)
                self.legend_items.append(smoothed_widget)
        
        # Add stretch at the end to center the legend items
        self.legend_layout.addStretch()
        
        logging.info(f"Custom legend populated with {len(self.legend_items)} items")

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

    def find_nearest_index(self, x_data, x_value):
        """Find nearest index using binary search - O(log n) instead of O(n)"""
        if len(x_data) == 0:
            return 0

        # Use searchsorted for O(log n) lookup (assumes sorted data)
        idx = np.searchsorted(x_data, x_value)

        # Clamp to valid range
        idx = np.clip(idx, 0, len(x_data) - 1)

        # Check if previous index is closer
        if idx > 0:
            if abs(x_data[idx - 1] - x_value) < abs(x_data[idx] - x_value):
                idx = idx - 1

        return idx

    def plot_data(self, df, x_column, y_columns, smoothing_params, limit_lines=[], title=None):
        try:
            if title is not None:
                self.current_title = title
            else:
                title = self.current_title
            logging.info(f"Plotting data: x={x_column}, y={y_columns}, title={title}")

            # Disable updates during batch operations for performance
            self.plot_widget.setUpdatesEnabled(False)

            self.clear_all_axes()

            # Clear previous plot
            self.plot_widget.clear()
            self.plot_items = []
            self.original_lines = []
            self.smoothed_lines = []
            self.y_axes = []

            # Clear custom legend
            self.clear_custom_legend()

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

            # Store all y data ranges for proper scaling
            all_y_ranges = []
            for y_column in y_columns:
                y_data = df[y_column].values
                if len(y_data) > 0:
                    y_min = float(np.min(y_data))
                    y_max = float(np.max(y_data))
                    all_y_ranges.append((y_min, y_max))

            for i, (y_column, color) in enumerate(zip(y_columns, colors)):
                logging.debug(f"Plotting column: {y_column}")

                x_data = df[x_column].values
                y_data = df[y_column].values

                # For now, use only the main viewbox to avoid complexity
                # Multi-axis support can be added later with proper implementation
                if i == 0:
                    viewbox = main_viewbox
                    self.plot_widget.setLabel('left', y_column, color=color.name())
                else:
                    # Use main viewbox for all plots for now
                    viewbox = main_viewbox
                    # Note: Multiple Y-axes disabled temporarily to fix rendering issues

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

                # Plot original data - all use main viewbox now
                original_curve = pg.PlotDataItem(
                    x_data, y_data,
                    pen=original_pen,
                    name=f'{y_column} (Original)',
                    clipToView=True,
                    autoDownsample=True,
                    downsampleMethod='subsample'
                )

                # Add to viewbox
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
                        name=f'{y_column} (Smoothed)',
                        clipToView=True,
                        autoDownsample=True,
                        downsampleMethod='subsample'
                    )

                    # Add to viewbox
                    viewbox.addItem(smoothed_curve)

                    self.smoothed_lines.append(smoothed_curve)
                    self.plot_items.append({
                        'curve': smoothed_curve,
                        'x_data': x_data,
                        'y_data': y_smoothed,
                        'label': y_column,
                        'viewbox': viewbox
                    })

            # Populate custom legend below plot (Excel-style)
            if self.show_legend:
                self.populate_custom_legend(y_columns, colors, smoothing_params['apply'])

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
            self.toggle_cursor(self.cursor_action.isChecked())

            # Calculate and set X-axis range starting from 0 or min(x)
            all_x_data = df[x_column].values
            if len(all_x_data) > 0:
                x_min = float(np.min(all_x_data))
                x_max = float(np.max(all_x_data))

                # Start from 0 if data is positive, otherwise from min(x)
                x_start = 0 if x_min >= 0 else x_min

                # Store original range for zoom operations
                self.original_x_range = (x_start, x_max)

                # Set X range with limits - always show from start point
                main_viewbox.setLimits(xMin=x_start, xMax=x_max)
                main_viewbox.setXRange(x_start, x_max, padding=0.02)

                logging.info(f"X-axis range set: [{x_start:.2f}, {x_max:.2f}]")

            # Set Y-axis range for the main viewbox based on all data
            if len(all_y_ranges) > 0:
                # Find the overall min and max across all y columns
                overall_y_min = min(y_range[0] for y_range in all_y_ranges)
                overall_y_max = max(y_range[1] for y_range in all_y_ranges)

                # Start from 0 if data is positive, otherwise from min(y)
                y_start = 0 if overall_y_min >= 0 else overall_y_min

                # Add some padding to y_max for better visibility
                y_range = overall_y_max - y_start
                y_max_padded = overall_y_max + (y_range * 0.05)

                # Set Y range with limits for main viewbox
                main_viewbox.setLimits(yMin=y_start, yMax=y_max_padded)
                main_viewbox.setYRange(y_start, y_max_padded, padding=0)

                logging.info(f"Y-axis range set: [{y_start:.2f}, {y_max_padded:.2f}]")

            # Disable auto-range after setting ranges to prevent automatic adjustments
            main_viewbox.enableAutoRange(enable=False)

            # Always show original data
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

            # Re-enable updates after batch operations complete
            self.plot_widget.setUpdatesEnabled(True)
            self.plot_widget.update()  # Force a single update

        except Exception as e:
            logging.error(f"Error in plot_data: {str(e)}")
            logging.error(traceback.format_exc())
            # Re-enable updates even on error
            self.plot_widget.setUpdatesEnabled(True)
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

            # Find nearest data points (optimized with binary search)
            cursor_text = f"{xlabel}: {x:.2f}\n"

            for item in self.plot_items:
                if item['curve'].isVisible():
                    x_data = item['x_data']
                    y_data = item['y_data']

                    if len(x_data) > 0:
                        idx = self.find_nearest_index(x_data, x)
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
            # Priority: Text operations > Zoom
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

        elif event.button() == Qt.RightButton:
            # Right-click: Cancel modes OR add highlight
            if self.text_insertion_mode:
                self.cancel_text_insertion()
            elif self.text_removal_mode:
                self.remove_text_action.setChecked(False)
                self.toggle_text_removal_mode(False)
            elif self.zoom_mode_active:
                self.remove_zoom_region_line(x)
            elif self.yaxis_approx_value_highlighter:
                # Right-click adds highlight in highlight mode
                self.add_highlight(x)

    def on_double_click(self, event):
        """Handle double-click events for removing highlights"""
        # Only process double-clicks
        if event.double():
            pos = event.scenePos()
            if not self.plot_widget.sceneBoundingRect().contains(pos):
                return

            mouse_point = self.plot_widget.getViewBox().mapSceneToView(pos)
            x = mouse_point.x()

            # Double-click removes highlight in highlight mode
            if self.yaxis_approx_value_highlighter:
                self.remove_nearest_highlight(x)

    def add_highlight(self, x):
        """Add vertical line and highlight points at x position (optimized)"""
        # Get x-axis label
        xlabel = self.last_plot_params.get('x_column', 'X') if hasattr(self, 'last_plot_params') else 'X'

        # Collect all items for this highlight
        points_group = []

        # Get the main viewbox
        main_viewbox = self.plot_widget.getViewBox()

        # Disable updates during batch add for performance
        self.plot_widget.setUpdatesEnabled(False)

        # Create separate annotation for each line at its intersection point
        for item in self.plot_items:
            if item['curve'].isVisible():
                x_data = item['x_data']
                y_data = item['y_data']

                if len(x_data) > 0:
                    # Find nearest point (optimized with binary search)
                    idx = self.find_nearest_index(x_data, x)
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

        # Re-enable updates after batch operations complete
        self.plot_widget.setUpdatesEnabled(True)
        self.plot_widget.update()  # Force a single update


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

    def remove_floating_text_at_position(self, x, y):
        """Remove floating text near the clicked position"""
        if not self.floating_text_items:
            return False

        # Find text within a reasonable distance threshold
        threshold = 50  # pixels in scene coordinates
        closest_text = None
        min_distance = float('inf')

        for text_data in self.floating_text_items:
            text_x, text_y = text_data['position']
            distance = np.sqrt((text_x - x)**2 + (text_y - y)**2)
            
            if distance < min_distance:
                min_distance = distance
                closest_text = text_data

        # If found text within threshold, remove it
        if closest_text and min_distance < threshold:
            self.plot_widget.removeItem(closest_text['item'])
            self.floating_text_items.remove(closest_text)
            logging.info(f"Removed floating text at ({closest_text['position'][0]:.2f}, {closest_text['position'][1]:.2f})")
            return True

        return False

    def remove_nearest_highlight(self, x):
        """Remove the nearest vertical line, points, and annotation (optimized)"""
        if not self.vertical_lines:
            return

        # Find nearest vertical line using numpy for efficiency
        distances = np.array([abs(vline[0] - x) for vline in self.vertical_lines])
        nearest_index = np.argmin(distances)

        # Remove all items with their correct viewboxes (batch operation)
        _, points_group = self.vertical_lines[nearest_index]

        # Block signals for batch removal
        for item, viewbox in points_group:
            try:
                viewbox.blockSignals(True)
                viewbox.removeItem(item)
                viewbox.blockSignals(False)
            except Exception as e:
                logging.warning(f"Could not remove item from viewbox: {e}")
                # Fallback: try removing from plot widget
                try:
                    self.plot_widget.removeItem(item)
                except:
                    pass

        # Remove from list
        self.vertical_lines.pop(nearest_index)
        logging.info(f"Removed highlight at x={x:.2f} (optimized)")

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
        """Toggle visibility of original data lines (optimized - no rebuild)"""
        show_original = True  # Always show original data now
        logging.info(f"Original data visibility: {show_original}")

        # Block signals to prevent multiple repaints
        for line in self.original_lines:
            line.setVisible(show_original)

        logging.info("Original data visibility toggled (optimized)")

    def get_show_original_state(self):
        """Get the state of show original - always True now"""
        return True

    def set_show_original_state(self, state):
        """Set the state of show original - deprecated, always shows original"""
        pass  # No longer used

    def toggle_zoom_region_mode(self, state):
        """Toggle zoom region mode on/off"""
        self.zoom_mode_active = bool(state)
        # Uncheck other exclusive modes
        if state:
            if hasattr(self, 'highlighter_action'):
                self.highlighter_action.setChecked(False)
            if hasattr(self, 'insert_text_action'):
                self.insert_text_action.setChecked(False)
            if hasattr(self, 'remove_text_action'):
                self.remove_text_action.setChecked(False)
            self.yaxis_approx_value_highlighter = False
            self.text_insertion_mode = False
            self.text_removal_mode = False
            self.plot_widget.setCursor(Qt.ArrowCursor)
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
            main_viewbox = self.plot_widget.getViewBox()
            main_viewbox.setXRange(
                self.original_x_range[0],
                self.original_x_range[1],
                padding=0.02
            )
            
            # Restore Y range based on all visible data
            if hasattr(self, 'last_plot_params'):
                df = self.last_plot_params['df']
                y_columns = self.last_plot_params['y_columns']
                
                all_y_data = []
                for y_column in y_columns:
                    all_y_data.extend(df[y_column].values)
                
                if len(all_y_data) > 0:
                    y_min = float(np.min(all_y_data))
                    y_max = float(np.max(all_y_data))
                    y_start = 0 if y_min >= 0 else y_min
                    y_range = y_max - y_start
                    y_max_padded = y_max + (y_range * 0.05)
                    main_viewbox.setYRange(y_start, y_max_padded, padding=0)
            
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
        
        # Clear all axes first to prevent viewbox issues
        self.clear_all_axes()
        
        # Clear the plot widget
        self.plot_widget.clear()
        
        # Reset all data structures
        self.plot_items = []
        self.original_lines = []
        self.smoothed_lines = []
        self.y_axes = []
        self.vertical_lines = []
        self.annotations = []
        self.zoom_region_lines = []
        self.original_x_range = None
        self.floating_text_items = []
        self.highlight_points = []
        
        # Clear last plot params to prevent replotting old data
        if hasattr(self, 'last_plot_params'):
            delattr(self, 'last_plot_params')

        # Clear custom legend
        self.clear_custom_legend()

        # Re-add basic items
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_h, ignoreBounds=True)
        self.plot_widget.addItem(self.cursor_label, ignoreBounds=True)

        self.plot_widget.setTitle("No data to display")
        self.plot_widget.setLabel('bottom', "X-axis")
        self.plot_widget.setLabel('left', "Y-axis")
        self.reset_title()
        
        logging.info("Plot cleared successfully")

    def reset_title(self):
        """Reset the title"""
        self.current_title = ""
        self.title_input.clear()
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = ""
        self.plot_widget.setTitle("")

    def set_default_title(self, title):
        """Set the default title in the input field and apply it"""
        self.title_input.setText(title)
        self.current_title = title
        self.plot_widget.setTitle(title)
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = title

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

                    # Uncheck other exclusive modes
                    if hasattr(self, 'remove_text_action'):
                        self.remove_text_action.setChecked(False)
                    if hasattr(self, 'zoom_region_action'):
                        self.zoom_region_action.setChecked(False)
                    if hasattr(self, 'highlighter_action'):
                        self.highlighter_action.setChecked(False)
                    self.zoom_mode_active = False
                    self.text_removal_mode = False
                    self.yaxis_approx_value_highlighter = False
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

            # Uncheck other exclusive modes
            if hasattr(self, 'insert_text_action'):
                self.insert_text_action.setChecked(False)
            if hasattr(self, 'zoom_region_action'):
                self.zoom_region_action.setChecked(False)
            if hasattr(self, 'highlighter_action'):
                self.highlighter_action.setChecked(False)
            self.zoom_mode_active = False
            self.text_insertion_mode = False
            self.yaxis_approx_value_highlighter = False

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

        # Remove all plot data items first to prevent viewbox errors
        for item_data in self.plot_items:
            try:
                curve = item_data.get('curve')
                viewbox = item_data.get('viewbox')
                if curve and viewbox:
                    viewbox.removeItem(curve)
            except Exception as e:
                logging.warning(f"Error removing curve from viewbox: {e}")

        # Remove all additional Y-axes viewboxes from scene
        if hasattr(self, 'y_axes'):
            for viewbox in self.y_axes:
                try:
                    # Remove all items from viewbox first
                    for item in list(viewbox.allChildren()):
                        try:
                            viewbox.removeItem(item)
                        except:
                            pass
                    
                    # Then remove viewbox from scene
                    if viewbox.scene() is not None:
                        self.plot_widget.scene().removeItem(viewbox)
                except Exception as e:
                    logging.warning(f"Error removing viewbox: {e}")

        # Remove all axis items from layout more carefully
        layout = self.plot_widget.plotItem.layout
        items_to_remove = []
        
        # Collect items to remove (avoid modifying during iteration)
        for row in range(layout.rowCount()):
            for col in range(layout.columnCount()):
                try:
                    item = layout.itemAt(row, col)
                    if item is not None and isinstance(item, pg.AxisItem):
                        # Don't remove the main left and bottom axes (positions 2,1 and 3,2)
                        if not ((row == 2 and col == 1) or (row == 3 and col == 2)):
                            items_to_remove.append(item)
                except:
                    pass
        
        # Remove collected items
        for item in items_to_remove:
            try:
                layout.removeItem(item)
            except Exception as e:
                logging.warning(f"Error removing axis item: {e}")

        # Reset storage
        self.plot_items = []
        self.original_lines = []
        self.smoothed_lines = []
        self.y_axes = []

        logging.info("All axes cleared successfully")