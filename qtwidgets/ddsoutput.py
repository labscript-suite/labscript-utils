#####################################################################
#                                                                   #
# ddsoutput.py                                                      #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import

import sys

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *

from labscript_utils.qtwidgets.analogoutput import AnalogOutput
from labscript_utils.qtwidgets.digitaloutput import DigitalOutput

class DDSOutput(QWidget):
    def __init__(self, hardware_name, connection_name='-', parent=None):
        QWidget.__init__(self,parent)
        
        self._connection_name = connection_name
        self._hardware_name = hardware_name
        
        label_text = (self._hardware_name + '\n' + self._connection_name) 
        self._label = QLabel(label_text)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
        
        
        self.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
        
        # Create widgets
        self._widgets = {}
        self._widgets['gate'] = DigitalOutput('Enable')
        self._widgets['freq'] = AnalogOutput('',display_name='<i>f&nbsp;</i>', horizontal_alignment=True)
        self._widgets['amp'] = AnalogOutput('',display_name='<i>A</i>', horizontal_alignment=True)
        self._widgets['phase'] = AnalogOutput('',display_name=u'<i>&phi;</i>', horizontal_alignment=True)
        
        # Extra layout at the top level with horizontal stretches so that our
        # widgets do not grow to take up all available horizontal space:
        self._outer_layout = QHBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        # self._layout.setHorizontalSpacing(3)
        self._frame = QFrame(self)
        self._outer_layout.addStretch()
        self._outer_layout.addWidget(self._frame)
        self._outer_layout.addStretch()

        # Create grid layout that keeps widgets from expanding and keeps label centred above the widgets
        self._layout = QGridLayout(self._frame)
        self._layout.setVerticalSpacing(6)
        self._layout.setHorizontalSpacing(0)
        self._layout.setContentsMargins(0,0,0,0)
        
        v_widget = QFrame()
        v_widget.setFrameStyle(QFrame.StyledPanel)            
        v_layout = QVBoxLayout(v_widget)
        v_layout.setContentsMargins(6,6,6,6)

        # Extra widget with stretches around the enabled button so it doesn't
        # stretch out to fill all horizontal space:
        self.gate_container = QWidget()
        gate_layout = QHBoxLayout(self.gate_container)
        gate_layout.setContentsMargins(0,0,0,0)
        gate_layout.setSpacing(0)
        gate_layout.addStretch()
        gate_layout.addWidget(self._widgets['gate'])
        gate_layout.addStretch()

        self._widgets['gate'].setToolTip("Enable")
        self._widgets['freq'].setToolTip("Frequency")
        self._widgets['amp'].setToolTip("Amplitude")
        self._widgets['phase'].setToolTip("Phase")

        v_layout.addWidget(self.gate_container)
        v_layout.addWidget(self._widgets['freq'])
        v_layout.addWidget(self._widgets['amp'])
        v_layout.addWidget(self._widgets['phase'])
        
        self._layout.addWidget(self._label,0,0)
        #self._layout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum),0,1)
        self._layout.addWidget(v_widget,1,0)            
        #self._layout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum),1,1)
        self._layout.addItem(QSpacerItem(0,0,QSizePolicy.Minimum,QSizePolicy.MinimumExpanding),2,0)
        
        
    def get_sub_widget(self,subchnl):
        if subchnl in self._widgets:
            return self._widgets[subchnl]
        
        raise RuntimeError('The sub-channel %s must be either gate, freq, amp or phase'%subchnl)
        
    def hide_sub_widget(self,subchnl):
        if subchnl in self._widgets:
            if subchnl == 'gate':
                self.gate_container.hide()
            else:
                self._widgets[subchnl].hide()
            return
        
        raise RuntimeError('The sub-channel %s must be either gate, freq, amp or phase'%subchnl)  
    
    def show_sub_widget(self,subchnl):
        if subchnl in self._widgets:
            if subchnl == 'gate':
                self.gate_container.show()
            else:
                self._widgets[subchnl].show()
            return
        
        raise RuntimeError('The sub-channel %s must be either gate, freq, amp or phase'%subchnl)
        
# A simple test!
if __name__ == '__main__':
    
    qapplication = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    button = DDSOutput('DDS1')
        
    layout.addWidget(button)
    
    window.show()
    
    
    sys.exit(qapplication.exec_())
    