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
        self.win = pg.plot([], title=title)

        broker_pub_port = int(LabConfig().get('ports', 'BLACS_Broker_Pub'))
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect("tcp://127.0.0.1:%d" % broker_pub_port)
        self.socket.setsockopt(zmq.SUBSCRIBE, "{} {}".format(self._device_name, self._hardware_name))

        self.analog_in_thread = threading.Thread(target=self._analog_read_loop)
        self.analog_in_thread.daemon = True
        self.analog_in_thread.start()

        QtGui.QApplication.instance().exec_()

        self.to_parent.put("closed")

    def _analog_read_loop(self):
        while True:
            devicename_and_channel, data = self.socket.recv_multipart()
            self.update_plot(np.frombuffer(buffer(data), dtype=np.float64))

    @inmain_decorator(False)
    def update_plot(self, data):
        self.data = np.append(self.data, data)
        if self.data.size > MAX_DATA:
            self.data = np.delete(self.data, np.arange(self.data.size - MAX_DATA))

        self.win.plot(self.data, clear=True)
