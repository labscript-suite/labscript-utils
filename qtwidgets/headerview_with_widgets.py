from __future__ import division

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSignal as Signal

class HeaderViewWithWidgets(QtGui.QHeaderView):
    """A QHeaderView that supports inserting arbitrary
    widgets into sections. Use setWidget(logical_index, widget)
    to set and setWidget(logical_index, None) to unset."""
    def __init__(self, model, orientation, parent=None):
        self.widgets = {}
        self.model = model
        QtGui.QHeaderView.__init__(self, orientation, parent)
        self.setDefaultAlignment(QtCore.Qt.AlignLeft)
        self.sectionMoved.connect(self.update_widget_positions)
        self.sectionResized.connect(self.update_widget_positions)
        self.geometriesChanged.connect(self.update_widget_positions)
        self.sectionCountChanged.connect(self.update_widget_positions)
        self.model.columnsInserted.connect(self.on_columnsInserted)
        self.model.columnsRemoved.connect(self.on_columnsRemoved)
        self.setMovable(True)
    
    def viewportEvent(self, event):
        if event.type() == QtCore.QEvent.Paint:
            self.update_widget_positions()
        return QtGui.QHeaderView.viewportEvent(self, event)
        
    def setWidget(self, logical_index, widget=None):
        if widget is None:
            if logical_index in self.widgets:
                widget = self.widgets[logical_index]
                widget.setParent(None)
                del self.widgets[logical_index]
                widget.removeEventFilter(self)
        else:
            self.widgets[logical_index] = widget
            widget.setParent(self)
            widget.installEventFilter(self)
        self.update_widget_positions()
     
    def showEvent(self, event):
        self.update_widget_positions()
        return QtGui.QHeaderView.showEvent(self, event)
        
    def sectionSizeFromContents(self, logical_index):
        base_size = QtGui.QHeaderView.sectionSizeFromContents(self, logical_index)
        width, height = base_size.width(), base_size.height()
        if logical_index in self.widgets:
            widget_size = self.widgets[logical_index].sizeHint()
            widget_width, widget_height = widget_size.width(), widget_size.height()
            width += widget_width + 3
            height = max(height, widget_height + 2)
        return QtCore.QSize(width, height)
    
    def paintSection(self, painter, rect, logical_index):
        if logical_index in self.widgets:
            widget = self.widgets[logical_index]
            option = QtGui.QStyleOptionHeader()
            self.initStyleOption(option)
            option.rect = rect
            self.style().drawControl(QtGui.QStyle.CE_Header, option, painter, self)
            rect.setLeft(rect.left() + widget.sizeHint().width() + 3)
        return QtGui.QHeaderView.paintSection(self, painter, rect, logical_index)
    
    def update_widget_positions(self):
        visible_indices = set()
        for visual_index in range(self.count()):
            logical_index = self.logicalIndex(visual_index)
            visible_indices.add(logical_index)
            if logical_index in self.widgets:
                widget = self.widgets[logical_index]
                if not self.isSectionHidden(logical_index) and not widget.isVisible():
                    widget.show()
                elif self.isSectionHidden(logical_index) and widget.isVisible():
                    widget.hide()
                section_position = self.sectionViewportPosition(logical_index)
                section_size = self.sectionSizeFromContents(logical_index)
                widget_size = widget.sizeHint()
                widget_width, widget_height = widget_size.width(), widget_size.height()
                widget_target_x = section_position + 3
                widget_target_y =(section_size.height() - widget_height)//2 - 1
                widget_current_pos = widget.pos()
                widget_current_x, widget_current_y = widget_current_pos.x(), widget_current_pos.y() 
                if (widget_target_x, widget_target_y) != (widget_current_x, widget_current_y):
                    widget.move(widget_target_x , widget_target_y)
            
    def eventFilter(self, target, event):
        """Ensure we don't leave the curor set as a resize
        handle when the mouse moves onto a child widget:"""
        if event.type() == QtCore.QEvent.Enter:
            self.unsetCursor()
        return False
    
    def on_columnsInserted(self, parent, logical_first, logical_last):
        n_inserted = logical_last - logical_first + 1
        widgets_with_offset = {}
        for logical_index, widget in self.widgets.items():
            if logical_index < logical_first:
                widgets_with_offset[logical_index] = widget
            else:
                widgets_with_offset[logical_index + n_inserted] = widget
        self.widgets = widgets_with_offset
        self.update_widget_positions()
        
    def on_columnsRemoved(self, parent, logical_first, logical_last):
        n_removed = logical_last - logical_first + 1
        widgets_with_offset = {}
        for logical_index, widget in self.widgets.items():
            if logical_index < logical_first:
                widgets_with_offset[logical_index] = widget
            elif logical_index <= logical_last:
                self.setWidget(logical_index, None)
            else:
                widgets_with_offset[logical_index - n_removed] = widget
        self.widgets = widgets_with_offset
        self.update_widget_positions()
        
        
if __name__ == '__main__':

    import sys
    import qtutils.icons
    
    class TestApp(object):
        def __init__(self):
            self.window = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(self.window)
            self.model = QtGui.QStandardItemModel()
            self.treeview = QtGui.QTreeView(self.window)
            self.header = HeaderViewWithWidgets(self.model, QtCore.Qt.Horizontal)
            
            self.model.setHorizontalHeaderLabels(['Delete', 'Name', 'Value', 'Units', 'Expansion'])
            self.button = QtGui.QCheckBox()
            #self.button.setIcon(QtGui.QIcon(':qtutils/fugue/ui-check-box'))
            
            self.button2 = QtGui.QToolButton()
            self.button2.setIcon(QtGui.QIcon(':qtutils/fugue/plus'))
            
            self.button3 = QtGui.QToolButton()
            self.button3.setIcon(QtGui.QIcon(':qtutils/fugue/minus'))
            
            self.header.setWidget(0, self.button)
            self.header.setWidget(1, self.button2)
            self.header.setWidget(2, self.button3)
            #self.header.setWidget(0, None)
            self.treeview.setHeader(self.header)
            self.treeview.setModel(self.model)
            #self.header.hideSection(2)
            
            layout.addWidget(self.treeview)
            
            self.model.insertColumn(2,[QtGui.QStandardItem('test')])
            self.window.show()
        
    qapplication = QtGui.QApplication(sys.argv)
    qapplication.setAttribute(QtCore.Qt.AA_DontShowIconsInMenus, False)
    app = TestApp()
    qapplication.exec_()
    
    