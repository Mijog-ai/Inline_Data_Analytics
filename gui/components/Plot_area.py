"""
Plot Area Component - PyQtGraph with Multi-Axis Support
Handles all plotting functionality with multiple Y-axes support
"""

import logging
import traceback
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
    QLabel, QLineEdit, QPushButton, QToolBar, QAction, QGroupBox,
    QComboBox, QFrame
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

from utils.asc_utils import apply_smoothing


class PlotArea(QWidget):
    """
    Main plotting area with multi-axis support using PyQtGraph
    """

    def __init__(self, parent):
        super().__init__(parent)

        # Initialize state variables
        self._init_state_variables()

        # Setup UI components
        self.setup_ui()

    def _init_state_variables(self):
        """Initialize all state tracking variables"""
        # Display modes
        self.show_cursor = False
        self.show_legend = True
        self.yaxis_approx_value_highlighter = False
        self.zoom_mode_active = False
        self.text_insertion_mode = False
        self.text_removal_mode = False

        # Plot data storage
        self.plot_items = []
        self.y_axes = []
        self.legend_items = []
        self.axis_colors = []

        # Interactive elements
        self.vertical_lines = []
        self.annotations = []
        self.highlight_points = []
        self.zoom_region_lines = []
        self.floating_text_items = []

        # Crosshair elements
        self.crosshair_vline = None
        self.crosshair_hline = None
        self.cursor_annotation = None

        # Plot state
        self.current_title = ""
        self.original_x_range = None
        self.pending_text = ""
        self.last_plot_params = {}

        # Data storage
        self.current_df = None
        self.x_column = None
        self.available_columns = []

        # Color palette for different columns
        self.colors = [
            (255, 100, 100),   # Red
            (100, 255, 100),   # Green
            (100, 100, 255),   # Blue
            (255, 255, 100),   # Yellow
            (255, 100, 255),   # Magenta
            (100, 255, 255),   # Cyan
            (255, 150, 100),   # Orange
            (150, 100, 255),   # Purple
            (255, 200, 100),   # Light Orange
            (100, 255, 200),   # Aqua
        ]

    def setup_ui(self):
        """Setup the complete UI structure"""
        self.layout = QVBoxLayout(self)

        # Title controls
        self._create_title_controls()

        # Toolbar with interactive tools
        self._create_toolbar()
        self.layout.addWidget(self.toolbar)

        # X-axis range controls
        self._create_x_axis_controls()

        # Main plot widget
        self._create_plot_widget()
        self.layout.addWidget(self.graphics_view)

        # Custom legend area
        self._create_legend_area()
        self.layout.addWidget(self.legend_widget)

        self.setLayout(self.layout)

    def _create_title_controls(self):
        """Create title input and set button"""
        title_layout = QHBoxLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter plot title")

        self.set_title_button = QPushButton("Set Title")
        self.set_title_button.clicked.connect(self._on_set_title)

        title_layout.addWidget(QLabel("Plot Title:"))
        title_layout.addWidget(self.title_input)
        title_layout.addWidget(self.set_title_button)
        self.layout.addLayout(title_layout)


    def _create_x_axis_controls(self):
        """Create X-axis range controls"""
        x_axis_layout = QHBoxLayout()

        x_label = QLabel("X-Axis Range:")
        x_label.setStyleSheet("font-weight: bold;")
        x_axis_layout.addWidget(x_label)

        x_axis_layout.addWidget(QLabel("Min:"))
        self.x_min_input = QLineEdit("0.0")
        self.x_min_input.setFixedWidth(100)
        x_axis_layout.addWidget(self.x_min_input)

        x_axis_layout.addWidget(QLabel("Max:"))
        self.x_max_input = QLineEdit("100.0")
        self.x_max_input.setFixedWidth(100)
        x_axis_layout.addWidget(self.x_max_input)

        # Apply and Reset buttons
        apply_button = QPushButton("Apply X-Range")
        apply_button.setFixedWidth(120)
        apply_button.clicked.connect(self.update_x_axis_range)
        x_axis_layout.addWidget(apply_button)

        reset_button = QPushButton("Reset X-Range")
        reset_button.setFixedWidth(120)
        reset_button.clicked.connect(self.reset_x_axis_range)
        x_axis_layout.addWidget(reset_button)

        x_axis_layout.addStretch()

        self.layout.addLayout(x_axis_layout)

    def _create_toolbar(self):
        """Create toolbar with all interactive tools"""
        self.toolbar = QToolBar("Plot Tools")
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Cursor toggle
        self.cursor_action = self._create_action(
            "Show Cursor",
            "Toggle crosshair cursor on/off",
            checkable=True,
            checked=False,
            callback=self._on_toggle_cursor
        )
        self.toolbar.addAction(self.cursor_action)
        self.toolbar.addSeparator()

        # Legend toggle
        self.legend_action = self._create_action(
            "Show Legend",
            "Toggle legend visibility",
            checkable=True,
            checked=True,
            callback=self._on_toggle_legend
        )
        self.toolbar.addAction(self.legend_action)
        self.toolbar.addSeparator()

        # Highlight mode
        self.highlighter_action = self._create_action(
            "Highlight Mode",
            "Enable highlight mode - right click to add highlights, double click to remove",
            checkable=True,
            checked=False,
            callback=self._on_toggle_highlighter
        )
        self.toolbar.addAction(self.highlighter_action)
        self.toolbar.addSeparator()

        # Text insertion
        self.insert_text_action = self._create_action(
            "Insert Text",
            "Enable text insertion mode - left click on plot to place text",
            checkable=True,
            checked=False,
            callback=self._on_toggle_text_insertion
        )
        self.toolbar.addAction(self.insert_text_action)
        self.toolbar.addSeparator()

        # Clear all texts
        self.clear_texts_action = self._create_action(
            "Clear All Texts",
            "Remove all floating text boxes from plot",
            checkable=False,
            callback=self._on_clear_all_texts
        )
        self.toolbar.addAction(self.clear_texts_action)

    def _create_action(self, text, tooltip, checkable=False, checked=False, callback=None):
        """Helper to create toolbar actions"""
        action = QAction(text, self)
        action.setToolTip(tooltip)
        if checkable:
            action.setCheckable(True)
            action.setChecked(checked)
        if callback:
            action.triggered.connect(callback)
        return action

    def _create_plot_widget(self):
        """Create and configure the main plot widget"""
        # Create GraphicsView for PyQtGraph
        self.graphics_view = pg.GraphicsView()
        self.graphics_view.setMinimumHeight(400)
        self.graphics_view.setBackground('w')

        # Create layout for the plot
        self.plot_layout = pg.GraphicsLayout()
        self.graphics_view.setCentralItem(self.plot_layout)

        # Create the main plot
        self.main_plot = self.plot_layout.addPlot()
        self.main_plot.setLabel('bottom', 'X-axis')
        self.main_plot.setLabel('left', 'Y-axis')
        self.main_plot.showGrid(x=True, y=True, alpha=0.3)

        # Enable mouse interaction
        self.main_plot.setMouseEnabled(x=True, y=True)

        # Connect mouse events
        self.main_plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self.main_plot.scene().sigMouseClicked.connect(self._on_mouse_click)

        # Create crosshair (initially hidden)
        self.crosshair_vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('k', style=QtCore.Qt.DashLine))
        self.crosshair_hline = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('k', style=QtCore.Qt.DashLine))
        self.crosshair_vline.setVisible(False)
        self.crosshair_hline.setVisible(False)
        self.main_plot.addItem(self.crosshair_vline)
        self.main_plot.addItem(self.crosshair_hline)

        # Create cursor text item
        self.cursor_annotation = pg.TextItem("", anchor=(0, 1), color='k')
        self.cursor_annotation.setVisible(False)
        self.main_plot.addItem(self.cursor_annotation)

    def _create_legend_area(self):
        """Create custom legend area below plot"""
        self.legend_widget = QWidget()
        self.legend_layout = QHBoxLayout(self.legend_widget)
        self.legend_layout.setContentsMargins(10, 5, 10, 5)
        self.legend_layout.setSpacing(15)
        self.legend_widget.setStyleSheet(
            "background-color: white; border-top: 1px solid #ccc;"
        )
        self.legend_widget.setMaximumHeight(60)

    # ========================================================================
    # TOOLBAR ACTION HANDLERS
    # ========================================================================

    def _on_toggle_cursor(self, state):
        """Toggle crosshair cursor visibility"""
        self.show_cursor = bool(state)
        if self.crosshair_vline:
            self.crosshair_vline.setVisible(self.show_cursor)
        if self.crosshair_hline:
            self.crosshair_hline.setVisible(self.show_cursor)
        if self.cursor_annotation:
            self.cursor_annotation.setVisible(self.show_cursor)
        logging.info(f"Cursor visibility: {self.show_cursor}")

    def _on_toggle_legend(self, state):
        """Toggle legend visibility"""
        self.show_legend = bool(state)
        self.legend_widget.setVisible(self.show_legend)
        logging.info(f"Legend visibility: {self.show_legend}")

    def _on_toggle_highlighter(self, state):
        """Toggle highlight mode"""
        self.yaxis_approx_value_highlighter = bool(state)

        if state:
            self._deactivate_other_modes(exclude='highlighter')

        logging.info(f"Highlight mode: {state}")

    def _on_toggle_text_insertion(self, checked):
        """Toggle text insertion mode"""
        if checked:
            comment_box = self._get_comment_box()
            if not comment_box:
                QMessageBox.warning(
                    self, "Error",
                    "Comment box not found. Please ensure the application is properly initialized."
                )
                self.insert_text_action.setChecked(False)
                return

            text = comment_box.get_comments()
            if not text.strip():
                QMessageBox.warning(
                    self, "No Text",
                    "Please enter text in the Comments box first."
                )
                self.insert_text_action.setChecked(False)
                return

            self.text_insertion_mode = True
            self.pending_text = text
            self._deactivate_other_modes(exclude='text_insert')
            logging.info("Text insertion mode enabled")
        else:
            self._cancel_text_insertion()

    def _on_clear_all_texts(self):
        """Remove all floating text items"""
        if not self.floating_text_items:
            QMessageBox.information(
                self, "No Texts",
                "There are no text boxes to clear."
            )
            return

        reply = QMessageBox.question(
            self, "Clear All Texts",
            f"Are you sure you want to remove all {len(self.floating_text_items)} text boxes?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for text_item in self.floating_text_items:
                self.main_plot.removeItem(text_item['item'])

            self.floating_text_items = []
            logging.info("Cleared all floating texts")
            QMessageBox.information(self, "Cleared", "All text boxes have been removed.")

    def _on_set_title(self):
        """Set the plot title from input"""
        title = self.title_input.text()
        self.current_title = title
        self.main_plot.setTitle(title)
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = title
        logging.info(f"Title set to: {title}")

    # ========================================================================
    # MODE MANAGEMENT
    # ========================================================================

    def _deactivate_other_modes(self, exclude=None):
        """Deactivate all modes except the specified one"""
        if exclude != 'highlighter':
            self.yaxis_approx_value_highlighter = False
            if self.highlighter_action:
                self.highlighter_action.setChecked(False)

        if exclude != 'text_insert':
            self.text_insertion_mode = False
            if self.insert_text_action:
                self.insert_text_action.setChecked(False)

    # ========================================================================
    # MOUSE EVENT HANDLERS
    # ========================================================================

    def _on_mouse_moved(self, pos):
        """Handle mouse movement for crosshair cursor"""
        if not self.show_cursor:
            return

        # Convert position to data coordinates
        mouse_point = self.main_plot.vb.mapSceneToView(pos)
        x, y = mouse_point.x(), mouse_point.y()

        # Update crosshair position
        self.crosshair_vline.setPos(x)
        self.crosshair_hline.setPos(y)

        # Build cursor label text
        xlabel = self.x_column if self.x_column else 'X'
        cursor_text = f"{xlabel}: {x:.2f}\n"

        for item in self.plot_items:
            if 'scatter' in item:
                x_data = item['x_data']
                y_data = item['y_data']

                if len(x_data) > 0:
                    idx = self._find_nearest_index(x_data, x)
                    nearest_y = y_data[idx]
                    cursor_text += f"{item['name']}: {nearest_y:.2f}\n"

        self.cursor_annotation.setPos(x, y)
        self.cursor_annotation.setText(cursor_text.strip())
        self.cursor_annotation.setVisible(True)

    def _on_mouse_click(self, event):
        """Handle mouse click events"""
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.scenePos()
            if self.main_plot.sceneBoundingRect().contains(pos):
                mouse_point = self.main_plot.vb.mapSceneToView(pos)
                x, y = mouse_point.x(), mouse_point.y()
                self._handle_left_click(x, y)
        elif event.button() == QtCore.Qt.RightButton:
            pos = event.scenePos()
            if self.main_plot.sceneBoundingRect().contains(pos):
                mouse_point = self.main_plot.vb.mapSceneToView(pos)
                x, y = mouse_point.x(), mouse_point.y()
                self._handle_right_click(x, y)

    def _handle_left_click(self, x, y):
        """Handle left mouse click based on active mode"""
        if self.text_insertion_mode:
            self._insert_floating_text_at(x, y)

    def _handle_right_click(self, x, y):
        """Handle right mouse click based on active mode"""
        if self.text_insertion_mode:
            self._cancel_text_insertion()
        elif self.yaxis_approx_value_highlighter:
            self._add_highlight(x)

    # ========================================================================
    # MULTI-AXIS PLOTTING FUNCTIONALITY
    # ========================================================================

    def plot_data(self, df, x_column, y_columns, smoothing_params, limit_lines=[], title=None):
        """Main plotting function - directly plots all selected Y columns with smoothing"""
        try:
            # Update title
            if title is not None:
                self.current_title = title
            else:
                title = self.current_title

            logging.info(f"Plotting data: x={x_column}, y={y_columns}, title={title}")

            # Store dataframe and column info
            self.current_df = df
            self.x_column = x_column
            self.available_columns = y_columns

            # Get X data
            self.x_data = df[x_column].values

            # Calculate default axis ranges for X
            x_min_default = float(np.min(self.x_data))
            x_max_default = float(np.max(self.x_data))
            x_padding = (x_max_default - x_min_default) * 0.1
            self.x_min_default = x_min_default - x_padding
            self.x_max_default = x_max_default + x_padding

            # Update X-axis range inputs
            self.x_min_input.setText(f"{self.x_min_default:.2f}")
            self.x_max_input.setText(f"{self.x_max_default:.2f}")

            # Clear previous plot
            self._clear_all_plot_items()

            # Set labels and title
            self.main_plot.setTitle(title)
            self.main_plot.setLabel('bottom', x_column)

            # Set initial X-axis range
            self.main_plot.setXRange(self.x_min_default, self.x_max_default, padding=0)

            # Store plot parameters
            self.last_plot_params = {
                'df': df,
                'x_column': x_column,
                'y_columns': y_columns,
                'smoothing_params': smoothing_params,
                'limit_lines': limit_lines,
                'title': title
            }

            # Plot all selected Y columns
            for y_column in y_columns:
                self._add_column_with_smoothing(y_column, smoothing_params)

            # Update legend
            if self.show_legend:
                self._populate_legend()

            logging.info(f"Successfully plotted {len(y_columns)} columns")

        except Exception as e:
            logging.error(f"Error in plot_data: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while plotting: {str(e)}")

    def _add_column_with_smoothing(self, column_name, smoothing_params):
        """Add a column to the plot with smoothing applied"""
        if self.current_df is None:
            logging.error("No data available to plot")
            return

        # Check if column is already plotted
        if column_name in [item['name'] for item in self.plot_items]:
            logging.warning(f"Column '{column_name}' already plotted, skipping")
            return

        # Get Y data from DataFrame
        y_data = self.current_df[column_name].values

        # Apply smoothing if enabled
        if smoothing_params and smoothing_params.get('apply', False):
            try:
                x_data = self.x_data
                y_data = apply_smoothing(x_data, y_data, smoothing_params)
                logging.info(f"Applied {smoothing_params.get('method', 'unknown')} smoothing to {column_name}")
            except Exception as e:
                logging.warning(f"Failed to apply smoothing to {column_name}: {str(e)}")
                # Continue with original data if smoothing fails

        # Get color for this column
        color_index = len(self.plot_items) % len(self.colors)
        color = self.colors[color_index]

        # Create a new ViewBox for this Y-axis
        if len(self.plot_items) == 0:
            # First plot uses the main plot's ViewBox
            view_box = self.main_plot.getViewBox()
            axis = self.main_plot.getAxis('left')
            axis.setLabel(column_name, color=color)
            axis.setPen(color)
            axis.setTextPen(color)
        else:
            # Additional plots get their own ViewBox and Y-axis
            view_box = pg.ViewBox()
            self.main_plot.scene().addItem(view_box)

            # Link X-axis to main plot
            view_box.setXLink(self.main_plot)

            # Create new Y-axis
            axis = pg.AxisItem('right')
            axis.linkToView(view_box)
            axis.setLabel(column_name, color=color)
            axis.setPen(color)
            axis.setTextPen(color)

            # Add axis to the plot layout
            self.plot_layout.addItem(axis, row=0, col=len(self.plot_items) + 1)

            # Update the view when the main plot changes
            self.main_plot.vb.sigResized.connect(self.update_views)
            view_box.setGeometry(self.main_plot.vb.sceneBoundingRect())

            # Store axis reference
            self.y_axes.append(axis)

        # Create scatter plot for this column
        scatter = pg.ScatterPlotItem(
            x=self.x_data,
            y=y_data,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(*color, 150),
            size=6,
            name=column_name
        )

        # Add to the appropriate ViewBox
        view_box.addItem(scatter)

        # Auto-range for this Y-axis
        view_box.enableAutoRange(axis=pg.ViewBox.YAxis)

        # Store plot item info
        self.plot_items.append({
            'name': column_name,
            'scatter': scatter,
            'viewbox': view_box,
            'axis': axis,
            'color': color,
            'x_data': self.x_data,
            'y_data': y_data
        })
        self.axis_colors.append(color)

        logging.info(f"Added column: {column_name} with color {color}")

    def _remove_last_plot_item(self):
        """Remove the last added column (internal method)"""
        if len(self.plot_items) == 0:
            return

        # Get last item
        last_item = self.plot_items.pop()

        # Remove scatter plot
        last_item['viewbox'].removeItem(last_item['scatter'])

        # Remove axis and viewbox if not the first one
        if len(self.plot_items) > 0:  # If this wasn't the first plot
            self.plot_layout.removeItem(last_item['axis'])
            self.main_plot.scene().removeItem(last_item['viewbox'])
            if last_item['axis'] in self.y_axes:
                self.y_axes.remove(last_item['axis'])
        else:
            # If removing the first/only plot, clear the label
            self.main_plot.getAxis('left').setLabel('')

        self.axis_colors.pop()
        logging.info(f"Removed column: {last_item['name']}")

    def _clear_all_plot_items(self):
        """Clear all plotted columns (internal method)"""
        while len(self.plot_items) > 0:
            self._remove_last_plot_item()

        logging.info("Cleared all plot items")

    def update_views(self):
        """Update all ViewBox geometries to match the main plot"""
        for item in self.plot_items[1:]:  # Skip first one (uses main ViewBox)
            item['viewbox'].setGeometry(self.main_plot.vb.sceneBoundingRect())


    def update_x_axis_range(self):
        """Update the X-axis range based on input values"""
        try:
            x_min = float(self.x_min_input.text())
            x_max = float(self.x_max_input.text())

            # Validate range
            if x_min >= x_max:
                QMessageBox.warning(self, "Invalid Range",
                                   "X-axis minimum must be less than maximum!")
                return

            # Set the X-axis range
            self.main_plot.setXRange(x_min, x_max, padding=0)

        except ValueError:
            QMessageBox.warning(self, "Invalid Input",
                               "Please enter valid numeric values!")

    def reset_x_axis_range(self):
        """Reset X-axis range to default values"""
        if hasattr(self, 'x_min_default') and hasattr(self, 'x_max_default'):
            self.x_min_input.setText(f"{self.x_min_default:.2f}")
            self.x_max_input.setText(f"{self.x_max_default:.2f}")
            self.update_x_axis_range()

    # ========================================================================
    # LEGEND MANAGEMENT
    # ========================================================================

    def _clear_legend(self):
        """Clear all legend items"""
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.legend_items = []

    def _populate_legend(self):
        """Populate custom legend with colored items"""
        self._clear_legend()

        self.legend_layout.addStretch()

        for item in self.plot_items:
            color = item['color']
            # Convert tuple to hex
            color_hex = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            self._add_legend_item(item['name'], color_hex)

        self.legend_layout.addStretch()
        logging.info(f"Legend populated with {len(self.legend_items)} items")

    def _add_legend_item(self, label, color_hex):
        """Add a single item to the legend"""
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(5)

        # Color indicator
        color_label = QLabel()
        color_label.setFixedSize(30, 3)
        color_label.setStyleSheet(f"background-color: {color_hex}; border: none;")
        item_layout.addWidget(color_label)

        # Text label
        text_label = QLabel(label)
        text_label.setStyleSheet("font-size: 10pt; color: black;")
        item_layout.addWidget(text_label)

        self.legend_layout.addWidget(item_widget)
        self.legend_items.append(item_widget)

    # ========================================================================
    # HIGHLIGHT FUNCTIONALITY
    # ========================================================================

    def _add_highlight(self, x):
        """Add vertical line and highlight points at x position"""
        xlabel = self.x_column if self.x_column else 'X'
        highlight_items = []

        for item in self.plot_items:
            x_data = item['x_data']
            y_data = item['y_data']

            if len(x_data) == 0:
                continue

            # Find nearest point
            idx = self._find_nearest_index(x_data, x)
            nearest_x = x_data[idx]
            nearest_y = y_data[idx]

            viewbox = item['viewbox']
            color = item['color']

            # Create vertical line
            vline = pg.InfiniteLine(pos=nearest_x, angle=90, pen=pg.mkPen('gray', style=QtCore.Qt.DashLine, width=2))
            viewbox.addItem(vline)
            highlight_items.append(vline)

            # Create highlight point
            scatter = pg.ScatterPlotItem(
                x=[nearest_x],
                y=[nearest_y],
                pen=pg.mkPen('r', width=2),
                brush=pg.mkBrush('r'),
                size=12
            )
            viewbox.addItem(scatter)
            highlight_items.append(scatter)

            # Create text annotation
            text = pg.TextItem(
                f"{xlabel}: {nearest_x:.2f}\n{item['name']}: {nearest_y:.2f}",
                anchor=(0, 1),
                color='k'
            )
            text.setPos(nearest_x, nearest_y)
            viewbox.addItem(text)
            highlight_items.append(text)

        self.vertical_lines.append((x, highlight_items))
        logging.info(f"Added highlight at x={x:.2f}")

    # ========================================================================
    # TEXT INSERTION/REMOVAL FUNCTIONALITY
    # ========================================================================

    def _insert_floating_text_at(self, x, y):
        """Insert floating text box at position"""
        try:
            text_item = pg.TextItem(
                self.pending_text,
                anchor=(0.5, 0.5),
                color='k',
                border=pg.mkPen('k', width=2),
                fill=pg.mkBrush(255, 255, 0, 230)
            )
            text_item.setPos(x, y)
            self.main_plot.addItem(text_item)

            self.floating_text_items.append({
                'item': text_item,
                'text': self.pending_text,
                'position': (x, y)
            })

            logging.info(f"Inserted floating text at ({x:.2f}, {y:.2f}): {self.pending_text}")

            # Exit insertion mode
            self.text_insertion_mode = False
            self.pending_text = ""
            self.insert_text_action.setChecked(False)

        except Exception as e:
            logging.error(f"Error inserting floating text: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to insert text: {str(e)}")

    def _cancel_text_insertion(self):
        """Cancel text insertion mode"""
        self.text_insertion_mode = False
        self.pending_text = ""
        self.insert_text_action.setChecked(False)
        logging.info("Text insertion mode cancelled")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _find_nearest_index(self, x_data, x_value):
        """Find nearest index using binary search"""
        if len(x_data) == 0:
            return 0

        idx = np.searchsorted(x_data, x_value)
        idx = np.clip(idx, 0, len(x_data) - 1)

        if idx > 0:
            if abs(x_data[idx - 1] - x_value) < abs(x_data[idx] - x_value):
                idx = idx - 1

        return idx

    def _get_comment_box(self):
        """Get reference to comment box from main window"""
        main_window = self.window()

        if hasattr(main_window, 'comment_box'):
            return main_window.comment_box
        elif hasattr(main_window, 'right_panel') and hasattr(main_window.right_panel, 'comment_box'):
            return main_window.right_panel.comment_box
        elif hasattr(main_window, 'left_panel') and hasattr(main_window.left_panel, 'comment_box'):
            return main_window.left_panel.comment_box
        else:
            for child in main_window.findChildren(QGroupBox):
                if child.title() == "Comments":
                    return child
        return None

    # ========================================================================
    # PUBLIC API METHODS (for compatibility with existing code)
    # ========================================================================

    def clear_plot(self):
        """Clear the entire plot"""
        logging.info("Clearing plot")

        # Clear all columns
        self._clear_all_plot_items()

        # Clear floating texts
        for text_item in self.floating_text_items:
            self.main_plot.removeItem(text_item['item'])
        self.floating_text_items = []

        # Clear highlights
        for _, highlight_items in self.vertical_lines:
            for item in highlight_items:
                if hasattr(item, 'scene') and item.scene() is not None:
                    item.scene().removeItem(item)
        self.vertical_lines = []

        # Reset state
        self.current_df = None
        self.x_column = None
        self.available_columns = []
        self.original_x_range = None

        if hasattr(self, 'last_plot_params'):
            delattr(self, 'last_plot_params')

        self._clear_legend()

        self.main_plot.setTitle("No data to display")
        self.main_plot.setLabel('bottom', "X-axis")
        self.main_plot.setLabel('left', "Y-axis")
        self.reset_title()

        logging.info("Plot cleared successfully")

    def reset_title(self):
        """Reset the title"""
        self.current_title = ""
        self.title_input.clear()
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = ""
        self.main_plot.setTitle("")

    def set_default_title(self, title):
        """Set default title in input field and apply it"""
        self.title_input.setText(title)
        self.current_title = title
        self.main_plot.setTitle(title)
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = title

    def update_plot(self):
        """Update plot with last parameters"""
        if hasattr(self, 'last_plot_params'):
            self.plot_data(**self.last_plot_params)

    # Compatibility methods for curve fitting (not implemented for scatter plots)
    def apply_curve_fitting(self, x_data, y_data, fit_func, equation, fit_type, x_label, y_label):
        """Apply curve fitting - not implemented for scatter plots"""
        QMessageBox.information(self, "Not Available",
                               "Curve fitting is not available for multi-axis scatter plots.")

    def remove_curve_fitting(self, y_label=None):
        """Remove curve fitting - not implemented for scatter plots"""
        pass

    # Compatibility aliases
    def toggle_cursor(self, state):
        """Toggle cursor - alias for _on_toggle_cursor"""
        self._on_toggle_cursor(state)

    def toggle_legend(self, state):
        """Toggle legend - alias for _on_toggle_legend"""
        self._on_toggle_legend(state)

    def toggle_highlighter(self, state):
        """Toggle highlighter - alias for _on_toggle_highlighter"""
        self._on_toggle_highlighter(state)

    def clear_custom_legend(self):
        """Clear custom legend - alias for _clear_legend"""
        self._clear_legend()

    def populate_custom_legend(self, y_columns, colors, has_smoothing):
        """Populate custom legend - compatibility method"""
        self._populate_legend()

    def set_title(self):
        """Set title - alias for _on_set_title"""
        self._on_set_title()

    def clear_all_floating_texts(self):
        """Clear all floating texts - alias for _on_clear_all_texts"""
        self._on_clear_all_texts()

    # Deprecated methods (for compatibility)
    def toggle_zoom_region_mode(self, state):
        """Zoom region mode - not implemented for PyQtGraph version"""
        pass

    def toggle_text_insertion_mode(self, checked):
        """Toggle text insertion mode - alias"""
        self._on_toggle_text_insertion(checked)

    def toggle_text_removal_mode(self, checked):
        """Text removal mode - not implemented for PyQtGraph version"""
        pass

    def clear_zoom_region(self):
        """Clear zoom region - not implemented for PyQtGraph version"""
        pass

    def toggle_original_data(self):
        """Toggle original data - not applicable for scatter plots"""
        pass

    def get_show_original_state(self):
        """Get show original state - always True"""
        return True

    def set_show_original_state(self, state):
        """Set show original state - deprecated"""
        pass

    def enable_insertion(self, text):
        """Enable text insertion mode with given text"""
        self.text_insertion_mode = True
        self.pending_text = text
        self.insert_text_action.setChecked(True)

        QMessageBox.information(
            self, "Text Insertion Mode",
            "Click anywhere on the plot to place the text.\nRight-click to cancel."
        )
