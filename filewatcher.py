#####################################################################
#                                                                   #
# filewatcher.py                                                    #
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
    from inspect import getargspec as getfullargspec
else:
    from inspect import getfullargspec

import threading
import os
import time
import hashlib


def hash_bytestr_iter(bytesiter, hasher, ashexstr=True):
    for block in bytesiter:
        hasher.update(block)
    return (hasher.hexdigest() if ashexstr else hasher.digest())


def file_as_blockiter(afile, blocksize=65536):
    with afile:
        block = afile.read(blocksize)
        while len(block) > 0:
            yield block
            block = afile.read(blocksize)


class FileWatcher(object):
    def __init__(self, callback, files=None, folders=None, modified_info=None,
                 hashable_types=None, interval=1, **kwargs):
        """
        Detect modification, deletion, creation, or restoration of specific files
        (and all files in specific folders).

        callback -- elicited whenever file events are detected, requires at least
            (name, info) arguments. Event specific callback requires 
            (name, info, event) arguments, where event is on of:
            'modified', 'deleted' (or None), 'created', 'restored', 'original'
            The 'original' event corresponds to a state change that results in 
            the original file info at instantiation.

        Keyword arguments:
        files -- List of specific files to watch.
            A single file can be specified as a string (default None).
        folders -- List of specific folders to watch.
            A single folder can be specified as a string (default None).
            If a file is created/deleted in/from any watched folder, it is added/
            removed to/from the FileWatcher.files attribute.
        modified_info -- File info to detect modification/restoration with.
            If None (default), the initial modified info will be based on the 
            first polling of files.
        hashable_types -- File extensions for which MD5 checksum will be used to
            detect modification/restoration with (default None). Files of any 
            other type will be watched using their modified time. 
            Restoration cannot be detected for types not in hashable_types.
        interval -- Polling interval in seconds (default 1).
        """
        if len(getfullargspec(callback)[0]) > 2:
            # For backwards compatability, allow callback to have only two args
            self.callback = callback
        else:
            self.callback = lambda name, info, event: callback(name, info)
        self.lock = threading.Lock()

        self.hashable_types = [] if hashable_types is None else [x.lower() for x in hashable_types]
        self.files = set()
        self.folders = set()
        if files:
            self.add_files(files)
        if folders:
            self.add_folders(folders)

        # Restore modified_info if modified_times is provided as a keyword argument
        if 'modified_times' in kwargs and modified_info is None:
            modified_info = kwargs['modified_times']
        elif modified_info is None:
            modified_info = {}
        self.modified_info_original = modified_info.copy()
        self.modified_info = modified_info.copy()
        self.update_files(trigger_callback=False)

        # Remove keys in self.modified_info that are not in the files watchlist
        for name in self.modified_info.copy():
            if name not in self.files:
                del self.modified_info[name]

        self.main = threading.Thread(target=self.mainloop)
        self.main.daemon = True
        self.running = True
        self.interval = interval
        self.main.start()

    def mainloop(self):
        while self.running:
            time.sleep(self.interval)
            with self.lock:
                self.update_files()
                self.check()

    def update_files(self, folders=None, trigger_callback=True, recursive=True):
        """Refresh the watchlist of files (FileWatcher.files) by checking the folders kwarg
        or Filewatcher.folders if this is not specified.
        """
        if folders is None:
            folders = self.folders
        for folder in folders:
            try:
                for name in os.listdir(folder):
                    path = os.path.join(folder, name)
                    # Recurse into subdirectories
                    if recursive and os.path.isdir(path):
                        self.update_files([path], trigger_callback)
                    else:
                        if not path in self.files:
                            self.files.add(path)
                            if trigger_callback:
                                self.callback(
                                    path, os.path.getmtime(path), 'created')
            except OSError:
                # Folder has been deleted. File deletion will still be
                # detected, so we can ignore this.
                continue

    def check(self):
        check_all = False
        first_pass = True if not self.modified_info_original else False
        files_to_forget = []
        for name in self.files:
            try:
                # If extension is a hashable type, use hash for modified_info
                if os.path.splitext(name)[-1].lower() in self.hashable_types:
                    modified_info = hash_bytestr_iter(
                        file_as_blockiter(open(name, 'rb')), hashlib.md5())
                # Otherwise use last modified time for modified_info
                else:
                    modified_info = os.path.getmtime(name)
            except (OSError, IOError):
                # If the file does not exist, set modified_info to None
                if not os.path.exists(name):
                    modified_info = None
                else:
                    # If we couldn't get the modified time but the path does exist,
                    # there was probablly some race condition with the path becoming unavailable briefly
                    # we'll skip the rest of the check for now, and leave it up to the next call of check()
                    # to catch any file modification
                    continue
            if first_pass:
                original_modified_info = self.modified_info_original.setdefault(
                    name, modified_info)
            else:
                if name in self.modified_info_original:
                    original_modified_info = self.modified_info_original[name]
                else:
                    original_modified_info = None
            previous_modified_info = self.modified_info.setdefault(
                name, modified_info)
            self.modified_info[name] = modified_info
            if modified_info != previous_modified_info and not first_pass:
                if modified_info == None:
                    self.callback(name, modified_info, 'deleted')
                    files_to_forget.append(name)
                    self.modified_info.pop(name)
                    check_all = True
                elif modified_info == original_modified_info:
                    self.callback(name, modified_info, 'restored')
                    check_all = True
                elif name in self.modified_info:
                    del self.modified_info[name]
                    self.callback(name, modified_info, 'modified')
        for name in files_to_forget:
            self.files.remove(name)
        if check_all and self.modified_info == self.modified_info_original:
            self.callback('all', '', 'original')
        if first_pass:
            print(self.modified_info_original)

    def stop(self):
        self.running = False

    def add_file(self, path):
        self.add_files(path)

    def get_modified_info(self):
        with self.lock:
            times = self.modified_info.copy()
        return times

    def add_folder(self, folder):
        self.add_folders(folder)

    def add_files(self, files):
        with self.lock:
            if isinstance(files, str):
                self.files.add(files)
            else:
                self.files = self.files.union(set(files))

    def add_folders(self, folders):
        with self.lock:
            if isinstance(folders, str):
                self.folders.add(folders)
            else:
                self.folders = self.folders.union(set(folders))
            self.update_files(trigger_callback=False)


if __name__ == '__main__':
    # Example usage

    def callback(name, modified, event=None):
        if event == 'deleted' or modified is None:
            print(name, 'has been deleted')
        elif event == 'modified':
            print(name, 'was modified: ', modified)
        elif event == 'created':
            print(name, 'was created at ', modified)
        elif event == 'restored':
            print(name, 'was restored (hash {})'.format(modified))
        elif event == 'original':
            print('All files are in the original state.')
        else:
            print('Unknown event from filewatcher: {}'.format(event))

    test_file = 'filewatcher_test.txt'
    test_folder = 'foobar'
    if not os.path.exists(test_folder):
        os.mkdir(test_folder)
        print(f'Created folder {test_folder}')
    if not os.path.exists(test_file):
        with open(test_file, 'w') as f:
            print(f'Created file {test_file}')
    f = FileWatcher(callback, files=test_file, folders=test_folder,
                    hashable_types=['.py', '.ini', '.txt'], interval=2)
