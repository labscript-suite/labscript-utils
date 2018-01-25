#####################################################################
#                                                                   #
# analogoutput.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

import sys

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *
from qtutils import *
import qtutils.icons

import threading
import time
from labscript_utils.qtwidgets.InputPlotWindow import PlotWindow


class AnalogInput(QWidget):
    def __init__(self, device_name, hardware_name, connection_name='-', display_name=None, horizontal_alignment=False, parent=None):
        QWidget.__init__(self, parent)

        self.plot = None
        self._device_name = device_name
        self._connection_name = connection_name
        self._hardware_name = hardware_name
        self.win = None

        label_text = (self._hardware_name + '\n' + self._connection_name) if display_name is None else display_name
        self._label = QLabel(label_text)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self._line_edit = QLineEdit()
        self._line_edit.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        self._line_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._line_edit.setMaximumWidth(55)
        self._line_edit.setAlignment(Qt.AlignRight)
        self._line_edit.setReadOnly(True)

        self._plot_btn = QPushButton()
        self._plot_btn.setIcon(QIcon(':/qtutils/fugue/chart-up'))
        self._plot_btn.clicked.connect(self.open_plot_window)

        self._value_changed_function = None

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)

        # Create widgets and layouts
        if horizontal_alignment:
            self._layout = QHBoxLayout(self)
            self._layout.addWidget(self._label)
            self._layout.addWidget(self._line_edit)
            self._layout.addWidget(self._plot_btn)
        else:
            self._layout = QGridLayout(self)
            self._layout.setVerticalSpacing(0)
            self._layout.setHorizontalSpacing(0)
            self._layout.setContentsMargins(5, 5, 5, 5)

            self._label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
            self._layout.addWidget(self._label)
            self._layout.addItem(QSpacerItem(0, 0, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum), 0, 1)

            h_widget = QWidget()
            h_layout = QHBoxLayout(h_widget)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.addWidget(self._line_edit)

            self._layout.addWidget(self._label, 0, 0)
            self._layout.addWidget(h_widget, 1, 0)
            self._layout.addWidget(self._plot_btn, 2, 0)
            self._layout.addItem(QSpacerItem(0, 0, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum), 1, 1)

        self.set_value(None)

        # The Analog input object that is in charge of this button
        self._AI = None

    # Setting and getting methods for the Digitl Out object in charge of this button
    def set_AI(self, AI, notify_old_AI=True, notify_new_AI=True):
        # If we are setting a new AO, remove this widget from the old one (if it isn't None) and add it to the new one (if it isn't None)
        if AI != self._AI:
            if self._AI is not None and notify_old_AI:
                self._AI.remove_widget(self, False)
            if AI is not None and notify_new_AI:
                AI.add_widget(self)
        # Store a reference to the digital out object
        self._AI = AI

    def get_AI(self):
        return self._AI

    @inmain_decorator(True)
    def set_value(self, value):
        if value is not None:
            text = "%0.4f" % value
        else:
            text = "no value"
        self._line_edit.setText(text)

    def _check_plot_window(self):
        while self.win is not None:
            time.sleep(0.1)
            if self.from_child.get() == "closed":
                self.win = None
                self.to_child = None
                self.from_child = None

    def open_plot_window(self):
        if self.win is None:
            self.win = PlotWindow()
            self.to_child, self.from_child = self.win.start(self._connection_name, self._hardware_name, self._device_name)

            check_plot_window_thread = threading.Thread(target=self._check_plot_window)
            check_plot_window_thread.daemon = True
            check_plot_window_thread.start()
        else:
            self.to_child.put('focus')


# A simple test!
if __name__ == '__main__':

    qapplication = QApplication(sys.argv)

    window = QWidget()
    layout = QVBoxLayout(window)
    button = AnalogInput('AI1', 'AI1')

    layout.addWidget(button)

    window.show()

    sys.exit(qapplication.exec_())
