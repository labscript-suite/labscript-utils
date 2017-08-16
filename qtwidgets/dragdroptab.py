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

from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *
from qtutils.qt.QtCore import *


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
    """Base class for Limbo and DragDropTabBar containing the common class
    attributes and  methods"""

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
        _BaseDragDropTabBar.__init__(self, self.parent_tabwidget)
        self.parent_tabwidget.setTabBar(self)
        self.previous_parent = None
        self.previous_index = None
        self.prev_active_tab = None
        self.setWindowFlags(Qt.ToolTip)
        self.setUsesScrollButtons(False)
        # For storing a pixmap to render during animations when we no longer
        # own the tab:
        self.pixmap = None
        self.animation_in_progress = False

    @debug.trace
    def remove_dragged_tab(self, index):
        # Grab a pixmap of our current contents for rendering in case there is
        # animation of the tab flying back to a tab bar:
        self.pixmap = QPixmap(self.size())
        self.render(self.pixmap, QPoint(), QRegion(self.rect()))
        result = _BaseDragDropTabBar.remove_dragged_tab(self, index)
        self.hide()
        return result

    @debug.trace
    def animation_starting(self):
        self.animation_in_progress = True
        self.show()

    @debug.trace
    def animation_over(self):
        if self.animation_in_progress:
            self.pixmap = None
            self.animation_in_progress = False
            self.hide()

    @debug.trace
    def add_dragged_tab(self, index, tab):
        self.animation_over() # cancel any animation in progress
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
        self.update()

    @debug.trace
    def insertion_index_at(self, pos):
        # Only ever insert at zero:
        return 0

    @debug.trace
    def update(self):
        """Move to keep the tab grabbed by the mouse. grab_point is the
        position on the tab relative to its top left corner where it is
        grabbed by the mouse. Use current mouse position rather than that
        associated with any event triggering this, for maximal
        responsiveness."""
        if self.dragged_tab_grab_point is not None:
            self.move(QCursor.pos() - self.dragged_tab_grab_point)
        _BaseDragDropTabBar.update(self)

    @debug.trace
    def paintEvent(self, event):
        if self.animation_in_progress:
            # Just draw the pixmap we've been given
            painter = QPainter(self)
            painter.drawPixmap(QPoint(), self.pixmap)
            painter.end()
        else:
            _BaseDragDropTabBar.paintEvent(self, event)


class TabAnimation(QAbstractAnimation):

    # We move tabs with speed proportional to the distance from their target.

    # Animation timescale - has units of time (milliseconds), but can
    # be thought of as the velocity in pixels per millisecond per pixel of
    # displacement that the object is from its target.
    tau = float(60)

    def __init__(self, parent):
        QAbstractAnimation.__init__(self, parent)
        # The left edges of where the tabs will be drawn. This animates over
        # time to approach the left edge as returned by parent.tabRect().
        self.positions = []
        # The position of the floating limbo tab, if it's in the process of being
        # sucked back into the tab bar that owns this animation object:
        self.limbo_position = None
        self.limbo_target_tab = None
        self.limbo = None
        self.previous_time = 0

        # A flag to set to avoid recursion when we ask widgets to update:
        self.callback_in_progress = False

    @debug.trace
    def duration(self):
        return -1

    @debug.trace
    def ensure_running(self):
        # Don't recurse:
        if self.callback_in_progress:
            return
        if self.state() == QAbstractAnimation.Stopped:
            self.start()

    @debug.trace
    def target(self, i):
        """Return the target position we are animating toward for a tab"""
        return self.parent().tabRect(i).left()

    @debug.trace
    def tabInserted(self, index):
        self.positions.insert(index, self.parent().tabRect(index).left())
        self.ensure_running()

    @debug.trace
    def tabRemoved(self, index):
        del self.positions[index]
        self.ensure_running()

    @debug.trace
    def on_tab_moved(self, source_index, dest_index):
        self.positions.insert(dest_index, self.positions.pop(source_index))
        self.ensure_running()

    @debug.trace
    def animate_limbo(self, limbo, index):
        """If the floating tab in limbo is being sucked back into one of our
        tabs, then we can animate that by hiding the relevant tab rect off to
        the side somwhere whilst the floating tab swoops in."""
        # floating tab doesn't own it anymore.
        self.limbo = limbo
        self.limbo.animation_starting()
        self.limbo_position = self.parent().mapFromGlobal(limbo.pos())
        self.limbo_target_tab = index
        self.ensure_running()

    @debug.trace
    def updateCurrentTime(self, current_time):
        dt = current_time - self.previous_time
        self.previous_time = current_time

        finished = True

        # Move tabs toward their target:
        for i, pos in enumerate(self.positions):
            target_pos = self.target(i)
            dx = target_pos - pos
            # Animate while the tab is more than a pixel away from its target:
            if abs(dx) > 1:
                finished = False
                new_pos = pos + dx * dt / self.tau
                # Check for overshoot:
                if dx * (target_pos - new_pos) < 0:
                    new_pos = target_pos
                self.positions[i] = new_pos
            else:
                # Once it's close enough, snap it to the final value
                self.positions[i] = target_pos

        # move the floating tab toward its target, if applicable:
        if self.limbo is not None:
            pos_x = self.limbo_position.x()
            pos_y = self.limbo_position.y()
            target_pos = self.parent().tabRect(self.limbo_target_tab).topLeft()
            target_pos_x = target_pos.x()
            target_pos_y = target_pos.y()
            dx = target_pos_x - pos_x
            dy = target_pos_y - pos_y 

            # Animate while the floating tab is more 15  pixels of taxicab-
            # metric distance away from its target:
            if abs(dx) + abs(dy) > 15:

                finished = False

                new_pos_x = pos_x + dx * dt / self.tau
                new_pos_y = pos_y + dy * dt / self.tau

                # Check for overshoot:
                if dx * (target_pos_x - new_pos_x) < 0:
                    new_pos_x = target_pos_x
                if dy * (target_pos_y - new_pos_y) < 0:
                    new_pos_y = target_pos_y

                self.limbo_position = QPoint(new_pos_x, new_pos_y)
            else:
                self.limbo.animation_over()
                self.limbo = None
                self.limbo_position = None
                self.limbo_target_tab = None
        if finished:
            self.previous_time = 0
            self.stop()
        # Update the parent whilst blocking signals back to us to prevent
        # recursion:
        self.callback_in_progress = True
        if self.limbo is not None:
            self.limbo.move(self.parent().mapToGlobal(self.limbo_position))
            self.limbo.update()
        self.parent().update()
        self.callback_in_progress = False


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

    # A TabWidget to hold the tab being dragged. Shared by all instances, but
    # not instantiated until first instance is created, since there may not be
    # a QApplication at import time.
    limbo = None

    def __init__(self, parent, group_id):
        _BaseDragDropTabBar.__init__(self, parent)

        self.group_id = group_id
        self.tab_widgets[group_id].add(self.parent())

        self.prev_active_tab = None
        if self.limbo is None:
            # One Limbo object for all instances:
            self.__class__.limbo = _Limbo()

        self.animation = TabAnimation(self)
        self.tabMoved.connect(self.animation.on_tab_moved)
        self.setUsesScrollButtons(False)
        self.setElideMode(Qt.ElideRight)

    @debug.trace
    def sizeHint(self):
        hint = _BaseDragDropTabBar.sizeHint(self)
        hint.setWidth(self.parent().width())
        return hint

    @debug.trace
    def update(self):
        _BaseDragDropTabBar.update(self)
        self.animation.ensure_running()

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
    def set_tab_parent(self, dest, index=None, pos=None):
        """Move the tab to the given parent DragDropTabBar if it's not already
        there. index=None will determined the insertion index from the
        given mouse position."""
        if index is None:
            assert pos is not None
            index = dest.insertion_index_at(self.mapToGlobal(pos -
                                                             self.dragged_tab_grab_point))
        if self.dragged_tab_parent != dest:
            tab = self.dragged_tab_parent.remove_dragged_tab(self.dragged_tab_index)
            dest.add_dragged_tab(index, tab)
            if dest is self.limbo:
                self.limbo.previous_parent = self.dragged_tab_parent
                self.limbo.previous_index = self.dragged_tab_index
            self.dragged_tab_parent = dest
            self.dragged_tab_index = index
             # Tell parent to redraw to reflect the new position:
            dest.update()

    @debug.trace
    def insertion_index_at(self, pos):
        """Compute at which index the tab with given upper left corner
        position in global coordinates should be inserted into the tabBar."""
        left = self.mapFromGlobal(pos).x()
        for other in range(self.count()):
            other_midpoint = self.tabRect(other).center().x()
            if other_midpoint > left:
                return other
        return self.count()

    @debug.trace
    def update_dragged_tab_animation_pos(self, pos):
        # update the animation position of the dragged tab so that it can be
        # correctly animated once released.
        assert self.dragged_tab_parent is self
        pinned_rect = self.tabRect(self.dragged_tab_index)
        pinned_rect.translate(pos - self.dragged_tab_grab_point - pinned_rect.topLeft())
        left = pinned_rect.left()
        self.animation.positions[self.dragged_tab_index] = left

    @debug.trace
    def update_tab_index(self, index, pos):
        """Check if the tab at the given index, being dragged by the mouse at
        the given position, needs to be moved. Move it and return the new
        index."""

        # If the tab rect were pinned to the mouse at the point it was
        # grabbed, where would it be?
        pinned_rect = self.tabRect(index)
        pinned_rect.translate(pos-self.dragged_tab_grab_point - pinned_rect.topLeft())
        left = pinned_rect.left()
        self.animation.positions[index] = left
        right = pinned_rect.right()

        move_target = None

        for other in range(self.count()):
            other_midpoint = self.tabRect(other).center().x()
            if other < index and left < other_midpoint:
                move_target = other
                # break to move as far left as warranted:
                break
            elif other > index and right > other_midpoint:
                move_target = other
                # Don't break because we might move further right
        if move_target is not None:
            self.moveTab(index, move_target)

            # Workaround for bug in PyQt4 - the tabWdiget does not update its
            # child StackedWidget's current widget when it gets a tabMoved
            # signal durint a mouseMove event:
            if self.currentIndex() == move_target:
                stack = self.parent().findChild(QStackedWidget, 'qt_tabwidget_stackedwidget')
                stack.setCurrentWidget(self.parent().widget(move_target))

            return move_target
        return index

    @debug.trace
    def widgetAt(self, pos):
        """If the given position is over a DragDropTabBar belonging to the
        current group, return the DragDropTabBar. If it is over a TabWidget in
        the same group that has no tabs, or the dragged tab as its only tab,
        return its DragDropTabBar. Otherwise return the limbo object."""
        for tab_widget in self.tab_widgets[self.group_id]:
            count = tab_widget.tabBar().count()
            
            if tab_widget.accept_drops_bar_only:
                if count == 0:
                    widget = tab_widget
                    rect = widget.rect()
                    # The region at the top of the TabWidget equal to the height
                    # of a tab:
                    height = self.dragged_tab_parent.tabRect(self.dragged_tab_index).height()
                    rect.setHeight(height)
                else:
                    widget = tab_widget.tabBar()
                    rect = widget.rect()
                    # Include the whole horizontal part of the tabBar:
                    rect.setLeft(widget.parent().rect().left())
                    rect.setRight(widget.parent().rect().right())
                    # If we're leaving, add a buffer region so that we don't leave
                    # until we have passed a certain distance:
                    if self.drag_in_progress and self.dragged_tab_parent is widget:
                        rect.setLeft(rect.left() - 10)
                        rect.setRight(rect.right() + 10)
                    # No buffer in the vertical directions, but make the tab bars
                    # a slightly bigger target for both coming and going:
                    rect.setTop(rect.top() - 10)
                    rect.setBottom(rect.bottom() + 10)

            else:
                widget = tab_widget
                rect = widget.rect()
                # If we're leaving, add a buffer region so that we don't leave
                # until we have passed a certain distance:
                if self.drag_in_progress and self.dragged_tab_parent is widget:
                    rect.setLeft(rect.left() - 10)
                    rect.setRight(rect.right() + 10)
                    rect.setTop(rect.top() - 10)
                    rect.setBottom(rect.bottom() + 10)

            other_local_pos = widget.mapFromGlobal(self.mapToGlobal(pos))
            if rect.contains(other_local_pos):
                return tab_widget.tabBar()
        else:
            return self.limbo

    @debug.trace
    def mousePressEvent(self, event):
        """Take note of the tab that was clicked so it can be dragged on
        mouseMoveEvents"""
        _BaseDragDropTabBar.mousePressEvent(self, event)
        if event.button() != Qt.LeftButton:
            return
        event.accept()
        self.drag_in_progress = True
        self.dragged_tab_index = self.tabAt(event.pos())
        self.dragged_tab_parent = self
        self.dragged_tab_grab_point = (event.pos()
                                       - self.tabRect(self.dragged_tab_index).topLeft())
        
    @debug.trace
    def mouseMoveEvent(self, event):
        """Update the parent of the tab to be the DragDropTabWidget under the
        mouse, if any, otherwise update it to the limbo object. Update the
        position of the tab in the widget it's in."""
        _BaseDragDropTabBar.mouseMoveEvent(self, event)
        if not self.drag_in_progress:
            self.update()
            return
        event.accept()
        if self.group_id is not None:
            widget = self.widgetAt(event.pos())
            self.set_tab_parent(widget, pos=event.pos())
            other_local_pos = widget.mapFromGlobal(self.mapToGlobal(event.pos()))
            self.dragged_tab_index = widget.update_tab_index(self.dragged_tab_index,
                                                             other_local_pos)
            if self.dragged_tab_parent is not self.limbo:
                self.dragged_tab_parent.update_dragged_tab_animation_pos(other_local_pos)
            widget.update()

    @debug.trace
    def leaveEvent(self, event):
        _BaseDragDropTabBar.leaveEvent(self, event)
        """Called if the window loses focus"""
        if not self.drag_in_progress:
            return
        # We've lost focus during a drag. Cancel the drag.
        self.drag_in_progress = False
        if self.dragged_tab_parent is self.limbo:
            index = self.limbo.previous_index
            self.set_tab_parent(self.limbo.previous_parent, index)
            self.limbo.previous_parent.animation.animate_limbo(self.limbo, index)

        # Put the tab right back in where it goes, by passing in the position
        # equal to the grab point. This way it won't animate:
        pos = self.dragged_tab_parent.tabRect(self.dragged_tab_index).topLeft()
        pos += self.dragged_tab_grab_point
        self.dragged_tab_parent.update_dragged_tab_animation_pos(pos)

        # Tell the parent to redraw the tabs:
        self.dragged_tab_parent.update()

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
        _BaseDragDropTabBar.mouseReleaseEvent(self, event)
        if not self.drag_in_progress or event.button() != Qt.LeftButton:
            return
        event.accept()
        # Cancel the drag:
        self.drag_in_progress = False
        widget = self.widgetAt(event.pos())
        # If the tab and the mouse are both in limbo, then put the tab
        # back at its last known place:
        if widget is self.limbo and self.dragged_tab_parent is self.limbo:
            index = self.limbo.previous_index
            self.set_tab_parent(self.limbo.previous_parent, index)
            self.limbo.previous_parent.animation.animate_limbo(self.limbo, index)
        # But if we're above a tab bar that it's not already in, put it there.
        # Otherwise leave it where it is (don't move it into limbo)
        elif widget is not self.limbo and widget is not self.dragged_tab_parent:
            self.set_tab_parent(widget, pos=event.pos())
        else:
            # It's already in this widget. Store the position of the tab so it
            # can animate:
            other_local_pos = self.dragged_tab_parent.mapFromGlobal(
                                  self.mapToGlobal(event.pos()))
            self.dragged_tab_parent.update_dragged_tab_animation_pos(other_local_pos)

        # Tell the parent to redraw the tabs:
        self.dragged_tab_parent.update()

        # Clear the variables about which tab is being dragged:
        self.dragged_tab_index = None
        self.dragged_tab_parent = None
        self.dragged_tab_grab_point = None

    @debug.trace
    def is_dragged_tab(self, index):
        """Return whether the tab at the given index is currently being dragged"""
        return (self.drag_in_progress
                and self.dragged_tab_parent is self
                and self.dragged_tab_index == index)

    @debug.trace
    def tabInserted(self, index):
        _BaseDragDropTabBar.tabInserted(self, index)
        self.animation.tabInserted(index)

    @debug.trace
    def tabRemoved(self, index):
        _BaseDragDropTabBar.tabRemoved(self, index)
        self.animation.tabRemoved(index)

    @debug.trace
    def tabLayoutChange(self):
        _BaseDragDropTabBar.tabLayoutChange(self)
        self.animation.ensure_running()

    @debug.trace
    def paint_tab(self, index, painter, option):
        # Don't paint the tab if it's the floating tab's target whilst it is
        # animated flying in:
        if index == self.animation.limbo_target_tab:
            return
        painter.save()
        if self.is_dragged_tab(index):
            # The dragged tab is pinned to the mouse:
            xpos = self.mapFromGlobal(QCursor.pos()).x() - self.dragged_tab_grab_point.x()
        else:
            # Other tabs are at their current animated position:
            xpos = self.animation.positions[index]
        tabrect = self.tabRect(index)
        if xpos < 0:
            # Don't draw tabs at negative positions:
            xpos = 0
        if xpos > self.width() - tabrect.width():
            # Don't draw tabs further right than the end of the tabBar:
            xpos = self.width() - tabrect.width()
        painter.translate(xpos - tabrect.left(), 0)
        self.initStyleOption(option, index)
        painter.drawControl(QStyle.CE_TabBarTab, option)
        painter.restore()

    @debug.trace
    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionTab()
        # Draw in reverse order so if there is overlap, tabs to the left are
        # on top:
        for index in range(self.count() -1 , -1, -1):
            if self.currentIndex() == index:
                # Draw the active tab last so it's on top:
                continue
            self.paint_tab(index, painter, option)
        if self.currentIndex() != -1:
            self.paint_tab(self.currentIndex(), painter, option)
        painter.end()


class DragDropTabWidget(QTabWidget):
    """A tab widget that supports dragging and dropping of tabs between tab
    widgets that share a group_id. a group_id of None indicates that tab
    dragging is disabled."""
    def __init__(self, group_id=None, accept_drops_bar_only=True):
        QTabWidget.__init__(self)
        self.setTabBar(DragDropTabBar(self, group_id))
        self.tabBar().setExpanding(False)
        self.tab_bar = self.tabBar() # Backward compatibility for BLACS

        # Whether to accept drops only on the tab bar at the top,
        # as opposed to accepting them anywhere on the tabWidget:
        self.accept_drops_bar_only = accept_drops_bar_only


if __name__ == '__main__':    
    class ViewPort(object):
        def __init__(self, id, container_layout,i):
            #ui = UiLoader().load('viewport.ui')
            self.tab_widget = DragDropTabWidget(id)
            container_layout.addWidget(self.tab_widget)
            self.tab_widget.addTab(QLabel("foo %d"%i), 'foo %d 1' % i)
            self.tab_widget.addTab(QLabel("bar %d"%i), 'bar bar bar %d 1' % i)
            self.tab_widget.tabBar().setTabTextColor(0, QColor(255, 0, 0))
            self.tab_widget.tabBar().setTabTextColor(1, QColor(0, 255, 0))

            self.tab_widget.tabBar().setTabIcon(1, lyse_icon)
            self.tab_widget.tabBar().setTabIcon(0, runmanager_icon)


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

    import qtutils.icons

    lyse_icon = QIcon(':/qtutils/custom/lyse')
    runmanager_icon = QIcon(':/qtutils/custom/runmanager')

    app = RunViewer()
    
    timer = QTimer()
    timer.start(500)

    import time

    def change_text():
        if DragDropTabBar.limbo is not None:
            limbo = DragDropTabBar.limbo
            if limbo.count():
                tab_text = limbo.tabText(0)
                split = str(tab_text).split()
                text = ' '.join(split[:-1])
                number = int(split[-1])
                number = number + 1
                limbo.setTabText(0, text + ' ' + str(number))
                if number % 2:
                    limbo.setTabIcon(0, lyse_icon)
                else:
                    limbo.setTabIcon(0, runmanager_icon)

    timer.timeout.connect(change_text)
    qapplication.exec_()
