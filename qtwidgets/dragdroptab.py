#####################################################################
#                                                                   #
# dragdroptab.py                                                    #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

from __future__ import print_function

import weakref
from collections import namedtuple, defaultdict


try:
    from qtutils.qt.QtGui import *
    from qtutils.qt.QtWidgets import *
    from qtutils.qt.QtCore import *
except Exception:
    # Can remove this once labscript_utils is ported to qtutils v2
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *


class limbo(object):
    """an object to be the parent of the tab when it is not in a QTabWidget"""
    tab = None
    previous_parent = None
    previous_index = None

    @classmethod
    def add_dragged_tab(cls, index, tab):
        assert cls.tab is None
        cls.tab = tab
        # TODO: Make the mouse change into a drag indicator of sorts until
        # remove_dragged_tab() called.

    @classmethod
    def remove_dragged_tab(cls, index):
        tab = cls.tab
        cls.tab = None
        return tab

    @classmethod
    def update_tab_index(cls, index, pos):
        """We only have one tab index, so it's not going to change."""
        return index

    @classmethod
    def mapFromGlobal(self, point):
        """We don't care about coordinates, anything is fine by us!"""
        return point

Tab = namedtuple('Tab', ['widget', 'text', 'data', 'text_color', 'tooltip',
                         'whats_this', 'button_left', 'button_right', 'icon'])


class DragDropTabBar(QTabBar):

    tab_widgets = defaultdict(weakref.WeakSet)

    def __init__(self, parent, group_id):
        QTabBar.__init__(self, parent)

        self.group_id = group_id
        self.tab_widgets[group_id].add(self.parent())

        self.dragged_tab_index = None
        self.dragged_tab_parent = None
        self.prev_active_tab = None


    def remove_dragged_tab(self, index):

        tab = Tab(widget=self.parent().widget(index),
                  text=self.tabText(index),
                  data=self.tabData(index),
                  text_color=self.tabTextColor(index),
                  tooltip=self.tabToolTip(index),
                  whats_this=self.tabWhatsThis(index),
                  button_left=self.tabButton(index, QTabBar.LeftSide),
                  button_right=self.tabButton(index, QTabBar.RightSide),
                  icon=self.tabIcon(index))

        self.parent().removeTab(index)
        if self.prev_active_tab is not None:
            self.setCurrentIndex(self.prev_active_tab)
            self.prev_active_tab = None

        return tab

    def add_dragged_tab(self, index, tab):
        """Insert the tab at the given index and set all of its configuration"""
        self.prev_active_tab = self.currentIndex()

        self.parent().insertTab(index, tab.widget, tab.text)
        self.setCurrentIndex(index)

        if tab.data:
            self.setTabData(index, tab.data)
        self.setTabTextColor(index, tab.text_color)
        if tab.tooltip:
            self.setTabToolTip(index, tab.tooltip)
        if tab.whats_this:
            self.setTabWhatsThis(index, tab.whats_this)
        if tab.button_left:
            self.setTabButton(index, QTabBar.LeftSide, tab.button_left)
        if tab.button_right:
            self.setTabButton(index, QTabBar.RightSide, tab.button_right)
        if tab.icon:
            self.setTabIcon(index, tab.icon)

    def moveTab(self, source_index, dest_index):
        """Move tab fron one index to another. Overriding this is not
        neccesary in PyQt5, the base implementation works fine. But there
        seems to be a bug in PyQt4 which temporarily shows the wrong page
        (though the right tab is active) after a moveTab,---at least, when
        it's called like we call it during the processing of a mouseMoveEvent.
        Simply removing the tab and re-adding it at the new index results in
        the correct page. This method can be removed once PyQt4 support is
        dropped."""
        tab = self.remove_dragged_tab(source_index)
        self.add_dragged_tab(dest_index, tab)

    def set_tab_parent(self, dest, index=0):
        """Move the tab to the given parent DragDropTabBar if it's not already
        there. The index argument will only be used if the tab is not already
        in the widget (the index is used for restoring a tab to its last known
        position in a tab bar, which is not needed if it is already there)."""
        if self.dragged_tab_parent != dest:
            if dest is limbo:
                # Set the mouse cursor to a picture of the tab:
                rect = self.dragged_tab_parent.tabRect(self.dragged_tab_index)
                pixmap = QPixmap(rect.size())
                self.dragged_tab_parent.render(pixmap, QPoint(), QRegion(rect));
                cursor = QCursor(pixmap)
                QApplication.setOverrideCursor(cursor)
            if self.dragged_tab_parent is limbo:
                # Restore the mouse cursor
                QApplication.restoreOverrideCursor()
            tab = self.dragged_tab_parent.remove_dragged_tab(self.dragged_tab_index)
            dest.add_dragged_tab(index, tab)
            if dest is limbo:
                limbo.previous_parent = self.dragged_tab_parent
                limbo.previous_index = self.dragged_tab_index
            self.dragged_tab_parent = dest
            self.dragged_tab_index = index

    def update_tab_index(self, index, pos):
        """Check if the tab at the given index, if being dragged by the mouse
        at the given position, needs to be moved. Move it and return the new
        index."""

        # What's the closest tab to the given position?

        # Consider a point that has the same x position as the given position
        # but is otherwise on the TabBar:
        bar_pos = QPoint(pos.x(), self.rect().bottom())

        # Is there a tab under the point?
        closest_tab = self.tabAt(bar_pos)
        if closest_tab == -1:
            # No there isn't. Are we to the left of the first tab?
            if pos.x() < self.rect().left():
                closest_tab = 0
            else:
                # No? Then we're to the right of the last tab:
                closest_tab = self.count() - 1

        if closest_tab == index:
            # We don't need to move:
            return index

        tab_rect = self.tabRect(index)
        tab_width = tab_rect.width()

        move_target = None
        if closest_tab < index:
            # Mouse is over a tab to the left. Is it far enough to the left
            # that it should be swapped with a tab to the left?
            for other_tab in range(closest_tab, index):
                other_tab_rect = self.tabRect(other_tab)
                other_tab_width = other_tab_rect.width()
                if pos.x() < other_tab_rect.left() + tab_width:
                    move_target = other_tab
                    break
        elif closest_tab > index:
            # Mouse is over a tab to the right. Is it far enough to the right
            # that it should be swapped with a tab to the right?
            for other_tab in range(closest_tab, index, -1):
                other_tab_rect = self.tabRect(other_tab)
                other_tab_width = other_tab_rect.width()
                if pos.x() > other_tab_rect.right() - tab_width:
                    move_target = other_tab
                    break

        if move_target is not None:
            self.moveTab(index, move_target)
            return move_target
        else:
            return index

    def widgetAt(self, pos):
        """If the given position is over a DragDropTabWidget belonging to the
        current group, return its corresponding DragDropTabBar. Otherwise
        return the limbo object."""
        for tab_widget in self.tab_widgets[self.group_id]:
            other_local_pos = tab_widget.mapFromGlobal(self.mapToGlobal(pos))
            if tab_widget.rect().contains(other_local_pos):
                return tab_widget.tabBar()
        else:
            return limbo

    def mousePressEvent(self, event):
        """Take note of the tab that was clicked so it can be dragged on
        mouseMoveEvents"""
        QTabBar.mousePressEvent(self, event)
        event.accept()
        if event.button() == Qt.LeftButton:
            self.dragged_tab_index = self.tabAt(event.pos())
            self.dragged_tab_parent = self
        
    def mouseMoveEvent(self, event):
        """Update the parent of the tab to be the DragDropTabWidget under the
        mouse, if any, otherwise update it to the limbo object. Update the
        position of the tab in the widget it's in."""
        QTabBar.mouseMoveEvent(self, event)
        event.accept()
        if self.group_id is not None:
            widget = self.widgetAt(event.pos())
            self.set_tab_parent(widget)
        other_local_pos = widget.mapFromGlobal(self.mapToGlobal(event.pos()))
        self.dragged_tab_index = widget.update_tab_index(self.dragged_tab_index,
                                                         other_local_pos)

    def mouseReleaseEvent(self, event):
        """Same as mouseMove event - update the DragDropTabWidget and position of
        the tab to the current mouse position. Unless the mouse position is
        outside of any widgets at the time of mouse release, in which case
        move the tab to its last known parent and position."""
        QTabBar.mouseReleaseEvent(self, event)
        event.accept()
        widget = self.widgetAt(event.pos())
        if widget is limbo:
            self.set_tab_parent(limbo.previous_parent, limbo.previous_index)
        else:
            if self.group_id is not None:
                self.set_tab_parent(widget)
            other_local_pos = widget.mapFromGlobal(self.mapToGlobal(event.pos()))
            self.dragged_tab_index = widget.update_tab_index(self.dragged_tab_index,
                                                             other_local_pos)


class DragDropTabWidget(QTabWidget):
    """A tab widget that supports dragging and dropping of tabs between tab
    widgets that share a group_id. a group_id of None indicates that tab
    dragging is disabled."""
    def __init__(self, group_id=None):
        QTabWidget.__init__(self)
        self.setTabBar(DragDropTabBar(self, group_id))
        self.setMovable(False)

    @property
    def tab_bar(self):
        """Backward compatibility for BLACS"""
        return self.tabBar()


if __name__ == '__main__':    
    class ViewPort(object):
        def __init__(self, id, container_layout,i):
            #ui = UiLoader().load('viewport.ui')
            self.tab_widget = DragDropTabWidget(id)
            container_layout.addWidget(self.tab_widget)
            self.tab_widget.addTab(QLabel("foo %d"%i), 'foo')
            self.tab_widget.addTab(QLabel("bar %d"%i), 'bar')
            self.tab_widget.tabBar().setTabTextColor(0, QColor(255, 0, 0))
            self.tab_widget.tabBar().setTabTextColor(1, QColor(0, 255, 0))
            
            
    class RunViewer(object):
        def __init__(self):
            # Load the gui:
            self.moving_tab = None
            self.moving_tab_index = -1
            
            self.window = QWidget()
            container = QVBoxLayout(self.window)
            
            self.viewports = []
            for i in range(3):               
                viewport = ViewPort(3,container,i)
                self.viewports.append(viewport)
            #button = QPushButton("launch iPython")
            #button.clicked.connect(embed)
            #ui.verticalLayout_6.addWidget(button)
            
            self.window.show()
        

    qapplication = QApplication([])
    app = RunViewer()
    qapplication.exec_()