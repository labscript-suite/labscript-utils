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

# from PyQt5.QtGui import *
# from PyQt5.QtCore import *
# from PyQt5.QtWidgets import *


class debug(object):
    DEBUG = False
    depth = 0
    @classmethod
    def trace(cls, f):
        """decorator to print function entries and exits"""
        if not cls.DEBUG:
            return f
        def wrapper(*args, **kwargs):
            print('    '*cls.depth + '->', f.__name__)
            try:
                cls.depth += 1
                return f(*args, **kwargs)
            finally:
                cls.depth -= 1
                print('    '*cls.depth + '<-', f.__name__)
        return wrapper


if debug.DEBUG:
    import sys
    print('sys.version:', sys.version)
    print('PyQt4:', 'PyQt4' in sys.modules)
    print('PyQt5:', 'PyQt5' in sys.modules)
    print('PySide:', 'PySide' in sys.modules)
    print('qtutils:', 'qtutils' in sys.modules)
    print('qtutils.qt:', 'qtutils.qt' in sys.modules)



Tab = namedtuple('Tab', ['widget', 'text', 'data', 'text_color', 'tooltip',
                         'whats_this', 'button_left', 'button_right', 'icon'])


class _BaseDragDropTabBar(QTabBar):
    """Base class for Limbo and DragDropTabBar containing the common add and
    remove methods"""

    # The QPoint of the mouse relative to the top left corner the tab at the
    # time the drag began. Shared by all instances:
    _dragged_tab_grab_point = None

    @property
    def dragged_tab_grab_point(self):
        return self._dragged_tab_grab_point

    @dragged_tab_grab_point.setter
    def dragged_tab_grab_point(self, value):
        # Setter specifies the class because we want subclasses to all share
        # it:
        _BaseDragDropTabBar._dragged_tab_grab_point = value

    @debug.trace
    def remove_dragged_tab(self, index):
        """Remove the tab at the given index and return all its configuration"""

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

    @debug.trace
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


class _Limbo(_BaseDragDropTabBar):
    """A floating TabBar to be the parent of the tab when it is not in a
    DragDropTabBar"""
    def __init__(self):
        self.parent_tabwidget = QTabWidget()
        QTabBar.__init__(self, self.parent_tabwidget)
        self.parent_tabwidget.setTabBar(self)
        self.previous_parent = None
        self.previous_index = None
        self.prev_active_tab = None
        self.setWindowFlags(Qt.ToolTip)
        self.setUsesScrollButtons(False)

    @debug.trace
    def remove_dragged_tab(self, index):
        result = _BaseDragDropTabBar.remove_dragged_tab(self, index)
        self.hide()
        return result

    @debug.trace
    def add_dragged_tab(self, index, tab):
        result = _BaseDragDropTabBar.add_dragged_tab(self, index, tab)
        self.show()
        return result

    @debug.trace
    def update_tab_index(self, index, pos):
        """We only have one tab index, so it's not going to change."""
        return index

    @debug.trace
    def tabLayoutChange(self):
        initial_size = self.size()
        if self.count():
            self.resize(self.tabSizeHint(0))
        self.update_pos()

    @debug.trace
    def update_pos(self):
        """Move to keep the tab grabbed by the mouse. grab_point is the
        position on the tab relative to its top left corner where it is
        grabbed by the mouse. Use current mouse position rather than that
        associated with any event triggering this, for maximal
        responsiveness."""
        QWidget.move(self, QCursor.pos() - self.dragged_tab_grab_point)


class DragDropTabBar(_BaseDragDropTabBar):

    # Keeping track of which tab widgets are in each group (that is, share a
    # common group_id):
    tab_widgets = defaultdict(weakref.WeakSet)

    # Whether or not a drag is in progress. It is important to have this in
    # addition to the below information so that we can set it to False when a
    # drag is about to be cancelled, even though we are not going to set the
    # below variables to None until after some processing. During that
    # processing, re-entrant event processing can see that there is no drag in
    # progress even though the below variables are still not None, and know
    # not to act as if there is a drag in progress (since the drag is in the
    # process of being cancelled).
    _drag_in_progress = False

    # The index and parent TabBar of the dragged tab, or None if no drag is in
    # progress. Shared by all instances:
    _dragged_tab_index = None
    _dragged_tab_parent = None

    # A TabWidget to hold the tab being dragged. Shared by all instsances, but
    # not instantiated until first instance is created, since there may not be
    # a QApplication at import time.
    limbo = None

    def __init__(self, parent, group_id):
        QTabBar.__init__(self, parent)

        self.group_id = group_id
        self.tab_widgets[group_id].add(self.parent())

        self.prev_active_tab = None
        if self.limbo is None:
            # One Limbo object for all instances:
            self.__class__.limbo = _Limbo()

    # Setters and getters for the class variables:
    @property
    def drag_in_progress(self):
        return self._drag_in_progress

    @drag_in_progress.setter
    def drag_in_progress(self, value):
        self.__class__._drag_in_progress = value

    @property
    def dragged_tab_index(self):
        return self._dragged_tab_index

    @dragged_tab_index.setter
    def dragged_tab_index(self, value):
        self.__class__._dragged_tab_index = value

    @property
    def dragged_tab_parent(self):
        return self._dragged_tab_parent

    @dragged_tab_parent.setter
    def dragged_tab_parent(self, value):
        self.__class__._dragged_tab_parent = value

    @debug.trace
    def moveTab(self, source_index, dest_index):
        """Move tab fron one index to another. Overriding this is not
        necessary in PyQt5, the base implementation works fine. But there
        seems to be a bug in PyQt4 which temporarily shows the wrong page
        (though the right tab is active) after a moveTab,---at least, when
        it's called like we call it during the processing of a mouseMoveEvent.
        Simply removing the tab and re-adding it at the new index results in
        the correct page. This method can be removed once PyQt4 support is
        dropped."""
        tab = self.remove_dragged_tab(source_index)
        self.add_dragged_tab(dest_index, tab)

    @debug.trace
    def set_tab_parent(self, dest, index=0):
        """Move the tab to the given parent DragDropTabBar if it's not already
        there. The index argument will only be used if the tab is not already
        in the widget (the index is used for restoring a tab to its last known
        position in a tab bar, which is not needed if it is already there)."""
        if self.dragged_tab_parent != dest:
            tab = self.dragged_tab_parent.remove_dragged_tab(self.dragged_tab_index)
            dest.add_dragged_tab(index, tab)
            if dest is self.limbo:
                self.limbo.previous_parent = self.dragged_tab_parent
                self.limbo.previous_index = self.dragged_tab_index
            self.dragged_tab_parent = dest
            self.dragged_tab_index = index

    @debug.trace
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

    @debug.trace
    def widgetAt(self, pos):
        """If the given position is over a DragDropTabBar belonging to the
        current group, return the DragDropTabBar. If it is over a TabWidget in
        the same group that has no tabs, or the dragged tab as its only tab,
        return its DragDropTabBar. Otherwise return the limbo object."""
        for tab_widget in self.tab_widgets[self.group_id]:
            count = tab_widget.tabBar().count()
            if count == 0 or (count == 1 and self.dragged_tab_parent is tab_widget.tabBar()):
                widget = tab_widget
                rect = widget.rect()
            else:
                widget = tab_widget.tabBar()
                rect = widget.rect()
                # Include the whole horizontal part of the tabBar:
                rect.setLeft(widget.parent().rect().left())
                rect.setRight(widget.parent().rect().right())
            other_local_pos = widget.mapFromGlobal(self.mapToGlobal(pos))
            if rect.contains(other_local_pos):
                return tab_widget.tabBar()
        else:
            return self.limbo

    @debug.trace
    def mousePressEvent(self, event):
        """Take note of the tab that was clicked so it can be dragged on
        mouseMoveEvents"""
        QTabBar.mousePressEvent(self, event)
        if event.button() != Qt.LeftButton:
            return
        event.accept()
        self.drag_in_progress = True
        self.dragged_tab_index = self.tabAt(event.pos())
        self.dragged_tab_parent = self
        self.dragged_tab_grab_point = event.pos() - self.tabRect(self.dragged_tab_index).topLeft()
        
    @debug.trace
    def mouseMoveEvent(self, event):
        """Update the parent of the tab to be the DragDropTabWidget under the
        mouse, if any, otherwise update it to the limbo object. Update the
        position of the tab in the widget it's in."""
        QTabBar.mouseMoveEvent(self, event)
        if not self.drag_in_progress:
            return
        event.accept()
        if self.group_id is not None:
            widget = self.widgetAt(event.pos())
            self.set_tab_parent(widget)
        other_local_pos = widget.mapFromGlobal(self.mapToGlobal(event.pos()))
        self.dragged_tab_index = widget.update_tab_index(self.dragged_tab_index,
                                                         other_local_pos)
        if self.dragged_tab_parent is self.limbo:
            # Update the position of the dragged tab following the mouse:
            self.limbo.update_pos()
        else:
            # The tab is in a TabBar. Tell its parent tab widget to
            # repaint to show the new position:
            self.dragged_tab_parent.parent().update()

    @debug.trace
    def leaveEvent(self, event):
        QTabBar.leaveEvent(self, event)
        """Called if the window loses focus"""
        if not self.drag_in_progress:
            return
        # We've lost focus during a drag. Cancel the drag.
        self.drag_in_progress = False
        if self.dragged_tab_parent is self.limbo:
            self.set_tab_parent(self.limbo.previous_parent, self.limbo.previous_index)        
        # Clear the variables about which tab is being dragged:
        self.dragged_tab_index = None
        self.dragged_tab_parent = None
        self.dragged_tab_grab_point = None

    @debug.trace
    def mouseReleaseEvent(self, event):
        """Same as mouseMove event - update the DragDropTabWidget and position of
        the tab to the current mouse position. Unless the mouse position is
        outside of any widgets at the time of mouse release, in which case
        move the tab to its last known parent and position."""
        QTabBar.mouseReleaseEvent(self, event)
        if self.dragged_tab_index is None or event.button() != Qt.LeftButton:
            return
        event.accept()
        # Cancel the drag:
        self.drag_in_progress = False
        widget = self.widgetAt(event.pos())
        # If the tab and the mouse are both in limbo, then put the tab
        # back at its last known place:
        if widget is self.limbo and self.dragged_tab_parent is self.limbo:
            self.set_tab_parent(self.limbo.previous_parent, self.limbo.previous_index)
        # But if we're above a tab widget, put it there. Otherwise leave it
        # where it is (don't move it into limbo)
        elif widget is not self.limbo:
            if self.group_id is not None:
                self.set_tab_parent(widget)
            other_local_pos = widget.mapFromGlobal(self.mapToGlobal(event.pos()))
            widget.update_tab_index(self.dragged_tab_index, other_local_pos)
        # Clear the variables about which tab is being dragged:
        self.dragged_tab_index = None
        self.dragged_tab_parent = None
        self.dragged_tab_grab_point = None


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
    
    timer = QTimer()
    timer.start(500)

    import time

    def change_text():
        if DragDropTabBar.limbo is not None:
            limbo = DragDropTabBar.limbo
            if limbo.count():
                limbo.setTabText(0, str(time.time()))
    timer.timeout.connect(change_text)  # Let the interpreter run each 500 ms.
    qapplication.exec_()
