#####################################################################
#                                                                   #
# imageoutput.py                                                    #
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

import base64
import sys
import os

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *
from qtutils.qt.QtCore import pyqtSignal as Signal

class BrowseButton(QPushButton):
    def __init__(self, image_output, *args, **kwargs):
        QPushButton.__init__(self, *args, **kwargs)
        self.image_output = image_output
        self.installEventFilter(self)
        self.clicked.connect(self.browse)
        self.last_opened_folder = ""
        
    def browse(self):
        # supported_images = "Image files (*.png *.bmp *.gif *.jpg *.jpeg *.pbm *.pgm *.ppm *.xbm *.xpm)"
        supported_images = "Image files ("
        
        for format in QImageReader.supportedImageFormats():
            supported_images += "*.%s "%format
            
        supported_images = supported_images [:-1]
        supported_images += ")"
        
        image_file = QFileDialog.getOpenFileName(self, 'Select image file to load', self.last_opened_folder, supported_images)
        if type(image_file) is tuple:
            image_file, _ = image_file
        if image_file == None or image_file == "":
            return
        image_file = os.path.abspath(image_file)
        if not os.path.exists(image_file):
            return 
            
        self.last_opened_folder = os.path.dirname(image_file)
        
        # read the file
        raw_data = u''
        with open(image_file, 'rb') as f:
            raw_data = f.read()

        
        data = base64.b64encode(raw_data)
        
        self.image_output.value = data
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.addAction("Lock" if not self.image_output.lock_state else "Unlock")
            menu.triggered.connect(self.image_output._menu_triggered)
            menu.popup(self.mapToGlobal(event.pos()))
            return True
            
        return QPushButton.eventFilter(self, obj, event)
    
    
class ImageView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        QGraphicsView.__init__(self, *args, **kwargs)
        self.installEventFilter(self)
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Lock" if not self.parent().lock_state else "Unlock")
        menu.triggered.connect(self.parent()._menu_triggered)
        menu.popup(self.mapToGlobal(event.pos()))
        
    
    # def eventFilter(self, obj, event):
        # if event.type() == QEvent.ContextMenu:
            # print 'a'
            # menu = QMenu(self)
            # menu.addAction("Lock" if self.parent().lock_state else "Unlock")
            # menu.triggered.connect(self.parent()._menu_triggered)
            # menu.popup(self.mapToGlobal(event.pos()))
            # return True
            
        # return QGraphicsView.eventFilter(self, obj, event)
    
    
class ImageOutput(QWidget):
    
    imageUpdated = Signal(str)

    def __init__(self, name, width, height, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)        
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        
        
        # create the layout
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a layout for the header of this ImageOutput widget
        header_widget = QWidget(self)
        header_layout = QHBoxLayout(header_widget)        
        
        # Add the label
        self._label = QLabel(name)
        header_layout.addWidget(self._label)
        
        # Add the browse button
        self._browse_button = BrowseButton(self, 'Select Image')
        self._browse_button.setIcon(QIcon(':/qtutils/fugue/image-import'))
        header_layout.addWidget(self._browse_button)
       
        # Add a spacer item to keep everything bunched
        header_layout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum))
        
        # add the header widget to the layout
        self._layout.addWidget(header_widget)
        
        self.image_size = QSize(width,height)
        
        # Create the graphics scene and view
        self._scene = QGraphicsScene(0, 0, width, height)
        self._scene.setBackgroundBrush(Qt.black)
        self._view = ImageView(self._scene)
        self._view.setAlignment(Qt.AlignLeft | Qt.AlignTop)        
        self._view.setStyleSheet("border: 0px")
        # self._view.setStyleSheet("background-color:#000000; border: 0px;")
        self._view.setMinimumSize(self.image_size)
        self._view.setMaximumSize(self.image_size)
        self._layout.addWidget(self._view)
        
        # Install the event filter that will allow us to catch right click mouse release events so we can popup a menu even when the button is disabled
        self.installEventFilter(self)
        
        # The Image Out object that is in charge of this button
        self._Image = None
        
        # the base64encoded value
        self._value = str("")
        
        # The image item to be added to the scene
        self._pixmap_item = None
        
        # The current lock state
        self.lock_state = False
    
    # Setting and getting methods for the Image Out object in charge of this button
    def set_Image(self,Image,notify_old_Image=True,notify_new_Image=True):
        # If we are setting a new Image, remove this widget from the old one (if it isn't None) and add it to the new one (if it isn't None)
        if Image != self._Image:
            if self._Image is not None and notify_old_Image:
                self._Image.remove_widget(self)
            if Image is not None and notify_new_Image:
                Image.add_widget(self)
        # Store a reference to the Image out object
        self._Image = Image
        
    def get_Image(self):
        return self._Image
    
    # The event filter that pops up a context menu on a right click, even when the button is disabled
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.addAction("Lock" if not self.lock_state else "Unlock")
            menu.triggered.connect(self._menu_triggered)
            menu.popup(self.mapToGlobal(event.pos()))
            return True
        
        # pass scrollwheel events of disabled buttons through to the parent
        # code adapted from: http://www.qtforum.org/article/28540/disabled-widgets-and-wheel-events.html
        elif obj and not obj.isEnabled() and event.type() == QEvent.Wheel:
            newEvent = QWheelEvent(obj.mapToParent(event.pos()), event.globalPos(),
                                   event.delta(), event.buttons(),
                                   event.modifiers(), event.orientation())
            QApplication.instance().postEvent(obj.parent(), newEvent)
            return True
        
        return QWidget.eventFilter(self, obj, event)
     
    # This method is called whenever an entry in the context menu is clicked
    def _menu_triggered(self,action):
        if action.text() == "Lock":
            self.lock()
        elif action.text() == "Unlock":
            self.unlock()
    
    # This method locks (disables) the widget, and if the widget has a parent Image object, notifies it of the lock
    def lock(self,notify_Image=True):        
        self._browse_button.setEnabled(False)
        self.lock_state = True
        if self._Image is not None and notify_Image:
            self._Image.lock()
    
    # This method unlocks (enables) the widget, and if the widget has a parent Image object, notifies it of the unlock    
    def unlock(self,notify_Image=True): 
        self._browse_button.setEnabled(True)
        self.lock_state = False
        if self._Image is not None and notify_Image:
            self._Image.unlock()
        
    @property
    def value(self):
        return str(self._value)
        
    @value.setter
    def value(self, value):
        decoded_image = base64.b64decode(str(value))
        pixmap = QPixmap()
        pixmap.loadFromData(decoded_image, flags=Qt.AvoidDither | Qt.ThresholdAlphaDither | Qt.ThresholdDither)
        # print decoded_image
        if pixmap.size() != self.image_size:
            QMessageBox.warning(self, "Failed to load image", 'The image size was incorrect. It must be %dx%d pixels.'%(self.image_size.width(), self.image_size.height()), QMessageBox.Ok, QMessageBox.Ok)
            return
        
        self._value = str(value)
        pixmap_item = QGraphicsPixmapItem(pixmap)
        
        if self._pixmap_item is not None:
            self._scene.removeItem(self._pixmap_item)
        self._scene.addItem(pixmap_item)
        self._pixmap_item = pixmap_item
        
        # Tell the Image object that the value has been updated
        self.imageUpdated.emit(self._value)
    
    
# A simple test!
if __name__ == '__main__':
    
    qapplication = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    button = ImageOutput('hello', 200, 200)
        
    layout.addWidget(button)
    
    window.show()
    
    
    sys.exit(qapplication.exec_())
    