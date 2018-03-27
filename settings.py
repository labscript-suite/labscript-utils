#####################################################################
#                                                                   #
# settings.py                                                       #
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
from labscript_utils import PY2
if PY2:
    str = unicode

try:
    from labscript_utils import check_version
except ImportError:
    raise ImportError('Require labscript_utils > 2.1.0')

check_version('qtutils', '2.0.0', '3.0.0')

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *

import labscript_utils.h5_lock, h5py
from labscript_utils.qtwidgets.fingertab import FingerTabWidget

# Create a generic interface for displaying pages of settings
class Settings(object):
    
    def __init__(self,storage='hdf5',file=None,parent = None,page_classes = []):
        self.pages = {}
        self.instantiated_pages = {}
        self.dialog_open = False
        self.parent = parent
        self.storage = storage
        self.file = file
        self.callback_list = []
        
        if not self.file:
            raise Exception('You must specify a file to load/save preferences from')
        
        for c in page_classes:
            self.add_settings_interface(c)
            
    # This function can be called to add a interface
    # Each one of these will display as a seperate page in the settings window
    # You can not add a class more than once!
    # Classes must have unique Class.name attributes! (This might change later...)
    def add_settings_interface(self,setting_class):
        if setting_class.name in self.pages:
            return False
                   
        self.pages[setting_class.name] = setting_class(self.load(setting_class.name))   
        return True
        
    def load(self,name):
        if self.storage == 'hdf5':
            with h5py.File(self.file,'r+') as h5file: 
                # does the settings group exist?
                if 'preferences' not in h5file:
                    h5file['/'].create_group('preferences')
                    
                # is there an entry for this preference type?
                group = h5file['/preferences']
                if name not in group.attrs:
                    group.attrs[name] = repr({})
                try:
                    data = eval(group.attrs[name])
                except Exception:
                    # TODO: log this properly
                    print('Could not load settings data for %s. It may contain data that could not be evaluated. All settings have now been lost'%name)
                    data = {}
            return data
        else:
            raise Exception("the Settings module cannot handle the storage type: %s"%str(self.storage))
        
    # A simple interface for accessing values in the settings interface
    def get_value(self,settings_class,value_name):
        return self.pages[settings_class.name].get_value(value_name)
        
    # goto_page should be the CLASS which you wish to go to!
    def create_dialog(self,goto_page=None):
        if not self.dialog_open:
            self.instantiated_pages = {}
            
            # Create the dialog
            self.dialog = QDialog(self.parent)
            self.dialog.setModal(True)
            self.dialog.accepted.connect(self.on_save)
            self.dialog.rejected.connect(self.on_cancel)
            self.dialog.setMinimumSize(800,600)
            self.dialog.setWindowTitle("Preferences")
            # Remove the help flag next to the [X] close button
            self.dialog.setWindowFlags(self.dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            
            # Create the layout
            layout = QVBoxLayout(self.dialog)
            #Create the Notebook
            self.notebook = FingerTabWidget(self.dialog)            
            self.notebook.setTabPosition(QTabWidget.West)
            self.notebook.show() 
            layout.addWidget(self.notebook)
            
            # Create the button box
            widget = QWidget()
            hlayout = QHBoxLayout(widget)
            button_box = QDialogButtonBox()
            button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(self.dialog.accept)
            button_box.rejected.connect(self.dialog.reject)
            hlayout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum))
            hlayout.addWidget(button_box)
            layout.addWidget(widget)
            
            #sorted(a.items(),key=lambda x: x[1])
            set_page = None
            #self.temp_pages = []
            for name, c in sorted(self.pages.items()):
                page,icon = c.create_dialog(self.notebook)
                
                # save page
                self.instantiated_pages[c.__class__] = page
                
                # Create label
                #if isinstance(icon,gtk.Image):
                    # use their icon
                #    pass
                #else:
                    # use default icon
                #    pass
                    
                self.notebook.addTab(page,c.name)
                
                if goto_page and isinstance(c,goto_page):
                    # this is the page we want to go to!
                    set_page = page
        
            # We do this here in case one of the settings pages specifically inserts itself in an out of order place (eg first)
            # We hope that everything will be in alphabetical order, but maybe not!
            if set_page:
                self.notebook.tabBar().setCurrentIndex(self.notebook.indexOf(set_page))
                pass
            
            self.dialog.show()
            self.dialog_open = True
        else:
            if goto_page and goto_page in self.instantiated_pages:
                self.notebook.tabBar().setCurrentIndex(self.notebook.indexOf(self.instantiated_pages[goto_page]))
                
    
    def register_callback(self,callback):
        self.callback_list.append(callback)
        
    def remove_callback(self,callback):
        self.callback_list.remove(callback)
    
    def on_save(self,*args,**kwargs):
        # Save the settings
        if self.storage == 'hdf5':
            with h5py.File(self.file,'r+') as h5file:
                group = h5file['/preferences']
                for page in self.pages.values():
                    group.attrs[page.__class__.name] = repr(page.save()) 
        else:
            # this should never happen as the exception will have been raised on load!
            pass
            
        # run callback functions!
        # Notifies other areas of the program that settings have changed
        for callback in self.callback_list:
            callback()
        
        self.close()
            
    def on_cancel(self,*args,**kwargs):
        self.close()
    
    def close(self,*args,**kwargs):
        if self.dialog_open:
            # Close the setting classes
            for page in self.pages.values():
                page.close()   
            self.dialog_open = False
            self.dialog.deleteLater()
            self.dialog = None
