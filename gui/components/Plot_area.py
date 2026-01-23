"""
Plot Area Component - Recreated for better structure and maintainability
Handles all plotting functionality with toolbar controls for interactive features
"""

import logging
import traceback
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
    QLabel, QLineEdit, QPushButton, QToolBar, QAction, QGroupBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont

import pyqtgraph as pg
from pyqtgraph import PlotWidget, InfiniteLine, TextItem, mkPen, mkBrush

from utils.asc_utils import apply_smoothing


class PlotArea(QWidget):
    """
    Main plotting area with interactive features and toolbar controls
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
        self.original_lines = []
        self.smoothed_lines = []
        self.y_axes = []
        self.legend_items = []

        # Interactive elements
        self.vertical_lines = []
        self.annotations = []
        self.highlight_points = []
        self.zoom_region_lines = []
        self.floating_text_items = []

        # Plot state
        self.current_title = ""
        self.original_x_range = None
        self.pending_text = ""
        self.last_plot_params = {}

    def setup_ui(self):
        """Setup the complete UI structure"""
        self.layout = QVBoxLayout(self)

        # Title controls
        self._create_title_controls()

        # Toolbar with interactive tools
        self._create_toolbar()
        self.layout.addWidget(self.toolbar)

        # Main plot widget
        self._create_plot_widget()
        self.layout.addWidget(self.plot_widget)

        # Custom legend area (Excel-style)
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

        title_layout.addWidget(self.title_input)
        title_layout.addWidget(self.set_title_button)
        self.layout.addLayout(title_layout)

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

        # Zoom region mode
        self.zoom_region_action = self._create_action(
            "Zoom Region",
            "Enable zoom region mode - left click to add boundary lines (max 2), right click to remove",
            checkable=True,
            checked=False,
            callback=self._on_toggle_zoom_mode
        )
        self.toolbar.addAction(self.zoom_region_action)
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

        # Text removal
        self.remove_text_action = self._create_action(
            "Remove Text",
            "Enable text removal mode - left click on text to remove it",
            checkable=True,
            checked=False,
            callback=self._on_toggle_text_removal
        )
        self.toolbar.addAction(self.remove_text_action)
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
        self.plot_widget = PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Enable performance optimizations
        pg.setConfigOptions(
            antialias=True,
            useOpenGL=True,
            enableExperimental=True
        )

        # Disable default mouse interactions
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.wheelEvent = lambda event: None

        # Setup crosshair cursor
        self.crosshair_v = InfiniteLine(
            angle=90, movable=False,
            pen=mkPen('k', width=1, style=Qt.DashLine)
        )
        self.crosshair_h = InfiniteLine(
            angle=0, movable=False,
            pen=mkPen('k', width=1, style=Qt.DashLine)
        )
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_h, ignoreBounds=True)

        # Cursor label
        self.cursor_label = TextItem(
            anchor=(0, 1),
            color='k',
            fill=mkBrush(255, 255, 255, 200)
        )
        self.plot_widget.addItem(self.cursor_label, ignoreBounds=True)

        # Connect mouse events
        self.plot_widget.scene().sigMouseClicked.connect(self._on_mouse_click)
        self.plot_widget.scene().sigMouseClicked.connect(self._on_double_click)

        # Setup mouse move tracking with rate limiting
        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved
        )

    def _create_legend_area(self):
        """Create custom legend area below plot (Excel-style)"""
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
        self.crosshair_v.setVisible(self.show_cursor)
        self.crosshair_h.setVisible(self.show_cursor)
        self.cursor_label.setVisible(self.show_cursor)
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
            self.plot_widget.setCursor(Qt.ArrowCursor)

        logging.info(f"Highlight mode: {state}")

    def _on_toggle_zoom_mode(self, state):
        """Toggle zoom region mode"""
        self.zoom_mode_active = bool(state)

        if state:
            self._deactivate_other_modes(exclude='zoom')
            self.plot_widget.setCursor(Qt.ArrowCursor)
            logging.info("Zoom region mode activated")
        else:
            logging.info("Zoom region mode deactivated")
            if len(self.zoom_region_lines) > 0:
                self._clear_zoom_region()

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
            self.plot_widget.setCursor(Qt.CrossCursor)
            self._deactivate_other_modes(exclude='text_insert')
            logging.info("Text insertion mode enabled")
        else:
            self._cancel_text_insertion()

    def _on_toggle_text_removal(self, checked):
        """Toggle text removal mode"""
        if checked:
            if not self.floating_text_items:
                QMessageBox.information(
                    self, "No Texts",
                    "There are no text boxes to remove."
                )
                self.remove_text_action.setChecked(False)
                return

            self.text_removal_mode = True
            self.plot_widget.setCursor(Qt.PointingHandCursor)
            self._deactivate_other_modes(exclude='text_remove')

            QMessageBox.information(
                self, "Text Removal Mode",
                "Click on a text box to remove it.\nClick toolbar button again to exit this mode."
            )
            logging.info("Text removal mode enabled")
        else:
            self.text_removal_mode = False
            self.plot_widget.setCursor(Qt.ArrowCursor)
            logging.info("Text removal mode disabled")

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
            self.plot_widget.blockSignals(True)
            for text_data in self.floating_text_items:
                self.plot_widget.removeItem(text_data['item'])
            self.plot_widget.blockSignals(False)

            self.floating_text_items = []

            if self.remove_text_action:
                self.remove_text_action.setChecked(False)
            self.text_removal_mode = False

            logging.info("Cleared all floating texts")
            QMessageBox.information(self, "Cleared", "All text boxes have been removed.")

    def _on_set_title(self):
        """Set the plot title from input"""
        title = self.title_input.text()
        self.current_title = title
        self.plot_widget.setTitle(title)
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

        if exclude != 'zoom':
            self.zoom_mode_active = False
            if self.zoom_region_action:
                self.zoom_region_action.setChecked(False)

        if exclude != 'text_insert':
            self.text_insertion_mode = False
            if self.insert_text_action:
                self.insert_text_action.setChecked(False)

        if exclude != 'text_remove':
            self.text_removal_mode = False
            if self.remove_text_action:
                self.remove_text_action.setChecked(False)

    # ========================================================================
    # MOUSE EVENT HANDLERS
    # ========================================================================

    def _on_mouse_moved(self, evt):
        """Handle mouse movement for crosshair cursor"""
        if not self.show_cursor:
            return

        pos = evt[0]
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return

        mouse_point = self.plot_widget.getPlotItem().getViewBox().mapSceneToView(pos)
        x, y = mouse_point.x(), mouse_point.y()

        # Update crosshair position
        self.crosshair_v.setPos(x)
        self.crosshair_h.setPos(y)

        # Build cursor label text
        xlabel = self.last_plot_params.get('x_column', 'X') if self.last_plot_params else 'X'
        cursor_text = f"{xlabel}: {x:.2f}\n"

        for item in self.plot_items:
            if item['curve'].isVisible():
                x_data = item['x_data']
                y_data = item['y_data']

                if len(x_data) > 0:
                    idx = self._find_nearest_index(x_data, x)
                    nearest_y = y_data[idx]
                    cursor_text += f"{item['label']}: {nearest_y:.2f}\n"

        self.cursor_label.setPos(x, y)
        self.cursor_label.setText(cursor_text.strip())

    def _on_mouse_click(self, event):
        """Handle mouse click events"""
        pos = event.scenePos()
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return

        mouse_point = self.plot_widget.getPlotItem().getViewBox().mapSceneToView(pos)
        x, y = mouse_point.x(), mouse_point.y()

        if event.button() == Qt.LeftButton:
            self._handle_left_click(x, y)
        elif event.button() == Qt.RightButton:
            self._handle_right_click(x, y)

    def _handle_left_click(self, x, y):
        """Handle left mouse click based on active mode"""
        if self.text_insertion_mode:
            self._insert_floating_text_at(x, y)
        elif self.text_removal_mode:
            if self._remove_floating_text_at(x, y):
                QMessageBox.information(
                    self, "Text Removed",
                    "Text box has been removed."
                )
            else:
                QMessageBox.information(
                    self, "No Text Found",
                    "No text box found at this location."
                )
        elif self.zoom_mode_active:
            self._add_zoom_region_line(x)

    def _handle_right_click(self, x, y):
        """Handle right mouse click based on active mode"""
        if self.text_insertion_mode:
            self._cancel_text_insertion()
        elif self.text_removal_mode:
            self.remove_text_action.setChecked(False)
            self._on_toggle_text_removal(False)
        elif self.zoom_mode_active:
            self._remove_zoom_region_line(x)
        elif self.yaxis_approx_value_highlighter:
            self._add_highlight(x)

    def _on_double_click(self, event):
        """Handle double-click to remove highlights"""
        if not event.double():
            return

        pos = event.scenePos()
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return

        mouse_point = self.plot_widget.getPlotItem().getViewBox().mapSceneToView(pos)
        x = mouse_point.x()

        if self.yaxis_approx_value_highlighter:
            self._remove_nearest_highlight(x)

    # ========================================================================
    # PLOTTING FUNCTIONALITY
    # ========================================================================

    def plot_data(self, df, x_column, y_columns, smoothing_params, limit_lines=[], title=None):
        """Main plotting function"""
        try:
            # Update title
            if title is not None:
                self.current_title = title
            else:
                title = self.current_title

            logging.info(f"Plotting data: x={x_column}, y={y_columns}, title={title}")

            # Disable updates during batch operations
            self.plot_widget.setUpdatesEnabled(False)

            # Clear previous plot
            self._clear_plot_data()

            # Set labels
            self.plot_widget.setTitle(title)
            self.plot_widget.setLabel('bottom', x_column)

            # Generate colors for each series
            colors = self._generate_distinct_colors(len(y_columns))

            # Get main viewbox
            main_viewbox = self.plot_widget.getPlotItem().getViewBox()
            if not isinstance(main_viewbox, pg.ViewBox):
                logging.error(f"Invalid main viewbox type: {type(main_viewbox)}")
                main_viewbox = self.plot_widget.plotItem.vb

            # Determine if multiple Y-axes needed
            use_multiple_axes = self._should_use_multiple_axes(df, y_columns)

            # Setup resize handling for multiple axes
            if use_multiple_axes and len(y_columns) > 1:
                try:
                    main_viewbox.sigResized.disconnect()
                except:
                    pass
                main_viewbox.sigResized.connect(self._update_views)

            # Plot each data series
            for i, (y_column, color) in enumerate(zip(y_columns, colors)):
                self._plot_single_series(
                    df, x_column, y_column, color, i,
                    main_viewbox, use_multiple_axes, smoothing_params
                )

            # Populate legend
            if self.show_legend:
                self._populate_legend(y_columns, colors, smoothing_params['apply'])

            # Add limit lines
            self._add_limit_lines(limit_lines)

            # Toggle cursor visibility
            self._on_toggle_cursor(self.cursor_action.isChecked())

            # Set X-axis range
            self._set_x_axis_range(df[x_column].values, main_viewbox)

            # Store plot parameters for later updates
            self.last_plot_params = {
                'df': df,
                'x_column': x_column,
                'y_columns': y_columns,
                'smoothing_params': smoothing_params,
                'limit_lines': limit_lines,
                'title': title
            }

            # Re-enable updates
            self.plot_widget.setUpdatesEnabled(True)
            self.plot_widget.update()

            logging.info("Plot completed successfully")

        except Exception as e:
            logging.error(f"Error in plot_data: {str(e)}")
            logging.error(traceback.format_exc())
            self.plot_widget.setUpdatesEnabled(True)
            QMessageBox.critical(self, "Error", f"An error occurred while plotting: {str(e)}")

    def _clear_plot_data(self):
        """Clear all plot data and axes"""
        self._clear_all_axes()
        self.plot_widget.clear()

        self.plot_items = []
        self.original_lines = []
        self.smoothed_lines = []
        self.y_axes = []

        self._clear_legend()

        # Re-add crosshair elements
        self.plot_widget.addItem(self.crosshair_v)
        self.plot_widget.addItem(self.crosshair_h)
        self.plot_widget.addItem(self.cursor_label)

    def _should_use_multiple_axes(self, df, y_columns):
        """Determine if multiple Y-axes are needed based on data ranges"""
        if len(y_columns) <= 1:
            return False

        # Get all y-data ranges
        all_ranges = []
        for y_column in y_columns:
            y_data = df[y_column].values
            if len(y_data) > 0:
                y_min = float(np.min(y_data))
                y_max = float(np.max(y_data))
                all_ranges.append((y_min, y_max))

        if len(all_ranges) <= 1:
            return False

        # Calculate range ratios
        ranges = [(y_max - y_min) for y_min, y_max in all_ranges]
        max_range = max(ranges)
        min_range = min(ranges) if min(ranges) > 0 else 1

        # Use multiple axes if ranges differ by more than 10x
        ratio = max_range / min_range
        if ratio > 10:
            logging.info(f"Using multiple Y-axes (range ratio: {ratio:.1f})")
            return True

        return False

    def _plot_single_series(self, df, x_column, y_column, color, index,
                           main_viewbox, use_multiple_axes, smoothing_params):
        """Plot a single data series with optional smoothing"""
        x_data = df[x_column].values
        y_data = df[y_column].values

        # Determine viewbox to use
        if index == 0 or not use_multiple_axes:
            viewbox = main_viewbox
            if index == 0:
                self.plot_widget.setLabel('left', y_column, color=color.name())
        else:
            viewbox = self._create_additional_y_axis(y_column, color, index, main_viewbox)

        # Plot original data
        original_alpha = 80 if smoothing_params['apply'] else 255
        self._plot_curve(x_data, y_data, color, original_alpha, y_column, viewbox, "(Original)")

        # Plot smoothed data if requested
        if smoothing_params['apply']:
            y_smoothed = apply_smoothing(
                y_data,
                method=smoothing_params['method'],
                window_length=smoothing_params['window_length'],
                poly_order=smoothing_params['poly_order'],
                sigma=smoothing_params['sigma']
            )
            self._plot_curve(x_data, y_smoothed, color, 255, y_column, viewbox, "(Smoothed)")

        # Set Y-axis range for this viewbox
        self._set_y_axis_range(y_data, viewbox, y_column)

    def _create_additional_y_axis(self, y_column, color, index, main_viewbox):
        """Create an additional Y-axis for a data series"""
        axis_item = pg.AxisItem('right')
        axis_item.setLabel(y_column, color=color.name())

        viewbox = pg.ViewBox()
        viewbox.setXLink(main_viewbox)

        self.plot_widget.plotItem.layout.addItem(axis_item, 2, 3 + index - 1)
        self.plot_widget.scene().addItem(viewbox)
        axis_item.linkToView(viewbox)
        viewbox.setGeometry(main_viewbox.sceneBoundingRect())

        self.y_axes.append(viewbox)
        logging.info(f"Created additional Y-axis for {y_column}")

        return viewbox

    def _plot_curve(self, x_data, y_data, color, alpha, label, viewbox, suffix=""):
        """Create and add a plot curve to the specified viewbox"""
        curve_color = QColor(color)
        curve_color.setAlpha(alpha)
        pen = mkPen(color=curve_color, width=2)

        curve = pg.PlotDataItem(
            x_data, y_data,
            pen=pen,
            name=f'{label} {suffix}',
            clipToView=True,
            autoDownsample=True,
            downsampleMethod='subsample'
        )

        if not isinstance(viewbox, pg.ViewBox):
            logging.error(f"Invalid viewbox type: {type(viewbox)}")
            viewbox = self.plot_widget.getPlotItem().getViewBox()

        viewbox.addItem(curve)

        if suffix == "(Original)" or suffix == "":
            self.original_lines.append(curve)
        else:
            self.smoothed_lines.append(curve)

        self.plot_items.append({
            'curve': curve,
            'x_data': x_data,
            'y_data': y_data,
            'label': label,
            'viewbox': viewbox
        })

    def _set_y_axis_range(self, y_data, viewbox, y_column):
        """Set the Y-axis range for a viewbox based on data"""
        if len(y_data) == 0:
            return

        y_min = float(np.min(y_data))
        y_max = float(np.max(y_data))

        # Calculate range with padding
        y_range = y_max - y_min
        if y_range == 0:
            y_range = abs(y_max) if y_max != 0 else 1

        y_min_display = y_min - (y_range * 0.02)
        y_max_display = y_max + (y_range * 0.05)

        viewbox.setLimits(yMin=y_min_display, yMax=y_max_display)
        viewbox.setYRange(y_min_display, y_max_display, padding=0)
        viewbox.enableAutoRange(enable=False)

        logging.info(f"Y-axis range for {y_column}: [{y_min_display:.2f}, {y_max_display:.2f}]")

    def _set_x_axis_range(self, x_data, viewbox):
        """Set the X-axis range from data"""
        if len(x_data) == 0:
            return

        x_min = float(np.min(x_data))
        x_max = float(np.max(x_data))

        self.original_x_range = (x_min, x_max)

        viewbox.setLimits(xMin=x_min, xMax=x_max)
        viewbox.setXRange(x_min, x_max, padding=0.02)

        logging.info(f"X-axis range set: [{x_min:.2f}, {x_max:.2f}]")

    def _add_limit_lines(self, limit_lines):
        """Add limit lines to the plot"""
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

    def _populate_legend(self, y_columns, colors, has_smoothing):
        """Populate custom legend with colored items"""
        self._clear_legend()

        self.legend_layout.addStretch()

        for y_column, color in zip(y_columns, colors):
            self._add_legend_item(y_column, color)

            if has_smoothing:
                self.legend_layout.addWidget(QLabel("  "))
                self._add_legend_item(f"{y_column} (Smoothed)", color)

        self.legend_layout.addStretch()
        logging.info(f"Legend populated with {len(self.legend_items)} items")

    def _add_legend_item(self, label, color):
        """Add a single item to the legend"""
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(5)

        # Color indicator
        color_label = QLabel()
        color_label.setFixedSize(30, 3)
        color_label.setStyleSheet(f"background-color: {color.name()}; border: none;")
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
        xlabel = self.last_plot_params.get('x_column', 'X') if self.last_plot_params else 'X'
        points_group = []

        main_viewbox = self.plot_widget.getPlotItem().getViewBox()
        self.plot_widget.setUpdatesEnabled(False)

        for item in self.plot_items:
            if not item['curve'].isVisible():
                continue

            x_data = item['x_data']
            y_data = item['y_data']

            if len(x_data) == 0:
                continue

            # Find nearest point
            idx = self._find_nearest_index(x_data, x)
            nearest_x = x_data[idx]
            nearest_y = y_data[idx]

            viewbox = item['viewbox']

            # Vertical line from bottom to point
            y_range = viewbox.viewRange()[1]
            y_min = y_range[0]

            vertical_line = pg.PlotDataItem(
                [nearest_x, nearest_x],
                [y_min, nearest_y],
                pen=mkPen('gray', width=2, style=Qt.DashLine)
            )
            viewbox.addItem(vertical_line)
            points_group.append((vertical_line, viewbox))

            # Horizontal line from left to point
            x_range = main_viewbox.viewRange()[0]
            x_min = x_range[0]

            horizontal_line = pg.PlotDataItem(
                [x_min, nearest_x],
                [nearest_y, nearest_y],
                pen=mkPen('gray', width=2, style=Qt.DashLine)
            )
            viewbox.addItem(horizontal_line)
            points_group.append((horizontal_line, viewbox))

            # Highlight point
            scatter = pg.ScatterPlotItem(
                [nearest_x], [nearest_y],
                pen=mkPen('r', width=2),
                brush=mkBrush('r'),
                size=10,
                symbol='o'
            )
            viewbox.addItem(scatter)
            points_group.append((scatter, viewbox))

            # Annotation
            annotation_text = f"{xlabel}: {nearest_x:.2f}\n{item['label']}: {nearest_y:.2f}"
            annotation = TextItem(
                annotation_text,
                anchor=(0, 0.5),
                color='k',
                fill=mkBrush(255, 255, 255, 200),
                border=mkPen('k', width=1)
            )
            annotation.setPos(nearest_x, nearest_y)
            viewbox.addItem(annotation)
            points_group.append((annotation, viewbox))

        self.vertical_lines.append((x, points_group))

        self.plot_widget.setUpdatesEnabled(True)
        self.plot_widget.update()

    def _remove_nearest_highlight(self, x):
        """Remove the nearest highlight"""
        if not self.vertical_lines:
            return

        distances = np.array([abs(vline[0] - x) for vline in self.vertical_lines])
        nearest_index = np.argmin(distances)

        _, points_group = self.vertical_lines[nearest_index]

        for item, viewbox in points_group:
            try:
                viewbox.blockSignals(True)
                viewbox.removeItem(item)
                viewbox.blockSignals(False)
            except Exception as e:
                logging.warning(f"Could not remove highlight item: {e}")
                try:
                    self.plot_widget.removeItem(item)
                except:
                    pass

        self.vertical_lines.pop(nearest_index)
        logging.info(f"Removed highlight at x={x:.2f}")

    # ========================================================================
    # ZOOM REGION FUNCTIONALITY
    # ========================================================================

    def _add_zoom_region_line(self, x):
        """Add a zoom region boundary line"""
        if len(self.zoom_region_lines) >= 2:
            QMessageBox.information(
                self, "Zoom Region",
                "Maximum 2 zoom region lines allowed. Right-click to remove existing lines."
            )
            return

        zoom_line = InfiniteLine(
            pos=x,
            angle=90,
            pen=mkPen('b', width=3, style=Qt.DashLine),
            movable=True
        )
        zoom_line.sigPositionChanged.connect(self._update_zoom_region)

        self.plot_widget.addItem(zoom_line)
        self.zoom_region_lines.append((x, zoom_line))

        logging.info(f"Added zoom region line at x={x:.2f}")

        if len(self.zoom_region_lines) == 2:
            self._update_zoom_region()

    def _remove_zoom_region_line(self, x):
        """Remove the nearest zoom region line"""
        if not self.zoom_region_lines:
            return

        distances = [abs(line[0] - x) for line in self.zoom_region_lines]
        nearest_index = np.argmin(distances)

        _, zoom_line = self.zoom_region_lines[nearest_index]
        self.plot_widget.removeItem(zoom_line)
        self.zoom_region_lines.pop(nearest_index)

        logging.info(f"Removed zoom region line at x={x:.2f}")

        if len(self.zoom_region_lines) < 2:
            self._restore_original_range()

    def _update_zoom_region(self):
        """Update plot zoom based on two region lines"""
        if len(self.zoom_region_lines) != 2:
            return

        x1 = self.zoom_region_lines[0][1].value()
        x2 = self.zoom_region_lines[1][1].value()

        x_min = min(x1, x2)
        x_max = max(x1, x2)

        self.plot_widget.setXRange(x_min, x_max, padding=0.02)
        logging.info(f"Zoomed to region: {x_min:.2f} to {x_max:.2f}")

    def _clear_zoom_region(self):
        """Clear all zoom region lines"""
        for _, zoom_line in self.zoom_region_lines:
            self.plot_widget.removeItem(zoom_line)
        self.zoom_region_lines = []
        self._restore_original_range()
        logging.info("Cleared all zoom region lines")

    def _restore_original_range(self):
        """Restore plot to original data range"""
        if self.original_x_range is None:
            return

        main_viewbox = self.plot_widget.getPlotItem().getViewBox()
        main_viewbox.setXRange(
            self.original_x_range[0],
            self.original_x_range[1],
            padding=0.02
        )

        # Restore Y ranges
        if self.last_plot_params:
            df = self.last_plot_params['df']
            y_columns = self.last_plot_params['y_columns']

            for item in self.plot_items:
                y_column = item['label']
                viewbox = item['viewbox']

                if y_column in y_columns:
                    y_data = df[y_column].values
                    if len(y_data) > 0:
                        y_min = float(np.min(y_data))
                        y_max = float(np.max(y_data))
                        y_range = y_max - y_min
                        if y_range == 0:
                            y_range = abs(y_max) if y_max != 0 else 1

                        y_min_display = y_min - (y_range * 0.02)
                        y_max_display = y_max + (y_range * 0.05)

                        viewbox.setYRange(y_min_display, y_max_display, padding=0)

        logging.info(f"Restored original range: {self.original_x_range}")

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
                fill=mkBrush(255, 255, 200, 220),
                border=mkPen('k', width=2)
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

            # Exit insertion mode
            self.text_insertion_mode = False
            self.pending_text = ""
            self.plot_widget.setCursor(Qt.ArrowCursor)
            self.insert_text_action.setChecked(False)

        except Exception as e:
            logging.error(f"Error inserting floating text: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to insert text: {str(e)}")

    def _remove_floating_text_at(self, x, y):
        """Remove floating text near clicked position"""
        if not self.floating_text_items:
            return False

        threshold = 50
        closest_text = None
        min_distance = float('inf')

        for text_data in self.floating_text_items:
            text_x, text_y = text_data['position']
            distance = np.sqrt((text_x - x)**2 + (text_y - y)**2)

            if distance < min_distance:
                min_distance = distance
                closest_text = text_data

        if closest_text and min_distance < threshold:
            self.plot_widget.removeItem(closest_text['item'])
            self.floating_text_items.remove(closest_text)
            logging.info(f"Removed floating text at ({closest_text['position'][0]:.2f}, {closest_text['position'][1]:.2f})")
            return True

        return False

    def _cancel_text_insertion(self):
        """Cancel text insertion mode"""
        self.text_insertion_mode = False
        self.pending_text = ""
        self.plot_widget.setCursor(Qt.ArrowCursor)
        self.insert_text_action.setChecked(False)
        logging.info("Text insertion mode cancelled")

    # ========================================================================
    # CURVE FITTING FUNCTIONALITY
    # ========================================================================

    def apply_curve_fitting(self, x_data, y_data, fit_func, equation, fit_type, x_label, y_label):
        """Apply curve fitting to plot"""
        try:
            logging.info(f"Applying {fit_type} curve fitting")

            for item in self.plot_items:
                if item['label'] == y_label:
                    x_fit = np.linspace(np.min(x_data), np.max(x_data), len(x_data))
                    y_fit = fit_func(x_fit)

                    item['curve'].setData(x_fit, y_fit)
                    item['is_fitted'] = True
                    item['fit_type'] = fit_type
                    item['fit_equation'] = equation

                    logging.info(f"Updated line with {fit_type} fit")
                    break

            current_title = self.plot_widget.plotItem.titleLabel.text
            self.plot_widget.setTitle(f'{current_title} - {fit_type} Fit Applied')

            logging.info("Curve fitting applied successfully")

        except Exception as e:
            logging.error(f"Error in apply_curve_fitting: {str(e)}")
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
                        y_column = item['label']
                        y_data = main_window.filtered_df[y_column].values

                        item['curve'].setData(x_data, y_data)
                        item['is_fitted'] = False

            logging.info("Curve fitting removed successfully")

        except Exception as e:
            logging.error(f"Error removing curve fitting: {str(e)}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _generate_distinct_colors(self, n):
        """Generate N visually distinct colors using HSV"""
        if n == 0:
            return []

        colors = []
        for i in range(n):
            hue = int(255 * i / n)
            color = QColor.fromHsv(hue, 255, 200)
            colors.append(color)
        return colors

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

    def _update_views(self):
        """Update geometry of all additional Y-axis viewboxes"""
        try:
            main_viewbox = self.plot_widget.getPlotItem().getViewBox()
            if not isinstance(main_viewbox, pg.ViewBox):
                logging.warning(f"Invalid main_viewbox type: {type(main_viewbox)}")
                return

            for viewbox in self.y_axes:
                if isinstance(viewbox, pg.ViewBox):
                    try:
                        viewbox.blockSignals(True)
                        viewbox.setGeometry(main_viewbox.sceneBoundingRect())
                        viewbox.blockSignals(False)
                    except Exception as e:
                        logging.warning(f"Error updating viewbox geometry: {e}")
        except Exception as e:
            logging.warning(f"Error updating views: {e}")

    def _clear_all_axes(self):
        """Clear all plot items and axes"""
        logging.info("Clearing all axes and plot items")

        try:
            main_viewbox = self.plot_widget.getPlotItem().getViewBox()
        except:
            main_viewbox = None

        # Remove plot data items
        for item_data in self.plot_items:
            try:
                curve = item_data.get('curve')
                viewbox = item_data.get('viewbox')

                if curve and viewbox and isinstance(viewbox, pg.ViewBox):
                    try:
                        viewbox.removeItem(curve)
                    except:
                        if main_viewbox:
                            try:
                                main_viewbox.removeItem(curve)
                            except:
                                pass
            except Exception as e:
                logging.warning(f"Error removing curve: {e}")

        # Remove additional viewboxes
        for viewbox in self.y_axes:
            try:
                if not isinstance(viewbox, pg.ViewBox):
                    continue

                for item in list(viewbox.allChildren()):
                    try:
                        viewbox.removeItem(item)
                    except:
                        pass

                if viewbox.scene() is not None:
                    self.plot_widget.scene().removeItem(viewbox)
            except Exception as e:
                logging.warning(f"Error removing viewbox: {e}")

        # Remove axis items from layout
        try:
            layout = self.plot_widget.plotItem.layout
            items_to_remove = []

            for row in range(layout.rowCount()):
                for col in range(layout.columnCount()):
                    try:
                        item = layout.itemAt(row, col)
                        if item is not None and isinstance(item, pg.AxisItem):
                            if not ((row == 2 and col == 1) or (row == 3 and col == 2)):
                                items_to_remove.append(item)
                    except:
                        pass

            for item in items_to_remove:
                try:
                    layout.removeItem(item)
                except Exception as e:
                    logging.warning(f"Error removing axis item: {e}")
        except Exception as e:
            logging.warning(f"Error clearing axis layout: {e}")

        # Reset storage
        self.plot_items = []
        self.original_lines = []
        self.smoothed_lines = []
        self.y_axes = []

        logging.info("All axes cleared successfully")

    # ========================================================================
    # PUBLIC API METHODS
    # ========================================================================

    def clear_plot(self):
        """Clear the entire plot"""
        logging.info("Clearing plot")

        self._clear_all_axes()
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

        if hasattr(self, 'last_plot_params'):
            delattr(self, 'last_plot_params')

        self._clear_legend()

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
        """Set default title in input field and apply it"""
        self.title_input.setText(title)
        self.current_title = title
        self.plot_widget.setTitle(title)
        if hasattr(self, 'last_plot_params'):
            self.last_plot_params['title'] = title

    def update_plot(self):
        """Update plot with last parameters"""
        if hasattr(self, 'last_plot_params'):
            self.plot_data(**self.last_plot_params)

    def toggle_original_data(self):
        """Toggle visibility of original data lines"""
        show_original = True
        for line in self.original_lines:
            line.setVisible(show_original)
        logging.info("Original data visibility toggled")

    def get_show_original_state(self):
        """Get state of show original - always True"""
        return True

    def set_show_original_state(self, state):
        """Set state of show original - deprecated"""
        pass

    def enable_insertion(self, text):
        """Enable text insertion mode with given text"""
        self.text_insertion_mode = True
        self.pending_text = text
        self.plot_widget.setCursor(Qt.CrossCursor)

        QMessageBox.information(
            self, "Text Insertion Mode",
            "Click anywhere on the plot to place the text.\nRight-click to cancel."
        )

    def clear_custom_legend(self):
        """Clear custom legend - alias for _clear_legend"""
        self._clear_legend()

    def populate_custom_legend(self, y_columns, colors, has_smoothing):
        """Populate custom legend - alias for _populate_legend"""
        self._populate_legend(y_columns, colors, has_smoothing)

    def set_title(self):
        """Set title - alias for _on_set_title"""
        self._on_set_title()

    def toggle_cursor(self, state):
        """Toggle cursor - alias for _on_toggle_cursor"""
        self._on_toggle_cursor(state)

    def toggle_legend(self, state):
        """Toggle legend - alias for _on_toggle_legend"""
        self._on_toggle_legend(state)

    def toggle_highlighter(self, state):
        """Toggle highlighter - alias for _on_toggle_highlighter"""
        self._on_toggle_highlighter(state)

    def toggle_zoom_region_mode(self, state):
        """Toggle zoom region mode - alias for _on_toggle_zoom_mode"""
        self._on_toggle_zoom_mode(state)

    def toggle_text_insertion_mode(self, checked):
        """Toggle text insertion mode - alias for _on_toggle_text_insertion"""
        self._on_toggle_text_insertion(checked)

    def toggle_text_removal_mode(self, checked):
        """Toggle text removal mode - alias for _on_toggle_text_removal"""
        self._on_toggle_text_removal(checked)

    def clear_all_floating_texts(self):
        """Clear all floating texts - alias for _on_clear_all_texts"""
        self._on_clear_all_texts()

    def clear_zoom_region(self):
        """Clear zoom region - alias for _clear_zoom_region"""
        self._clear_zoom_region()
