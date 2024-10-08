import sys
from PyQt5.QtWidgets import QApplication
from gui import DataVisualizationApp

def main():
    app = QApplication(sys.argv)
    window = DataVisualizationApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()