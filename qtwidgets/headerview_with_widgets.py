from __future__ import division, unicode_literals, print_function, absolute_import
from qtutils.qt import QtCore, QtGui, QtWidgets


class HorizontalHeaderViewWithWidgets(QtWidgets.QHeaderView):

    """A QHeaderView that supports inserting arbitrary
    widgets into sections. Use setWidget(logical_index, widget)
    to set and setWidget(logical_index, None) to unset.
    Decorations, checkboxes or anything other than text in the
    headers containing widgets is unsupported, and may result
    in garbled output"""

    thinspace = u'\u2009'  # For indenting text

    stylesheet = """
                 QHeaderView::section {
                 /* Will be set dynamically: */
                 padding-top: %dpx;
                 padding-bottom: %dpx;
                 /* Required, otherwise set to zero upon setting any stylesheet at all: */
                 padding-left: 4px;
                 /* Required for some reason, otherwise other settings ignored: */
                 color: black;
                 }

                 /* Any other style goes here: */
                 %s
                 """

    def __init__(self, model, parent=None):
        self.widgets = {}
        self.indents = {}
        self.model = model
        QtWidgets.QHeaderView.__init__(self, QtCore.Qt.Horizontal, parent)
        self.setDefaultAlignment(QtCore.Qt.AlignLeft)
        self.sectionMoved.connect(self.update_widget_positions)
        self.sectionResized.connect(self.update_widget_positions)
        self.geometriesChanged.connect(self.update_widget_positions)
        self.sectionCountChanged.connect(self.update_widget_positions)
        self.model.columnsInserted.connect(self.on_columnsInserted)
        self.model.columnsRemoved.connect(self.on_columnsRemoved)
        self.setSectionsMovable(True)
        self.vertical_padding = 0
        self.position_update_required = False
        self.custom_style = ''
        self.update_indents()

    def setStyleSheet(self, custom_style):
        self.custom_style = custom_style
        self.update_indents()

    def showSection(self, *args, **kwargs):
        result = QtWidgets.QHeaderView.showSection(self, *args, **kwargs)
        self.update_indents()
        self.update_widget_positions()
        return result

    def hideSection(self, *args, **kwargs):
        result = QtWidgets.QHeaderView.hideSection(self, *args, **kwargs)
        self.update_indents()
        self.update_widget_positions()
        return result

    def setSectionHidden(self, *args, **kwargs):
        result = QtWidgets.QHeaderView.setSectionHidden(self, *args, **kwargs)
        self.update_indents()
        self.update_widget_positions()
        return result

    def viewportEvent(self, event):
        if event.type() == QtCore.QEvent.Paint:
            self.update_widget_positions()
        return QtWidgets.QHeaderView.viewportEvent(self, event)

    def setWidget(self, logical_index, widget=None):
        header_item = self.model.horizontalHeaderItem(logical_index)
        if header_item is None:
            self.model.setHorizontalHeaderItem(logical_index, QtGui.QStandardItem())
        if widget is None:
            if logical_index in self.widgets:
                widget = self.widgets[logical_index]
                widget.setParent(None)
                del self.widgets[logical_index]
                widget.removeEventFilter(self)
                del self.indents[widget]
                label_text = self.model.headerData(logical_index, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
                # Compatibility with both API types:
                if isinstance(label_text, QtCore.QVariant):
                    if label_text.isNull():
                        return
                    else:
                        label_text = label_text.toString()
                if label_text is None:
                    return
                else:
                    raw_label_text = label_text.replace(self.thinspace, '')
                    self.model.setHeaderData(logical_index, QtCore.Qt.Horizontal, raw_label_text, QtCore.Qt.DisplayRole)
        else:
            self.widgets[logical_index] = widget
            widget.setParent(self)
            widget.installEventFilter(self)
            if not self.isSectionHidden(logical_index) and not widget.isVisible():
                widget.show()
        self.update_indents()
        self.update_widget_positions()

    def showEvent(self, event):
        QtWidgets.QHeaderView.showEvent(self, event)
        self.update_indents()
        self.update_widget_positions()

    def update_indents(self):
        max_widget_height = 0
        for visual_index in range(self.count()):
            logical_index = self.logicalIndex(visual_index)
            if logical_index in self.widgets:
                widget = self.widgets[logical_index]
                if not self.isSectionHidden(logical_index):
                    max_widget_height = max(max_widget_height, widget.size().height())
                desired_indent = widget.size().width()
                item = self.model.horizontalHeaderItem(logical_index)
                font = item.font()
                fontmetrics = QtGui.QFontMetrics(font, self)
                indent = ''
                while fontmetrics.width(indent) < desired_indent:
                    indent += self.thinspace
                self.indents[widget] = indent
        font = self.font()
        fontmetrics = QtGui.QFontMetrics(font, self)
        height = fontmetrics.height()
        required_padding = (max_widget_height + 2 - height) // 2
        required_padding = max(required_padding, 3)
        QtWidgets.QHeaderView.setStyleSheet(self, self.stylesheet % (required_padding, required_padding, self.custom_style))

    def sectionSizeFromContents(self, logical_index):
        base_size = QtWidgets.QHeaderView.sectionSizeFromContents(self, logical_index)
        width, height = base_size.width(), base_size.height()
        if logical_index in self.widgets:
            widget_size = self.widgets[logical_index].size()
            widget_width, widget_height = widget_size.width(), widget_size.height()
            height = max(height, widget_height + 2)
            width = max(width, widget_width + 7)
        return QtCore.QSize(width, height)

    def update_widget_positions(self):
        # Do later and compress events, so as not to call
        # self.do_update_widget_positions multiple times:
        if not self.position_update_required:
            timer = QtCore.QTimer.singleShot(0, self.do_update_widget_positions)
            self.position_update_required = True

    def do_update_widget_positions(self):
        self.position_update_required = False
        if not self.count():
            return
        max_height = max(self.sectionSizeFromContents(i).height()
                         for i in range(self.count())
                         if not self.isSectionHidden(i))
        for visual_index in range(self.count()):
            logical_index = self.logicalIndex(visual_index)
            if logical_index in self.widgets:
                widget = self.widgets[logical_index]
                if not self.isSectionHidden(logical_index) and not widget.isVisible():
                    widget.show()
                elif self.isSectionHidden(logical_index) and widget.isVisible():
                    widget.hide()
                section_position = self.sectionViewportPosition(logical_index)
                widget_size = widget.size()
                widget_width, widget_height = widget_size.width(), widget_size.height()
                widget_target_x = section_position + 3
                widget_target_y = (max_height - widget_height) // 2 - 1
                widget_current_pos = widget.pos()
                widget_current_x, widget_current_y = widget_current_pos.x(), widget_current_pos.y()
                if (widget_target_x, widget_target_y) != (widget_current_x, widget_current_y):
                    widget.move(widget_target_x, widget_target_y)
                try:
                    indent = self.indents[widget]
                except KeyError:
                    return
                label_text = self.model.headerData(logical_index, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
                # Compatibility with both API types:
                if isinstance(label_text, QtCore.QVariant):
                    if not label_text.isNull():
                        label_text = label_text.toString()
                    else:
                        label_text = ''
                if label_text is None:
                    label_text = ''
                raw_label_text = label_text.replace(self.thinspace, '')
                if label_text != indent + raw_label_text:
                    self.model.setHeaderData(
                        logical_index, QtCore.Qt.Horizontal, indent + raw_label_text, QtCore.Qt.DisplayRole)

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
            self.window.resize(640, 480)
            layout = QtGui.QVBoxLayout(self.window)
            self.model = QtGui.QStandardItemModel()
            self.treeview = QtGui.QTreeView(self.window)
            self.header = HorizontalHeaderViewWithWidgets(self.model)

            self.treeview.setSortingEnabled(True)

            self.model.setHorizontalHeaderLabels(['Delete', 'Name', 'Value', 'Units', 'Expansion'])
            self.button = QtGui.QPushButton('hello, world!')
            self.button.setIcon(QtGui.QIcon(':qtutils/fugue/smiley-lol'))

            self.button2 = QtGui.QToolButton()
            self.button2.setIcon(QtGui.QIcon(':qtutils/fugue/plus'))

            self.button3 = QtGui.QToolButton()
            self.button3.setMinimumHeight(50)
            self.button3.setIcon(QtGui.QIcon(':qtutils/fugue/minus'))

            self.button4 = QtGui.QCheckBox()

            self.header.setWidget(0, self.button)
            self.header.setWidget(1, self.button2)
            self.header.setWidget(2, self.button3)
            self.header.setWidget(4, self.button4)
            self.treeview.setHeader(self.header)
            self.treeview.setModel(self.model)
            layout.addWidget(self.treeview)
            self.model.insertColumn(2, [QtGui.QStandardItem('test')])
            self.window.show()

            for col in range(self.model.columnCount()):
                self.treeview.resizeColumnToContents(col)

            QtCore.QTimer.singleShot(2000, lambda: self.header.hideSection(3))
            QtCore.QTimer.singleShot(4000, lambda: self.header.showSection(3))
            QtCore.QTimer.singleShot(6000, lambda: self.header.setWidget(0, None))
            QtCore.QTimer.singleShot(8000, lambda: self.header.setWidget(0, self.button))

    qapplication = QtGui.QApplication(sys.argv)
    qapplication.setAttribute(QtCore.Qt.AA_DontShowIconsInMenus, False)
    app = TestApp()
    qapplication.exec_()
