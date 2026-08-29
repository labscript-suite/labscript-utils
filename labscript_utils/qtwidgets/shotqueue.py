#####################################################################
#                                                                   #
# shotqueue.py                                                      #
#                                                                   #
# Copyright 2026, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import os

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *
from qtutils.qt.QtCore import pyqtSignal as Signal


FILEPATH_COLUMN = 0
__all__ = ['FILEPATH_COLUMN', 'ShotQueueTreeView', 'ShotQueueWidget']


def _normalise_extensions(accepted_extensions):
    if accepted_extensions is None:
        accepted_extensions = ('.h5', '.hdf5')
    elif isinstance(accepted_extensions, str):
        accepted_extensions = (accepted_extensions,)
    return tuple(extension.lower() for extension in accepted_extensions)


class ShotQueueTreeView(QTreeView):
    """Generic queue view with delete-key handling and shot-file drops."""

    deleteRequested = Signal()
    filesDropped = Signal(list)

    def __init__(self, parent=None, accepted_extensions=None):
        QTreeView.__init__(self, parent)
        self._accepted_extensions = _normalise_extensions(accepted_extensions)
        self.header().setStretchLastSection(True)
        self.setAutoScroll(False)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)

    def accepted_extensions(self):
        return tuple(self._accepted_extensions)

    def set_accepted_extensions(self, accepted_extensions):
        self._accepted_extensions = _normalise_extensions(accepted_extensions)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            event.accept()
            self.deleteRequested.emit()
            return
        QTreeView.keyPressEvent(self, event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        delete_action = menu.addAction('Delete selected rows')
        delete_action.setEnabled(bool(self.selectionModel().selectedRows()))
        chosen_action = menu.exec(event.globalPos())
        if chosen_action is delete_action:
            self.deleteRequested.emit()
            event.accept()
            return
        QTreeView.contextMenuEvent(self, event)

    def dragEnterEvent(self, event):
        if self._event_has_acceptable_urls(event):
            event.setDropAction(Qt.CopyAction)
            event.accept()
            return
        QTreeView.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        if self._event_has_acceptable_urls(event):
            event.setDropAction(Qt.CopyAction)
            event.accept()
            return
        QTreeView.dragMoveEvent(self, event)

    def dropEvent(self, event):
        if self._event_has_acceptable_urls(event):
            paths = self._paths_from_urls(event.mimeData().urls())
            if paths:
                event.setDropAction(Qt.CopyAction)
                event.accept()
                self.filesDropped.emit(paths)
                return
        QTreeView.dropEvent(self, event)

    def _event_has_acceptable_urls(self, event):
        if not event.mimeData().hasUrls():
            return False
        return bool(self._paths_from_urls(event.mimeData().urls()))

    def _paths_from_urls(self, urls):
        paths = []
        for url in urls:
            if not url.isLocalFile():
                continue
            path = os.path.abspath(str(url.toLocalFile()))
            if self._is_accepted_path(path):
                paths.append(path)
        return paths

    def _is_accepted_path(self, path):
        return os.path.isfile(path) and path.lower().endswith(self._accepted_extensions)

class ShotQueueWidget(QWidget):
    """Reusable shot queue editor widget."""

    queueChanged = Signal()
    selectionChanged = Signal(list)
    filesAdded = Signal(list)

    def __init__(
        self,
        parent=None,
        accepted_extensions=None,
        file_dialog_filter='Shot files (*.h5 *.hdf5)',
        allow_duplicates=False,
        column_title='Filepath',
        column_titles=None,
        path_column=FILEPATH_COLUMN,
        connect_add_button=True,
        connect_delete_requested=True,
        connect_files_dropped=True,
    ):
        QWidget.__init__(self, parent)
        self.accepted_extensions = _normalise_extensions(accepted_extensions)
        self.file_dialog_filter = file_dialog_filter
        self.allow_duplicates = allow_duplicates
        self.last_opened_shots_folder = ''
        if column_titles is None:
            column_titles = [column_title]
        self.column_titles = list(column_titles)
        self.path_column = int(path_column)

        self.queue_model = QStandardItemModel(self)
        self.queue_model.setColumnCount(len(self.column_titles))
        for column, title in enumerate(self.column_titles):
            self.queue_model.setHorizontalHeaderItem(column, QStandardItem(title))

        self.queue_view = ShotQueueTreeView(self, accepted_extensions=self.accepted_extensions)
        self.queue_view.setModel(self.queue_model)
        self.queue_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.queue_view.header().setStretchLastSection(False)
        for column in range(len(self.column_titles)):
            resize_mode = (
                QHeaderView.Stretch
                if column == self.path_column
                else QHeaderView.ResizeToContents
            )
            self.queue_view.header().setSectionResizeMode(column, resize_mode)

        self.add_button = QToolButton(self)
        self.add_button.setText('Add')

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.add_button)
        button_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.queue_view)
        layout.addLayout(button_layout)

        if connect_add_button:
            self.add_button.clicked.connect(self.prompt_for_files)
        if connect_delete_requested:
            self.queue_view.deleteRequested.connect(self.remove_selected)
        if connect_files_dropped:
            self.queue_view.filesDropped.connect(self.add_files)
        self.queue_model.rowsInserted.connect(self._on_queue_changed)
        self.queue_model.rowsRemoved.connect(self._on_queue_changed)
        self.queue_model.modelReset.connect(self._on_queue_changed)
        self.queue_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self._update_button_states()

    def files(self):
        return [
            self._queue_path_for_row(row)
            for row in range(self.queue_model.rowCount())
        ]

    def selected_files(self):
        return [self._queue_path_for_row(row) for row in self.selected_rows()]

    def selected_rows(self):
        return sorted(index.row() for index in self.queue_view.selectionModel().selectedRows())

    def select_paths(self, paths):
        if isinstance(paths, str):
            paths = [paths]
        path_lookup = {os.path.abspath(str(path)) for path in paths}
        rows = []
        for row in range(self.queue_model.rowCount()):
            if self._queue_path_for_row(row) in path_lookup:
                rows.append(row)
        self._select_rows(rows)

    def set_files(self, paths):
        self.queue_model.removeRows(0, self.queue_model.rowCount())
        self.append(paths)

    def append(self, paths):
        paths = self._prepare_paths(paths)
        if not paths:
            return []
        for path in paths:
            self.queue_model.appendRow(self._create_row(path))
        self.filesAdded.emit(paths)
        return paths

    def prepend(self, path):
        paths = self._prepare_paths([path])
        if not paths:
            return []
        self.queue_model.insertRow(0, self._create_row(paths[0]))
        self.filesAdded.emit(paths)
        self._select_rows([0])
        return paths

    def add_files(self, paths):
        added = self.append(paths)
        if added:
            self.last_opened_shots_folder = os.path.dirname(added[-1])
            first_new_row = self.queue_model.rowCount() - len(added)
            self._select_rows(range(first_new_row, self.queue_model.rowCount()))
        return added

    def prompt_for_files(self):
        file_names = QFileDialog.getOpenFileNames(
            self,
            'Select shot file(s) to add to the queue',
            self.last_opened_shots_folder,
            self.file_dialog_filter,
        )
        if isinstance(file_names, tuple):
            file_names, _ = file_names
        return self.add_files(file_names)

    def remove_selected(self):
        for row in reversed(self.selected_rows()):
            self.queue_model.removeRow(row)

    def clear(self):
        if self.queue_model.rowCount():
            self.queue_model.removeRows(0, self.queue_model.rowCount())

    def is_in_queue(self, path):
        path = os.path.abspath(str(path))
        return any(
            self._queue_path_for_row(row) == path
            for row in range(self.queue_model.rowCount())
        )

    def get_save_data(self):
        return {
            'files_queued': self.files(),
            'last_opened_shots_folder': self.last_opened_shots_folder,
        }

    def restore_save_data(self, data):
        self.last_opened_shots_folder = data.get('last_opened_shots_folder', '')
        self.set_files(data.get('files_queued', []))

    def set_row_infos(self, row_infos):
        self.queue_model.removeRows(0, self.queue_model.rowCount())
        if not row_infos:
            return
        for row_info in row_infos:
            self.queue_model.appendRow(self._create_row_from_info(row_info))

    def _create_row(self, path):
        row_items = self._create_padding_items(self.queue_model.columnCount())
        row_items[self.path_column] = self._create_display_item(
            path,
            tooltip=path,
            path=path,
        )
        return row_items

    def _create_row_from_info(self, row_info):
        if not isinstance(row_info, dict):
            return self._create_row(str(row_info))
        path = os.path.abspath(str(row_info['path']))
        label = row_info.get('label', os.path.basename(path))
        tooltip = row_info.get('tooltip', path)
        columns = list(row_info.get('columns', []))
        row_items = self._create_padding_items(self.queue_model.columnCount())
        row_items[self.path_column] = self._create_display_item(
            label,
            tooltip=tooltip,
            path=path,
        )
        extra_columns = [i for i in range(self.queue_model.columnCount()) if i != self.path_column]
        for column_index, column_info in zip(extra_columns, columns):
            row_items[column_index] = self._create_display_item_from_info(column_info)
        return row_items

    def _create_padding_items(self, count):
        items = []
        for _ in range(max(0, count)):
            items.append(self._create_display_item(''))
        return items

    def _create_display_item(self, text, tooltip='', alignment=None, path=None):
        item = QStandardItem(str(text))
        item.setEditable(False)
        item.setToolTip(tooltip)
        if alignment is not None:
            item.setTextAlignment(alignment)
        if path is not None:
            item.setData(os.path.abspath(str(path)), Qt.UserRole)
        return item

    def _create_display_item_from_info(self, column_info):
        if isinstance(column_info, dict):
            text = column_info.get('text', '')
            tooltip = column_info.get('tooltip', '')
            alignment = column_info.get('alignment', Qt.AlignLeft | Qt.AlignVCenter)
        else:
            text = column_info
            tooltip = ''
            alignment = Qt.AlignLeft | Qt.AlignVCenter
        return self._create_display_item(text, tooltip=tooltip, alignment=alignment)

    def _queue_path_for_row(self, row):
        item = self.queue_model.item(row, self.path_column)
        path = item.data(Qt.UserRole)
        if path is None:
            path = item.text()
        return os.path.abspath(str(path))

    def _prepare_paths(self, paths):
        if isinstance(paths, str):
            paths = [paths]
        existing = set(self.files())
        pending = set()
        prepared = []
        for path in paths:
            path = os.path.abspath(str(path))
            if not self._is_accepted_path(path):
                continue
            if not self.allow_duplicates and (path in existing or path in pending):
                continue
            pending.add(path)
            prepared.append(path)
        return prepared

    def _is_accepted_path(self, path):
        return os.path.isfile(path) and path.lower().endswith(self.accepted_extensions)

    def _on_queue_changed(self, *args):
        self._update_button_states()
        self.queueChanged.emit()

    def _on_selection_changed(self, *args):
        self._update_button_states()
        self.selectionChanged.emit(self.selected_files())

    def _update_button_states(self):
        pass

    def _select_rows(self, rows):
        rows = list(rows)
        selection_model = self.queue_view.selectionModel()
        selection_model.clearSelection()
        for row in rows:
            index = self.queue_model.index(row, self.path_column)
            selection_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        if rows:
            self.queue_view.setCurrentIndex(self.queue_model.index(rows[0], self.path_column))
