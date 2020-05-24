#####################################################################
#                                                                   #
# enumcontrol.py                                                    #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
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


class EnumOutput(QWidget):
    def __init__(self, hardware_name, connection_name='-', display_name=None, horizontal_alignment=False, parent=None):
        QWidget.__init__(self,parent)
        
        self._connection_name = connection_name
        self._hardware_name = hardware_name
        
        label_text = (self._hardware_name + '\n' + self._connection_name) if display_name is None else display_name
        self._label = QLabel(label_text)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Minimum)
        self._combobox = QComboBox()
        self._combobox.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum)

        self._value_changed_function = None
        
        self.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
        
        # Lock/Unlock action        
        self._lock_action = QAction("Lock",self._combobox)
        self._lock_action.triggered.connect(lambda:self._menu_triggered(self._lock_action))

        # Create widgets and layouts        
        if horizontal_alignment:
            self._layout = QHBoxLayout(self)
            self._layout.addWidget(self._label)
            self._layout.addWidget(self._combobox)
            self._layout.setContentsMargins(0,0,0,0)
        else:
            self._layout = QGridLayout(self)
            self._layout.setVerticalSpacing(3)
            self._layout.setHorizontalSpacing(0)
            self._layout.setContentsMargins(3,3,3,3)
            
            self._label.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
            
            h_widget = QWidget()            
            h_layout = QHBoxLayout(h_widget)
            h_layout.setContentsMargins(0,0,0,0)
            h_layout.addWidget(self._combobox)
            
            self._layout.addWidget(self._label,0,0)
            self._layout.addWidget(h_widget,1,0)            
            self._layout.addItem(QSpacerItem(0,0,QSizePolicy.Minimum,QSizePolicy.MinimumExpanding),2,0)
        
        
        # Install the event filter that will allow us to catch right click mouse release events so we can popup a menu even when the button is disabled
        self.installEventFilter(self)
        
        # The Analog Out object that is in charge of this button
        self._EO = None
    
    # Setting and getting methods for the object in charge of this button
    def set_EO(self,EO,notify_old_EO=True,notify_new_EO=True):
        # If we are setting a new EO, remove this widget from the old one (if it isn't None) and add it to the new one (if it isn't None)
        if EO != self._EO:
            if self._EO is not None and notify_old_EO:
                self._EO.remove_widget(self,False)
            if EO is not None and notify_new_EO:
                EO.add_widget(self)
        # Store a reference to the digital out object
        self._EO = EO
        
    def get_EO(self):
        return self._EO
    
    def set_combobox_model(self,model):
        self._combobox.setModel(model)

    def connect_value_change(self,func):
        self._value_changed_function = func
        self._combobox.currentTextChanged.connect(self._value_changed_function)
        
    def disconnect_value_change(self):
        self._combobox.currentTextChanged.disconnect(self._value_changed_function)
    
    @property
    def selected_option(self):
        return str(self._combobox.currentText())
    
    @selected_option.setter
    def selected_option(self,option):
        if option != self.selected_option:
            #item = self._combobox.model().findItems(option)
            model_index = self._combobox.findText(option)
            if model_index != -1:
                #model_index = self._combobox.model().indexFromItem(item[0]).row()
                self._combobox.setCurrentIndex(model_index)

    @property
    def selected_index(self):
        return self._combobox.currentData(Qt.UserRole)

    @selected_index.setter
    def selected_index(self,index):
        if index != self.selected_index:
            model_index = self._combobox.findData(index,Qt.UserRole)
            if model_index != -1:
                self._combobox.setCurrentIndex(model_index)
            else:
                raise RuntimeError('Index {index} not found!'.format(index=index))

    def block_combobox_signals(self):
        return self._combobox.blockSignals(True)
        
    def unblock_combobox_signals(self):
        return self._combobox.blockSignals(False)
    
    # The event filter that pops up a context menu on a right click, even when the button is disabled
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.addAction("Lock" if self._combobox.isEnabled() else "Unlock")
            menu.triggered.connect(self._menu_triggered)
            menu.popup(self.mapToGlobal(event.pos()))
        
        # pass scrollwheel events of disabled buttons through to the parent
        # code adapted from: http://www.qtforum.org/article/28540/disabled-widgets-and-wheel-events.html
        elif obj and not obj.isEnabled() and event.type() == QEvent.Wheel and QT_ENV != PYQT5:
            newEvent = QWheelEvent(obj.mapToParent(event.pos()), event.globalPos(),
                                   event.delta(), event.buttons(),
                                   event.modifiers(), event.orientation())
            QApplication.instance().postEvent(obj.parent(), newEvent)
            return True
        
        return QPushButton.eventFilter(self, obj, event)
     
    # This method is called whenever an entry in the context menu is clicked
    def _menu_triggered(self,action):
        if action.text() == "Lock":
            self.lock()
        elif action.text() == "Unlock":
            self.unlock()
    
    # This method locks (disables) the widget, and if the widget has a parent EO object, notifies it of the lock
    def lock(self,notify_eo=True):        
        self._combobox.setEnabled(False)
        self._lock_action.setText("Unlock")
        if self._EO is not None and notify_eo:
            self._EO.lock()
    
    # This method unlocks (enables) the widget, and if the widget has a parent EO object, notifies it of the unlock    
    def unlock(self,notify_eo=True):        
        self._combobox.setEnabled(True)        
        self._lock_action.setText("Lock")
        if self._EO is not None and notify_eo:
            self._EO.unlock()

    
# A simple test!
if __name__ == '__main__':
    
    qapplication = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)

    test_options = {'option 1':{'index':0,'tooltip':"Option 1 Description"},
                    'option 2':{'index':1,'tooltip':"Option 2 Description"},
                    'option 3':2}
    test_model = QStandardItemModel()
    for key,val in test_options.items():
        item = QStandardItem(key)
        if type(val) != dict:
            item.setData(val,Qt.UserRole)
        else:
            item.setData(val['index'],Qt.UserRole)
            item.setData(val['tooltip'],Qt.ToolTipRole)
        test_model.appendRow(item)
    combobox = EnumOutput('Enumerate',display_name='Test Name',
                            horizontal_alignment=True)        
    layout.addWidget(combobox)
    combobox.set_combobox_model(test_model)
    
    window.show()
    
    
    sys.exit(qapplication.exec_())
    
