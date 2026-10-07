# import matplotlib.pyplot as plt
# import numpy as np
# from matplotlib.animation import FuncAnimation
#
# fig, ax = plt.subplots()
# line, = ax.plot([], [], lw=2)
# xdata, ydata = [], []
#
# def update(frame):
#     xdata.append(frame)
#     ydata.append(np.sin(frame))
#     line.set_data(xdata, ydata)
#     ax.relim()
#     ax.autoscale_view()
#     return line,
#
# ani = FuncAnimation(fig, update, frames=np.linspace(0, 10, 200), blit=True)
# plt.show()


import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
import numpy as np

app = QtWidgets.QApplication([])
win = pg.plot()
data = np.random.normal(size=100)
curve = win.plot(data)

def update():
    curve.setData(np.random.normal(size=100))

timer = pg.QtCore.QTimer()
timer.timeout.connect(update)
timer.start(50)

app.exec_()