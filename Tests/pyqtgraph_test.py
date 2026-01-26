"""
PyQtGraph Interactive Plot with Multiple Y-Axes
Each column gets its own Y-axis and color
"""

import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from sklearn import datasets


class MultiAxisPlotWidget(QtWidgets.QWidget):
    """Custom widget with multiple Y-axes support"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('California Housing: Multiple Columns with Separate Y-Axes')
        self.resize(1200, 700)

        # Load California housing dataset AS DATAFRAME
        california = datasets.fetch_california_housing(as_frame=True)
        self.df = california.frame  # This is a pandas DataFrame

        # Sample data for better performance
        sample_size = 3000
        self.df_sample = self.df.sample(n=sample_size, random_state=42).reset_index(drop=True)

        # Get initial data (using first column as X-axis)
        self.x_column = self.df_sample.columns[0]  # Default X column
        self.x_data = self.df_sample[self.x_column].values

        # Calculate default axis ranges for X
        self.x_min_default = float(np.min(self.x_data))
        self.x_max_default = float(np.max(self.x_data))
        x_padding = (self.x_max_default - self.x_min_default) * 0.1
        self.x_min_default -= x_padding
        self.x_max_default += x_padding

        # Keep track of plotted items and their axes
        self.plot_items = []
        self.y_axes = []
        self.axis_colors = []

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

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        # Main layout
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        # Control panel at the top
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)

        # Create plot widget with ViewBox
        self.graphics_view = pg.GraphicsView()
        main_layout.addWidget(self.graphics_view)

        # Create layout for the plot
        self.plot_layout = pg.GraphicsLayout()
        self.graphics_view.setCentralItem(self.plot_layout)

        # Create the main plot (this will hold the X-axis)
        self.main_plot = self.plot_layout.addPlot()
        self.main_plot.setLabel('bottom', self.x_column)

        # DISABLE MOUSE INTERACTION - This keeps the plot static
        self.main_plot.setMouseEnabled(x=False, y=False)
        self.main_plot.setMenuEnabled(False)

        # Set initial X-axis range
        self.main_plot.setXRange(self.x_min_default, self.x_max_default, padding=0)

    def create_control_panel(self):
        """Create the control panel with input fields and column selector"""
        control_widget = QtWidgets.QWidget()
        control_widget.setMaximumHeight(150)
        control_layout = QtWidgets.QGridLayout()
        control_widget.setLayout(control_layout)

        # Title
        title_label = QtWidgets.QLabel("Multi-Column Plot with Separate Y-Axes")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        control_layout.addWidget(title_label, 0, 0, 1, 8)

        # Column Selector Section
        selector_frame = QtWidgets.QFrame()
        selector_frame.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        selector_layout = QtWidgets.QHBoxLayout()
        selector_frame.setLayout(selector_layout)

        column_label = QtWidgets.QLabel("Select Column to Add:")
        column_label.setStyleSheet("font-weight: bold;")
        selector_layout.addWidget(column_label)

        self.column_dropdown = QtWidgets.QComboBox()
        # READ COLUMN NAMES DIRECTLY FROM DATAFRAME
        column_names = self.df_sample.columns.tolist()
        self.column_dropdown.addItems(column_names)
        self.column_dropdown.setFixedWidth(180)
        selector_layout.addWidget(self.column_dropdown)

        # Add to Plot button
        add_button = QtWidgets.QPushButton("Add to Plot")
        add_button.setFixedWidth(100)
        add_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        add_button.clicked.connect(self.add_column_to_plot)
        selector_layout.addWidget(add_button)

        # Clear Plot button
        clear_button = QtWidgets.QPushButton("Clear All")
        clear_button.setFixedWidth(100)
        clear_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        clear_button.clicked.connect(self.clear_plot)
        selector_layout.addWidget(clear_button)

        # Remove Last button
        remove_button = QtWidgets.QPushButton("Remove Last")
        remove_button.setFixedWidth(100)
        remove_button.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
        remove_button.clicked.connect(self.remove_last_column)
        selector_layout.addWidget(remove_button)

        selector_layout.addStretch()

        control_layout.addWidget(selector_frame, 1, 0, 1, 8)

        # X-axis controls
        x_label = QtWidgets.QLabel("X-Axis Range:")
        x_label.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(x_label, 2, 0)

        control_layout.addWidget(QtWidgets.QLabel("Min:"), 2, 1)
        self.x_min_input = QtWidgets.QLineEdit(f"{self.x_min_default:.2f}")
        self.x_min_input.setFixedWidth(100)
        control_layout.addWidget(self.x_min_input, 2, 2)

        control_layout.addWidget(QtWidgets.QLabel("Max:"), 2, 3)
        self.x_max_input = QtWidgets.QLineEdit(f"{self.x_max_default:.2f}")
        self.x_max_input.setFixedWidth(100)
        control_layout.addWidget(self.x_max_input, 2, 4)

        # Apply and Reset buttons
        apply_button = QtWidgets.QPushButton("Apply X-Range")
        apply_button.setFixedWidth(120)
        apply_button.clicked.connect(self.update_x_axis_range)
        control_layout.addWidget(apply_button, 2, 5)

        reset_button = QtWidgets.QPushButton("Reset X-Range")
        reset_button.setFixedWidth(120)
        reset_button.clicked.connect(self.reset_x_axis_range)
        control_layout.addWidget(reset_button, 2, 6)

        # Active columns label
        self.active_label = QtWidgets.QLabel("Active Columns: None")
        self.active_label.setStyleSheet("color: blue; font-style: italic;")
        control_layout.addWidget(self.active_label, 3, 0, 1, 8)

        return control_widget

    def add_column_to_plot(self):
        """Add selected column data to the plot with its own Y-axis"""
        # Get selected column name from dropdown
        column_name = self.column_dropdown.currentText()

        # Check if column is already plotted
        if column_name in [item['name'] for item in self.plot_items]:
            QtWidgets.QMessageBox.information(self, "Column Already Added",
                                            f"Column '{column_name}' is already in the plot!")
            return

        # Get data directly from DataFrame
        y_data = self.df_sample[column_name].values

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
            'color': color
        })
        self.axis_colors.append(color)

        # Update active columns label
        self.update_active_label()

        print(f"Added column: {column_name} with color {color}")

    def update_views(self):
        """Update all ViewBox geometries to match the main plot"""
        for item in self.plot_items[1:]:  # Skip first one (uses main ViewBox)
            item['viewbox'].setGeometry(self.main_plot.vb.sceneBoundingRect())

    def remove_last_column(self):
        """Remove the last added column"""
        if len(self.plot_items) == 0:
            QtWidgets.QMessageBox.information(self, "No Columns",
                                            "No columns to remove!")
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

        # Update active columns label
        self.update_active_label()

        print(f"Removed column: {last_item['name']}")

    def clear_plot(self):
        """Clear all plotted items"""
        while len(self.plot_items) > 0:
            self.remove_last_column()

        print("Cleared all columns")

    def update_active_label(self):
        """Update the label showing active columns"""
        if len(self.plot_items) == 0:
            self.active_label.setText("Active Columns: None")
        else:
            column_list = ", ".join([item['name'] for item in self.plot_items])
            self.active_label.setText(f"Active Columns: {column_list}")

    def update_x_axis_range(self):
        """Update the X-axis range based on input values"""
        try:
            x_min = float(self.x_min_input.text())
            x_max = float(self.x_max_input.text())

            # Validate range
            if x_min >= x_max:
                QtWidgets.QMessageBox.warning(self, "Invalid Range",
                                            "X-axis minimum must be less than maximum!")
                return

            # Set the X-axis range
            self.main_plot.setXRange(x_min, x_max, padding=0)

        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input",
                                        "Please enter valid numeric values!")

    def reset_x_axis_range(self):
        """Reset X-axis range to default values"""
        self.x_min_input.setText(f"{self.x_min_default:.2f}")
        self.x_max_input.setText(f"{self.x_max_default:.2f}")
        self.update_x_axis_range()


def main():
    """Main function to run the application"""
    app = QtWidgets.QApplication(sys.argv)
    window = MultiAxisPlotWidget()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()