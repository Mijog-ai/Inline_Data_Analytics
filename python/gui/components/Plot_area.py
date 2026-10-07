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
    QShortcut, QInputDialog, QMenu
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QPixmap, QKeySequence

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

from utils.asc_utils import apply_smoothing


class EditableTextItem(pg.TextItem):
    """Custom TextItem that supports editing and deletion via context menu"""

    def __init__(self, text='', parent_plot_area=None, **kwargs):
        super().__init__(text, **kwargs)
        self.parent_plot_area = parent_plot_area
        self.text_data = None  # Reference to the text data dict

    def mouseDoubleClickEvent(self, event):
        """Handle double-click to edit text"""
        if self.parent_plot_area:
            self.parent_plot_area._edit_text_item(self)
        event.accept()

    def mousePressEvent(self, event):
        """Handle right-click to remove text directly"""
        if event.button() == QtCore.Qt.RightButton:
            if self.parent_plot_area:
                self.parent_plot_area._remove_text_item(self)
            event.accept()
        else:
            # Call parent implementation for other buttons (like left-click for dragging)
            super().mousePressEvent(event)


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

        def _init_state_variables(self):
            """Initialize all state tracking variables"""
        # Display modes
        self.show_cursor = False
        self.show_legend = True
        self.yaxis_approx_value_highlighter = False
        self.zoom_mode_active = False
        self.text_insertion_mode = False
        self.text_removal_mode = False

        # Click handling
        self.click_timer = None
        self.pending_click = None
        self.double_click_interval = 300  # milliseconds

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

            (79, 121, 66),   # Green
            (100, 100, 255),   # Blue
            (255, 150, 100),  # Orange
            (255, 255, 100),   # Yellow
            (255, 100, 255),   # Magenta
            (100, 255, 255),   # Cyan

            (150, 100, 255),   # Purple
            (255, 200, 100),   # Light Orange
            (100, 255, 200),   # Aqua
        ]
        # Undo/Redo

        # Undo/Redo functionality
        self.history_stack = []  # Stack of previous states
        self.redo_stack = []  # Stack for redo operations
        self.max_history = 50  # Maximum number of undo steps


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

        # Add keyboard shortcuts
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.undo_last_action)

        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.redo_shortcut.activated.connect(self.redo_last_action)

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
            "Enable highlight mode - left click to add, double-click to remove highlights",  # Updated
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

        self.toolbar.addSeparator()
        #Undo action
        self.undo_action = self._create_action(
            "Undo",
            "Undo last action (Ctrl+Z)",
            checkable= False,
            callback = self.undo_last_action
        )
        self.undo_action.setEnabled(False)  # Disabled initially
        self.toolbar.addAction(self.undo_action)

        #Redo action
        self.redo_action = self._create_action(
            "Redo",
            "Redo last action (Ctrl + Y)",
            checkable = False,
            callback = self.redo_last_action
        )

        self.redo_action.setEnabled(False)  # Disabled initially
        self.toolbar.addAction(self.redo_action)
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
        self.main_plot.setMouseEnabled(x=False, y=False)

        # Connect mouse events
        # Connect mouse events
        self.main_plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self.main_plot.scene().sigMouseClicked.connect(self._on_mouse_click)


        # # Create crosshair (initially hidden)
        # self.crosshair_vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('k', style=QtCore.Qt.DashLine))
        # self.crosshair_hline = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('k', style=QtCore.Qt.DashLine))
        # self.crosshair_vline.setVisible(False)
        # self.crosshair_hline.setVisible(False)
        # self.main_plot.addItem(self.crosshair_vline)
        # self.main_plot.addItem(self.crosshair_hline)

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

            self._save_state()

            self.floating_text_items = []
            logging.info("Cleared all floating texts")
            QMessageBox.information(self, "Cleared", "All text boxes have been removed.")

    def _on_set_title(self):
        """Set the plot title from input"""
        self._save_state()
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
        if self.crosshair_vline:
            self.crosshair_vline.setPos(x)
        if self.crosshair_hline:
            self.crosshair_hline.setPos(y)

        # Build cursor label text
        xlabel = self.x_column if self.x_column else 'X'
        cursor_text = f"{xlabel}: {x:.2f}\n"

        for item in self.plot_items:
            if 'plot_line' in item:
                x_data = item['x_data']
                y_data = item['y_data']

                if len(x_data) > 0:
                    idx = self._find_nearest_index(x_data, x)
                    nearest_y = y_data[idx]
                    cursor_text += f"{item['name']}: {nearest_y:.2f}\n"

        self.cursor_annotation.setPos(x, y)
        self.cursor_annotation.setText(cursor_text.strip())
        self.cursor_annotation.setVisible(True)

    def _process_single_click(self):
        """Process a confirmed single click after timer expires"""
        if self.pending_click:
            x, y = self.pending_click
            print(f"Processing single click at x={x}, y={y}")
            self._handle_left_click(x, y)
            self.pending_click = None
        self.click_timer = None

    def _on_mouse_click(self, event):
        """Handle mouse click events with double-click detection"""
        print(f"MOUSE CLICK: Button={event.button()}, Double={event.double()}")

        if event.button() == QtCore.Qt.LeftButton:
            if event.double():
                # Double click detected
                print("LEFT DOUBLE CLICK")
                if self.click_timer:
                    self.click_timer.stop()
                    self.click_timer = None
                    self.pending_click = None

                pos = event.scenePos()
                if self.main_plot.sceneBoundingRect().contains(pos):
                    mouse_point = self.main_plot.vb.mapSceneToView(pos)
                    x, y = mouse_point.x(), mouse_point.y()
                    self._handle_left_double_click(x, y)
            else:
                # Single click - delay to see if double-click follows
                print("LEFT CLICK (pending)")
                pos = event.scenePos()
                if self.main_plot.sceneBoundingRect().contains(pos):
                    mouse_point = self.main_plot.vb.mapSceneToView(pos)
                    x, y = mouse_point.x(), mouse_point.y()

                    # Cancel any existing timer
                    if self.click_timer:
                        self.click_timer.stop()

                    # Store click and start timer
                    self.pending_click = (x, y)
                    self.click_timer = QTimer()
                    self.click_timer.setSingleShot(True)
                    self.click_timer.timeout.connect(self._process_single_click)
                    self.click_timer.start(self.double_click_interval)

        elif event.button() == QtCore.Qt.RightButton:
            print("RIGHT CLICK")
            pos = event.scenePos()
            if self.main_plot.sceneBoundingRect().contains(pos):
                mouse_point = self.main_plot.vb.mapSceneToView(pos)
                x, y = mouse_point.x(), mouse_point.y()
                self._handle_right_click(x, y)




    def _handle_left_click(self, x, y):
        """Handle left mouse click based on active mode"""
        if self.text_insertion_mode:
            self._insert_floating_text_at(x, y)
        elif self.yaxis_approx_value_highlighter:
            print("Adding highlight via left click...")
            self._add_highlight(x)

    def _handle_left_double_click(self, x, y):
        """Handle left double-click to remove nearest highlight"""
        if self.yaxis_approx_value_highlighter:
            print(f"Attempting to remove highlight near x={x}")
            self._remove_nearest_highlight(x)

    def _on_toggle_highlighter(self, state):
        """Toggle highlight mode"""
        self.yaxis_approx_value_highlighter = bool(state)
        print(f"HIGHLIGHTER TOGGLED: {self.yaxis_approx_value_highlighter}")

        if state:
            self._deactivate_other_modes(exclude='highlighter')

        logging.info(f"Highlight mode: {state}")

    def _remove_nearest_highlight(self, x):
        """Remove the highlight closest to the given x position"""
        self._save_state()
        if not self.vertical_lines:
            QMessageBox.information(
                self, "No Highlights",
                "There are no highlights to remove."
            )
            return

        # Find nearest highlight
        min_distance = float('inf')
        nearest_idx = None

        for idx, (highlight_x, _) in enumerate(self.vertical_lines):
            distance = abs(highlight_x - x)
            if distance < min_distance:
                min_distance = distance
                nearest_idx = idx

        if nearest_idx is not None:
            # Get the highlight items
            highlight_x, highlight_items = self.vertical_lines[nearest_idx]

            # Remove all items
            for item in highlight_items:
                try:
                    # Remove from main plot
                    if item in self.main_plot.items:
                        self.main_plot.removeItem(item)
                    else:
                        # Try to find which viewbox contains it
                        for plot_item in self.plot_items:
                            if hasattr(plot_item['viewbox'], 'addedItems') and item in plot_item['viewbox'].addedItems:
                                plot_item['viewbox'].removeItem(item)
                                break
                except Exception as e:
                    logging.warning(f"Could not remove highlight item: {str(e)}")

            # Remove from list
            self.vertical_lines.pop(nearest_idx)
            logging.info(f"Removed highlight at x={highlight_x:.2f}")
            print(f"Removed highlight at x={highlight_x:.2f}")

    def _handle_right_click(self, x, y):
        """Handle right mouse click based on active mode"""
        print(f"RIGHT CLICK DETECTED at x={x}, y={y}")
        print(f"Text insertion mode: {self.text_insertion_mode}")
        print(f"Highlighter mode: {self.yaxis_approx_value_highlighter}")

        if self.text_insertion_mode:
            self._cancel_text_insertion()

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
            # Check if data is valid before calculating min/max
            if len(self.x_data) == 0 or np.all(np.isnan(self.x_data)):
                logging.error(f"No valid data in column '{x_column}'")
                QMessageBox.critical(
                    self, "Error",
                    f"No valid data found in column '{x_column}'. Please check your data file."
                )
                return

            # Filter out NaN values for min/max calculation
            valid_x_data = self.x_data[~np.isnan(self.x_data)]
            if len(valid_x_data) == 0:
                logging.error(f"All data in column '{x_column}' is NaN")
                QMessageBox.critical(
                    self, "Error",
                    f"All data in column '{x_column}' contains invalid (NaN) values. Please check your data file."
                )
                return

            x_min_default = float(np.min(valid_x_data))
            x_max_default = float(np.max(valid_x_data))

            # Additional check: ensure min and max are valid numbers
            if np.isnan(x_min_default) or np.isnan(x_max_default) or np.isinf(x_min_default) or np.isinf(x_max_default):
                logging.error(f"Invalid range calculated for column '{x_column}': [{x_min_default}, {x_max_default}]")
                QMessageBox.critical(
                    self, "Error",
                    f"Could not calculate valid range for column '{x_column}'. Please check your data file."
                )
                return

            self.x_min_default = x_min_default
            self.x_max_default = x_max_default

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
        y_data_original = self.current_df[column_name].values
        y_data = y_data_original.copy()

        # Validate Y data
        if len(y_data) == 0:
            logging.warning(f"No data in column '{column_name}', skipping")
            QMessageBox.warning(
                self, "Warning",
                f"Column '{column_name}' contains no data and will be skipped."
            )
            return

        # Check if all values are NaN
        if np.all(np.isnan(y_data)):
            logging.warning(f"All data in column '{column_name}' is NaN, skipping")
            QMessageBox.warning(
                self, "Warning",
                f"Column '{column_name}' contains only invalid (NaN) values and will be skipped."
            )
            return

        # Track if smoothing was applied
        smoothing_applied = False

        # Apply smoothing if enabled
        if smoothing_params and smoothing_params.get('apply', False):
            try:
                y_data = apply_smoothing(
                    y_data,
                    method=smoothing_params.get('method', 'savgol'),
                    window_length=smoothing_params.get('window_length', 21),
                    poly_order=smoothing_params.get('poly_order', 3),
                    sigma=smoothing_params.get('sigma', 2)
                )
                smoothing_applied = True
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

        # Create original data line plot (background) if smoothing was applied
        plot_original = None
        if smoothing_applied:
            # Light color for original data (20% opacity = 51/255)
            light_color = (*color, 51)
            plot_original = pg.PlotDataItem(
                x=self.x_data,
                y=y_data_original,
                pen=pg.mkPen(light_color, width=1.5),
                name=f"{column_name} (Original)"
            )
            view_box.addItem(plot_original)

        # Create smoothed/main line plot (foreground)
        # Dark, fully opaque color for smoothed data
        dark_color = (*color, 255)
        plot_line = pg.PlotDataItem(
            x=self.x_data,
            y=y_data,
            pen=pg.mkPen(dark_color, width=3),  # Thicker and fully opaque
            name=column_name
        )

        # Add to the appropriate ViewBox
        view_box.addItem(plot_line)

        # Auto-range for this Y-axis
        view_box.enableAutoRange(axis=pg.ViewBox.YAxis)

        # Store plot item info
        self.plot_items.append({
            'name': column_name,
            'plot_line': plot_line,
            'plot_original': plot_original,  # Store original line plot
            'viewbox': view_box,
            'axis': axis,
            'color': color,
            'x_data': self.x_data,
            'y_data': y_data,
            'y_data_original': y_data_original,  # Store original y data
            'smoothing_applied': smoothing_applied
        })
        self.axis_colors.append(color)

        logging.info(f"Added column: {column_name} with color {color}" +
                     (" (with smoothing)" if smoothing_applied else ""))

    def _remove_last_plot_item(self):
        """Remove the last added column (internal method)"""
        if len(self.plot_items) == 0:
            return

        # Get last item
        last_item = self.plot_items.pop()

        # Remove line plot
        last_item['viewbox'].removeItem(last_item['plot_line'])

        # Remove original line plot if it exists
        if last_item.get('plot_original'):
            last_item['viewbox'].removeItem(last_item['plot_original'])

        # Check if this is a curve fit (which reuses parent's axis/viewbox)
        is_curve_fit = last_item.get('is_curve_fit', False)

        if not is_curve_fit:
            # Only remove axis/viewbox if this plot owns them (not a curve fit)
            if last_item['axis'] in self.y_axes:
                # This is a secondary axis that was added to the layout
                self.plot_layout.removeItem(last_item['axis'])
                self.main_plot.scene().removeItem(last_item['viewbox'])
                self.y_axes.remove(last_item['axis'])
            elif len(self.plot_items) == 0:
                # If removing the last plot using the main axis, clear the label
                self.main_plot.getAxis('left').setLabel('')

            # Only pop axis_colors for non-curve-fit items
            if self.axis_colors:
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
        self._save_state()
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
        """Add vertical line and create a legend box showing all axis values at x position"""
        self._save_state()
        global nearest_y, nearest_x
        try:
            if not self.plot_items or len(self.plot_items) == 0:
                QMessageBox.warning(self, "No Data", "No plot data available.")
                return

            xlabel = self.x_column if self.x_column else 'X'
            all_highlight_items = []

            # Build legend text with all values
            legend_text = f"{xlabel}: {x:.2f}\n" + "-" * 30 + "\n"

            for item in self.plot_items:
                x_data = item['x_data']
                y_data = item['y_data']

                if len(x_data) == 0:
                    continue

                # Find nearest point
                idx = self._find_nearest_index(x_data, x)
                nearest_x = x_data[idx]
                nearest_y = y_data[idx]

                # Add to legend text
                legend_text += f"{item['name']}: {nearest_y:.2f}\n"

                viewbox = item['viewbox']

                # Create highlight point at intersection
                highlight_scatter = pg.ScatterPlotItem(
                    x=[nearest_x],
                    y=[nearest_y],
                    pen=pg.mkPen('r', width=2),
                    brush=pg.mkBrush('r'),
                    size=12
                )
                viewbox.addItem(highlight_scatter)
                all_highlight_items.append(highlight_scatter)

                # Get the x-axis range for this viewbox to find the left edge
                view_range = viewbox.viewRange()
                x_left = view_range[0][0]  # Left edge of x-axis

                # Add horizontal line from left edge to the data point
                hline = pg.PlotCurveItem(
                    x=[x_left, nearest_x],
                    y=[nearest_y, nearest_y],
                    pen=pg.mkPen('gray', style=QtCore.Qt.DashLine, width=1)
                )
                viewbox.addItem(hline)
                all_highlight_items.append(hline)

            # Create single vertical line on main plot that extends full height
            vline = pg.InfiniteLine(
                pos=nearest_x,
                angle=90,  # vertical line
                pen=pg.mkPen('gray', style=QtCore.Qt.DashLine, width=2)
            )

            self.main_plot.addItem(vline)
            all_highlight_items.append(vline)

            # Create legend box with all values
            legend_box = pg.TextItem(
                legend_text.strip(),
                anchor=(0, 0),
                color='k',
                border=pg.mkPen('k', width=2),
                fill=pg.mkBrush(255, 255, 255, 230)
            )

            # Make the legend box draggable
            legend_box.setFlag(legend_box.GraphicsItemFlag.ItemIsMovable)
            legend_box.setFlag(legend_box.GraphicsItemFlag.ItemSendsGeometryChanges)

            # Position legend box near the clicked point
            view_range = self.main_plot.viewRange()
            x_range = view_range[0][1] - view_range[0][0]
            y_range = view_range[1][1] - view_range[1][0]

            # Position slightly to the right and above the clicked point
            x_offset = x_range * 0.02  # 2% of range to the right
            y_offset = y_range * 0.05  # 5% of range above

            # Make sure it stays within bounds
            x_pos = min(nearest_x + x_offset, view_range[0][1] - x_range * 0.15)
            y_pos = min(view_range[1][1] - y_range * 0.02, view_range[1][1])

            # If too far right, move to left of the line instead
            if x_pos + x_range * 0.12 > view_range[0][1]:
                x_pos = nearest_x - x_offset - x_range * 0.10

            legend_box.setPos(x_pos, y_pos)
            self.main_plot.addItem(legend_box)
            all_highlight_items.append(legend_box)

            # Store all highlight items
            self.vertical_lines.append((nearest_x, all_highlight_items))
            logging.info(f"Added highlight at x={nearest_x:.2f}")

        except Exception as e:
            logging.error(f"Error adding highlight: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Failed to add highlight: {str(e)}")

    def _find_nearest_index(self, x_data, x_value):
        """Find nearest index using binary search"""
        self._save_state()
        if len(x_data) == 0:
            return 0

        idx = np.searchsorted(x_data, x_value)
        idx = np.clip(idx, 0, len(x_data) - 1)

        if idx > 0:
            if abs(x_data[idx - 1] - x_value) < abs(x_data[idx] - x_value):
                idx = idx - 1

        return idx



    # ========================================================================
    # TEXT INSERTION/REMOVAL FUNCTIONALITY
    # ========================================================================

    def _insert_floating_text_at(self, x, y):
        """Insert floating text box at position"""
        self._save_state()
        try:
            text_item = EditableTextItem(
                self.pending_text,
                parent_plot_area=self,
                anchor=(0.5, 0.5),
                color='k',
                border=pg.mkPen('k', width=2),
                fill=pg.mkBrush(255, 255, 0, 230)
            )
            text_item.setPos(x, y)

            # Make the text item draggable
            text_item.setFlag(text_item.GraphicsItemFlag.ItemIsMovable, True)
            text_item.setFlag(text_item.GraphicsItemFlag.ItemSendsGeometryChanges, True)
            text_item.setFlag(text_item.GraphicsItemFlag.ItemIsSelectable, True)

            self.main_plot.addItem(text_item)

            # Store reference with the text item
            text_data = {
                'item': text_item,
                'text': self.pending_text,
                'position': (x, y)
            }
            self.floating_text_items.append(text_data)

            # Link text_item to its data for editing/removal
            text_item.text_data = text_data

            # Create a custom itemChange handler to track position changes
            original_itemChange = text_item.itemChange

            def custom_itemChange(change, value):
                if change == text_item.GraphicsItemChange.ItemPositionHasChanged:
                    # Update stored position when item is moved
                    new_pos = text_item.pos()
                    text_data['position'] = (new_pos.x(), new_pos.y())
                    logging.debug(f"Text moved to ({new_pos.x():.2f}, {new_pos.y():.2f})")
                return original_itemChange(change, value)

            text_item.itemChange = custom_itemChange

            logging.info(f"Inserted draggable floating text at ({x:.2f}, {y:.2f}): {self.pending_text}")

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

    def _edit_text_item(self, text_item):
        """Edit an existing text item"""
        try:
            current_text = text_item.toPlainText()
            new_text, ok = QInputDialog.getText(
                self,
                "Edit Text",
                "Enter new text:",
                QLineEdit.Normal,
                current_text
            )

            if ok and new_text:
                self._save_state()
                text_item.setText(new_text)
                # Update the stored text in text_data
                if text_item.text_data:
                    text_item.text_data['text'] = new_text
                logging.info(f"Edited text from '{current_text}' to '{new_text}'")

        except Exception as e:
            logging.error(f"Error editing text item: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to edit text: {str(e)}")

    def _remove_text_item(self, text_item):
        """Remove a specific text item"""
        try:
            self._save_state()

            # Remove from plot
            self.main_plot.removeItem(text_item)

            # Remove from floating_text_items list
            if text_item.text_data in self.floating_text_items:
                self.floating_text_items.remove(text_item.text_data)

            logging.info(f"Removed text item: {text_item.toPlainText()}")

        except Exception as e:
            logging.error(f"Error removing text item: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove text: {str(e)}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    # def _find_nearest_index(self, x_data, x_value):
    #     """Find nearest index using binary search"""
    #     if len(x_data) == 0:
    #         return 0
    #
    #     idx = np.searchsorted(x_data, x_value)
    #     idx = np.clip(idx, 0, len(x_data) - 1)
    #
    #     if idx > 0:
    #         if abs(x_data[idx - 1] - x_value) < abs(x_data[idx] - x_value):
    #             idx = idx - 1
    #
    #     return idx

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

    # Curve fitting methods
    def apply_curve_fitting(self, x_data, y_data, fit_func, equation, fit_type, x_label, y_label):
        """Apply curve fitting to the plot"""
        try:
            # Generate fitted data points
            x_fit = np.linspace(np.min(x_data), np.max(x_data), 500)
            y_fit = fit_func(x_fit)

            # Find the plot item for the y_label
            target_item = None
            for item in self.plot_items:
                if item['name'] == y_label:
                    target_item = item
                    break

            if target_item is None:
                logging.warning(f"Could not find plot item for {y_label}")
                return

            # Create curve fit line
            fit_color = (255, 0, 0)  # Red color for fit line
            fit_line = pg.PlotDataItem(
                x=x_fit,
                y=y_fit,
                pen=pg.mkPen((*fit_color, 200), width=2, style=QtCore.Qt.DashLine),
                name=f"{y_label} - {fit_type} Fit"
            )

            # Add to the same ViewBox as the original data
            target_item['viewbox'].addItem(fit_line)

            # Store the fit line reference in the original plot item
            target_item['fit_line'] = fit_line
            target_item['fit_equation'] = equation

            # Create a new plot item for the fitted curve and add to plot_items
            fit_plot_item = {
                'name': f"{y_label} - {fit_type} Fit",
                'plot_line': fit_line,
                'plot_original': None,
                'viewbox': target_item['viewbox'],
                'axis': target_item['axis'],
                'color': fit_color,
                'x_data': x_fit,
                'y_data': y_fit,
                'y_data_original': y_fit,
                'smoothing_applied': False,
                'is_curve_fit': True,
                'parent_column': y_label
            }
            self.plot_items.append(fit_plot_item)

            # Update legend to include the fitted curve
            if self.show_legend:
                self._populate_legend()

            logging.info(f"Applied {fit_type} curve fitting to {y_label}: {equation}")

        except Exception as e:
            logging.error(f"Error applying curve fitting: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to apply curve fitting: {str(e)}")

    def remove_curve_fitting(self, y_label=None):
        """Remove curve fitting from specified plot or all plots"""
        try:
            if y_label:
                # Remove fit from specific plot
                for item in self.plot_items[:]:
                    if item['name'] == y_label and 'fit_line' in item:
                        item['viewbox'].removeItem(item['fit_line'])
                        del item['fit_line']
                        del item['fit_equation']
                        logging.info(f"Removed curve fit from {y_label}")

                    # Remove the curve fit plot item from plot_items
                    if item.get('is_curve_fit') and item.get('parent_column') == y_label:
                        item['viewbox'].removeItem(item['plot_line'])
                        self.plot_items.remove(item)
            else:
                # Remove all curve fits
                items_to_remove = []
                for item in self.plot_items:
                    if 'fit_line' in item:
                        item['viewbox'].removeItem(item['fit_line'])
                        del item['fit_line']
                        del item['fit_equation']

                    # Collect curve fit plot items to remove
                    if item.get('is_curve_fit'):
                        item['viewbox'].removeItem(item['plot_line'])
                        items_to_remove.append(item)

                # Remove collected items
                for item in items_to_remove:
                    self.plot_items.remove(item)

                logging.info("Removed all curve fits")

            # Update legend after removing curve fits
            if self.show_legend:
                self._populate_legend()

        except Exception as e:
            logging.error(f"Error removing curve fitting: {str(e)}")

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

    def export_plot(self, file_name, include_legend=True):
        """
        Export the complete plot with all axes, annotations, and legend
        """
        from PyQt5.QtWidgets import QApplication

        try:
            # Temporarily hide cursor if active
            cursor_was_visible = False
            if self.show_cursor and self.cursor_annotation:
                cursor_was_visible = True
                self.cursor_annotation.setVisible(False)
                if self.crosshair_vline:
                    self.crosshair_vline.setVisible(False)
                if self.crosshair_hline:
                    self.crosshair_hline.setVisible(False)

            # Force update
            QApplication.processEvents()

            # Grab the graphics view
            pixmap = self.graphics_view.grab()

            # If legend is visible and should be included, grab both
            if include_legend and self.legend_widget.isVisible():
                legend_pixmap = self.legend_widget.grab()

                # Combine plot and legend
                from PyQt5.QtGui import QPainter
                from PyQt5.QtCore import Qt

                total_height = pixmap.height() + legend_pixmap.height()
                combined_pixmap = QPixmap(pixmap.width(), total_height)
                combined_pixmap.fill(Qt.white)

                painter = QPainter(combined_pixmap)
                painter.drawPixmap(0, 0, pixmap)
                painter.drawPixmap(0, pixmap.height(), legend_pixmap)
                painter.end()

                combined_pixmap.save(file_name, 'PNG')
            else:
                pixmap.save(file_name, 'PNG')

            # Restore cursor visibility
            if cursor_was_visible:
                self.cursor_annotation.setVisible(True)
                if self.crosshair_vline:
                    self.crosshair_vline.setVisible(True)
                if self.crosshair_hline:
                    self.crosshair_hline.setVisible(True)

            logging.info(f"Plot successfully exported to: {file_name}")
            return True

        except Exception as e:
            logging.error(f"Error in export_plot: {str(e)}")
            logging.error(traceback.format_exc())
            raise
    def enable_insertion(self, text):
        """Enable text insertion mode with given text"""
        self.text_insertion_mode = True
        self.pending_text = text
        self.insert_text_action.setChecked(True)

        QMessageBox.information(
            self, "Text Insertion Mode",
            "Click anywhere on the plot to place the text.\nRight-click to cancel."
        )

    def _save_state(self):
        """Save current state to history stack"""
        try:
            state = {
                'highlights': [(x, self._serialize_highlight_items(items))
                               for x, items in self.vertical_lines],
                'floating_texts': [
                    {
                        'text': item['text'],
                        'position': item['position']
                    }
                    for item in self.floating_text_items
                ],
                'title': self.current_title,
                'x_range': (float(self.x_min_input.text()),
                            float(self.x_max_input.text()))
            }

            # Add to history
            self.history_stack.append(state)

            # Limit history size
            if len(self.history_stack) > self.max_history:
                self.history_stack.pop(0)

            # Clear redo stack when new action is performed
            self.redo_stack.clear()

            # Update button states
            self._update_undo_redo_buttons()

        except Exception as e:
            logging.error(f"Error saving state: {str(e)}")

    def _serialize_highlight_items(self, items):
        """Serialize highlight items for storage"""
        # Store only the data needed to recreate highlights
        serialized = []
        for item in items:
            if isinstance(item, pg.TextItem):
                serialized.append({
                    'type': 'text',
                    'text': item.toPlainText(),
                    'pos': item.pos()
                })
            elif isinstance(item, pg.InfiniteLine):
                serialized.append({
                    'type': 'vline',
                    'pos': item.value()
                })
        return serialized

    def _restore_state(self, state):
        """Restore a saved state"""
        try:
            # Clear current highlights
            for _, highlight_items in self.vertical_lines:
                for item in highlight_items:
                    try:
                        if item in self.main_plot.items:
                            self.main_plot.removeItem(item)
                        else:
                            for plot_item in self.plot_items:
                                if hasattr(plot_item['viewbox'], 'addedItems'):
                                    if item in plot_item['viewbox'].addedItems:
                                        plot_item['viewbox'].removeItem(item)
                                        break
                    except:
                        pass
            self.vertical_lines = []

            # Clear floating texts
            for text_item in self.floating_text_items:
                self.main_plot.removeItem(text_item['item'])
            self.floating_text_items = []

            # Restore highlights
            for x, serialized_items in state['highlights']:
                self._add_highlight(x)

            # Restore floating texts
            for text_data in state['floating_texts']:
                text_item = EditableTextItem(
                    text_data['text'],
                    parent_plot_area=self,
                    anchor=(0.5, 0.5),
                    color='k',
                    border=pg.mkPen('k', width=2),
                    fill=pg.mkBrush(255, 255, 0, 230)
                )
                text_item.setPos(*text_data['position'])

                # Make restored text items draggable too
                text_item.setFlag(text_item.GraphicsItemFlag.ItemIsMovable, True)
                text_item.setFlag(text_item.GraphicsItemFlag.ItemSendsGeometryChanges, True)
                text_item.setFlag(text_item.GraphicsItemFlag.ItemIsSelectable, True)

                self.main_plot.addItem(text_item)

                # Store reference with the text item
                stored_data = {
                    'item': text_item,
                    'text': text_data['text'],
                    'position': text_data['position']
                }
                self.floating_text_items.append(stored_data)

                # Link text_item to its data for editing/removal
                text_item.text_data = stored_data

            # Restore title
            self.current_title = state['title']
            self.title_input.setText(state['title'])
            self.main_plot.setTitle(state['title'])

            # Restore x-range
            x_min, x_max = state['x_range']
            self.x_min_input.setText(f"{x_min:.2f}")
            self.x_max_input.setText(f"{x_max:.2f}")
            self.main_plot.setXRange(x_min, x_max, padding=0)

        except Exception as e:
            logging.error(f"Error restoring state: {str(e)}")
            QMessageBox.warning(self, "Restore Error",
                                f"Could not fully restore state: {str(e)}")

    def undo_last_action(self):
        """Undo the last action"""
        if not self.history_stack:
            return

        try:
            # Save current state to redo stack
            current_state = {
                'highlights': [(x, self._serialize_highlight_items(items))
                               for x, items in self.vertical_lines],
                'floating_texts': [
                    {
                        'text': item['text'],
                        'position': item['position']
                    }
                    for item in self.floating_text_items
                ],
                'title': self.current_title,
                'x_range': (float(self.x_min_input.text()),
                            float(self.x_max_input.text()))
            }
            self.redo_stack.append(current_state)

            # Pop and restore previous state
            previous_state = self.history_stack.pop()
            self._restore_state(previous_state)

            # Update button states
            self._update_undo_redo_buttons()

            logging.info("Undo performed")

        except Exception as e:
            logging.error(f"Error in undo: {str(e)}")
            QMessageBox.warning(self, "Undo Error", f"Could not undo: {str(e)}")

    def redo_last_action(self):
        """Redo the last undone action"""
        if not self.redo_stack:
            return

        try:
            # Save current state to history stack
            current_state = {
                'highlights': [(x, self._serialize_highlight_items(items))
                               for x, items in self.vertical_lines],
                'floating_texts': [
                    {
                        'text': item['text'],
                        'position': item['position']
                    }
                    for item in self.floating_text_items
                ],
                'title': self.current_title,
                'x_range': (float(self.x_min_input.text()),
                            float(self.x_max_input.text()))
            }
            self.history_stack.append(current_state)

            # Pop and restore next state
            next_state = self.redo_stack.pop()
            self._restore_state(next_state)

            # Update button states
            self._update_undo_redo_buttons()

            logging.info("Redo performed")

        except Exception as e:
            logging.error(f"Error in redo: {str(e)}")
            QMessageBox.warning(self, "Redo Error", f"Could not redo: {str(e)}")

    def _update_undo_redo_buttons(self):
        """Update enabled state of undo/redo buttons"""
        self.undo_action.setEnabled(len(self.history_stack) > 0)
        self.redo_action.setEnabled(len(self.redo_stack) > 0)