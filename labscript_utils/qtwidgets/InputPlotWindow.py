from zprocess import Process
import pyqtgraph as pg
import numpy as np
from qtutils import inmain_decorator
import qtutils.qt.QtGui as QtGui
import zmq
from labscript_utils.labconfig import LabConfig
import threading

# maximum amount of datapoints to be plotted at once
MAX_DATA = 1000


class PlotWindow(Process):
    def run(self, connection_name, hardware_name, device_name):
        self._connection_name = connection_name
        self._hardware_name = hardware_name
        self._device_name = device_name
        self.data = np.array([], dtype=np.float64)

        if self._connection_name != '-':
            title = "{} ({})".format(self._hardware_name, self._connection_name)
        else:
            title = "{}".format(self._hardware_name)
        self.plot_win = pg.plot([], title=title)

        broker_pub_port = int(LabConfig().get('ports', 'BLACS_Broker_Pub'))
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect("tcp://127.0.0.1:%d" % broker_pub_port)
        self.socket.setsockopt(zmq.SUBSCRIBE, "{} {}\0".format(self._device_name, self._hardware_name).encode('utf-8'))

        self.analog_in_thread = threading.Thread(target=self._analog_read_loop)
        self.analog_in_thread.daemon = True
        self.analog_in_thread.start()

        self.cmd_thread = threading.Thread(target=self._cmd_loop)
        self.cmd_thread.daemon = True
        self.cmd_thread.start()

        QtGui.QApplication.instance().exec_()

        self.to_parent.put("closed")

    def _analog_read_loop(self):
        while True:
            devicename_and_channel, data = self.socket.recv_multipart()
            self.update_plot(np.frombuffer(memoryview(data), dtype=np.float64))

    def _cmd_loop(self):
        while True:
            cmd = self.from_parent.get()
            if cmd == 'focus':
                self.setTopLevelWindow()

    @inmain_decorator(False)
    def setTopLevelWindow(self):
        self.plot_win.win.activateWindow()
        self.plot_win.win.raise_()

    @inmain_decorator(False)
    def update_plot(self, new_data):
        if self.data.size < MAX_DATA:
            if new_data.size + self.data.size <= MAX_DATA:
                self.data = np.append(self.data, new_data)
            else:
                if new_data.size < MAX_DATA:
                    self.data = np.roll(self.data, -new_data.size)
                    self.data[self.data.size - new_data.size:self.data.size] = new_data
                else:
                    self.data = new_data[new_data.size - MAX_DATA:new_data.size]
        else:
            if new_data.size <= self.data.size:
                self.data = np.roll(self.data, -new_data.size)
                self.data[self.data.size - new_data.size:self.data.size] = new_data
            else:
                self.data = new_data[new_data.size - self.data.size:new_data.size]

        self.plot_win.plot(self.data, clear=True)
