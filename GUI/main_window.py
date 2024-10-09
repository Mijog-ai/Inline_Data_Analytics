from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QFileDialog, QMessageBox
from .menu_bar import MenuBar
from .tool_bar  import ToolBar
from .left_panel import LeftPanel
from .right_panel import RightPanel
from utils.asc_utils import load_and_process_asc_file, load_and_process_csv_file, load_and_process_tdms_file
import pandas as pd


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Format Data Visualization Tool")
        self.setGeometry(100, 100, 1600, 900)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.df = None
        self.setup_ui()

    def setup_ui(self):
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.tool_bar = ToolBar(self)
        self.addToolBar(self.tool_bar)

        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)

        self.layout.addWidget(self.left_panel, 1)
        self.layout.addWidget(self.right_panel, 4)

    def load_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "",
                                                   "All Files (*);;ASC Files (*.asc);;CSV Files (*.csv);;TDMS Files (*.tdms)")
        if file_name:
            try:
                file_extension = file_name.split('.')[-1].lower()
                if file_extension == 'asc':
                    self.df = load_and_process_asc_file(file_name)
                elif file_extension == 'csv':
                    self.df = load_and_process_csv_file(file_name)
                elif file_extension == 'tdms':
                    self.df = load_and_process_tdms_file(file_name)
                else:
                    raise ValueError(f"Unsupported file type: {file_extension}")

                self.update_ui_after_load()
                QMessageBox.information(self, "Success", "File loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while loading the file: {str(e)}")

    def update_ui_after_load(self):
        # Update axis selection options
        self.left_panel.axis_selection.update_options(self.df.columns)

        # Update statistics
        self.right_panel.statistics_area.update_stats(self.df)

    def save_data(self):
        if self.df is None:
            QMessageBox.warning(self, "Warning", "No data to save. Please load a file first.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save Data", "", "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if file_name:
            try:
                if file_name.endswith('.csv'):
                    self.df.to_csv(file_name, index=False)
                elif file_name.endswith('.xlsx'):
                    self.df.to_excel(file_name, index=False)
                QMessageBox.information(self, "Success", "Data saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while saving the data: {str(e)}")

    def save_plot(self):
        if not hasattr(self.right_panel.plot_area, 'figure') or len(self.right_panel.plot_area.figure.axes) == 0:
            QMessageBox.warning(self, "Warning", "No plot to save. Please create a plot first.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save Plot", "", "PNG Files (*.png);;PDF Files (*.pdf)")
        if file_name:
            try:
                fig = self.right_panel.plot_area.figure

                # Get comments from the comment box
                comments = self.left_panel.comment_box.get_comments()
                if comments:
                    fig.text(0.1, 0.01, comments, wrap=True, fontsize=8, va='bottom')

                # Save the figure
                fig.savefig(file_name, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", "Plot saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while saving the plot: {str(e)}")

    def export_table_to_excel(self):
        if self.df is None:
            QMessageBox.warning(self, "Warning", "No data to export. Please load a file first.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Export Table to Excel", "", "Excel Files (*.xlsx)")
        if file_name:
            try:
                with pd.ExcelWriter(file_name) as writer:
                    # Write the main data
                    self.df.to_excel(writer, sheet_name='Data', index=False)

                    # Write statistics
                    stats = self.df.describe()
                    stats.to_excel(writer, sheet_name='Statistics')

                    # Write current plot configuration
                    plot_config = pd.DataFrame({
                        'X-axis': [self.left_panel.axis_selection.x_combo.currentText()],
                        'Y-axes': [
                            ', '.join([item.text() for item in self.left_panel.axis_selection.y_list.selectedItems()])],
                        'Smoothing': [self.left_panel.smoothing_options.smooth_check.isChecked()],
                        'Smoothing Method': [self.left_panel.smoothing_options.smooth_method.currentText()],
                        'Window Size': [self.left_panel.smoothing_options.window_size.value()],
                        'Polynomial Order': [self.left_panel.smoothing_options.poly_order.value()],
                        'Gaussian Sigma': [self.left_panel.smoothing_options.sigma.value()],
                    })
                    plot_config.to_excel(writer, sheet_name='Plot Configuration', index=False)

                    # Write comments
                    comments = pd.DataFrame({'Comments': [self.left_panel.comment_box.get_comments()]})
                    comments.to_excel(writer, sheet_name='Comments', index=False)

                QMessageBox.information(self, "Success", "Table exported to Excel successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while exporting the table: {str(e)}")