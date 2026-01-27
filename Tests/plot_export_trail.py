import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from sklearn.datasets import load_iris
import pyqtgraph as pg


class PlotWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout()

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Add title
        self.plot_widget.setTitle('Iris Dataset - Dual Y-Axis', color='k', size='14pt')

        # Load iris dataset
        iris = load_iris()
        x = np.arange(len(iris.data))
        y1 = iris.data[:, 0]  # sepal length
        y2 = iris.data[:, 1]  # sepal width

        # Plot on left y-axis
        self.plot_widget.plot(x, y1, pen=pg.mkPen('b', width=2), name='Sepal Length')
        self.plot_widget.setLabel('left', 'Sepal Length', color='blue')
        self.plot_widget.setLabel('bottom', 'Sample Index')
        self.plot_widget.showAxis('right')

        # Create right y-axis
        self.view_box_right = pg.ViewBox()
        self.plot_widget.scene().addItem(self.view_box_right)
        self.plot_widget.getAxis('right').linkToView(self.view_box_right)
        self.view_box_right.setXLink(self.plot_widget)
        self.plot_widget.getAxis('right').setLabel('Sepal Width', color='red')

        # Plot on right y-axis
        self.curve2 = pg.PlotCurveItem(x, y2, pen=pg.mkPen('r', width=2))
        self.view_box_right.addItem(self.curve2)

        # Update views
        self.plot_widget.getViewBox().sigResized.connect(self.updateViews)
        self.updateViews()

        # Export button
        export_btn = QtWidgets.QPushButton('Export as PNG')
        export_btn.clicked.connect(self.exportImage)

        layout.addWidget(self.plot_widget)
        layout.addWidget(export_btn)
        self.setLayout(layout)
        self.setWindowTitle('Iris Dataset - Dual Y-Axis')
        self.resize(800, 600)

    def updateViews(self):
        self.view_box_right.setGeometry(self.plot_widget.getViewBox().sceneBoundingRect())
        self.view_box_right.linkedViewChanged(self.plot_widget.getViewBox(), self.view_box_right.XAxis)

    def exportImage(self):
        # Grab the entire plot widget as a pixmap
        pixmap = self.plot_widget.grab()
        pixmap.save('iris_plot.png', 'PNG')
        QtWidgets.QMessageBox.information(self, 'Success', 'Image saved as iris_plot.png')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = PlotWindow()
    window.show()
    sys.exit(app.exec_())