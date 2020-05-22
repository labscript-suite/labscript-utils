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
from inspect import getfullargspec
from queue import Queue, Empty
import threading
import os
import hashlib


class FileWatcher(object):
    def __init__(self, callback, files=None, folders=None, clean_modified_info=None,
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
        clean_modified_info -- File info to detect modification/restoration with respect
            to. If None (default), or for files not present in clean_modified_info, the
            initial modified info will be based on the first polling of files.
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

        self.hashable_types = (
            [] if hashable_types is None else [x.lower() for x in hashable_types]
        )
        self.files = set()
        self.folders = set()

        # Backwards compat for BLACS before hashing was introduced:
        if 'modified_times' in kwargs and clean_modified_info is None:
            clean_modified_info = kwargs['modified_times']

        if clean_modified_info is None:
            clean_modified_info = {}
        self.clean_modified_info = clean_modified_info.copy()

        if files:
            self.add_files(files)
        if folders:
            self.add_folders(folders)
        self.update_files(trigger_callback=False)

        # Remove keys from clean_modified_info that are not in the files watchlist:
        for name in self.clean_modified_info.copy():
            if name not in self.files:
                del self.clean_modified_info[name]

        self.modified_info = self.clean_modified_info.copy()

        self.main = threading.Thread(target=self.mainloop)
        self.main.daemon = True
        self.running = True
        self.interval = interval
        self._stopping = Queue() 
        self.main.start()

    def mainloop(self):
        stopping = False
        while not stopping:
            try:
                self._stopping.get(timeout=self.interval)
            except Empty:
                stopping = False
            else:
                stopping = True
            # We run one final time if stopping so that after we have stopped,
            # get_modified_info() is guaranteed to reflect any events prior to stop()
            # being called
            with self.lock:
                self.update_files(trigger_callback=not stopping)
                self.check(trigger_callback=not stopping)

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

    def _modified_info_of_file(self, name):
        try:
            # If extension is a hashable type, use hash for modified_info
            if os.path.splitext(name)[-1].lower() in self.hashable_types:
                with open(name, 'rb') as f:
                    return hashlib.md5(f.read()).hexdigest()
            # Otherwise use last modified time for modified_info
            elif os.path.isdir(name):
                # Modified info of a directory is a hash of its entries:
                entries = os.listdir(os.fsencode(name))
                return hashlib.md5(b'\0'.join(entries)).hexdigest()
            else:
                return os.path.getmtime(name)
        except (OSError, IOError):
            # If it doesn't exist or is inaccessible, modified info is None
            return None

    def check(self, trigger_callback=True):
        check_all = False
        deleted_files = set()
        for name in self.files:
            modified_info = self._modified_info_of_file(name)
            previous_modified_info = self.modified_info.setdefault(name, modified_info)
            self.modified_info[name] = modified_info
            if modified_info != previous_modified_info:
                if modified_info is None:
                    if trigger_callback:
                        self.callback(name, modified_info, 'deleted')
                    deleted_files.add(name)
                    check_all = True
                elif modified_info == self.clean_modified_info.get(name, None):
                    if trigger_callback:
                        self.callback(name, modified_info, 'restored')
                    check_all = True
                elif name in self.modified_info:
                    if trigger_callback:
                        self.callback(name, modified_info, 'modified')
        for name in deleted_files:
            # Keep monitoring deleted files if they were explicitly added, since we want
            # to be able to detect them being restored:
            if name not in self.clean_modified_info:
                self.files.remove(name)
                del self.modified_info[name]
        if (
            check_all
            and self.modified_info == self.clean_modified_info
            and self.files == self.clean_modified_info.keys()
            and trigger_callback
        ):
            self.callback('all', '', 'original')

    def stop(self):
        with self.lock:
            if not self.running:
                raise RuntimeError("Not running")
            self._stopping.put(None)
            self.running = False
        self.main.join()
        self.main = None

    def add_file(self, path):
        self.add_files((path,))

    def get_clean_modified_info(self):
        with self.lock:
            return self.clean_modified_info.copy()

    def get_modified_info(self):
        with self.lock:
            return self.modified_info.copy()

    def get_modified_times(self):
        # Backward compat for BLACS from before file hashes were introduced
        return self.get_modified_info()

    def add_folder(self, folder):
        self.add_folders((folder,))

    def add_files(self, files, clean_modified_info=None):
        if clean_modified_info is None:
            clean_modified_info = {}
        with self.lock:
            self.files = self.files.union(set(files))
            # Remove keys from the clean_modified_info that are not in the files
            # watchlist:
            for name in self.clean_modified_info.copy():
                if name not in self.files:
                    del self.clean_modified_info[name]
            # For all files added to the watchlist that we were not given a
            # clean_modified_info for, set it based on their info now:
            for name in files:
                if name in clean_modified_info:
                    self.clean_modified_info[name] = clean_modified_info[name]
                elif name not in self.clean_modified_info:
                    self.clean_modified_info[name] = self._modified_info_of_file(name)

    def add_folders(self, folders, clean_modified_info=None):
        if clean_modified_info is None:
            clean_modified_info = {}
        with self.lock:
            self.folders = self.folders.union(set(folders))
            initial_files = self.files.copy()
            self.update_files(trigger_callback=False)
            # Remove keys from the clean_modified_info that are not in the files
            # watchlist:
            for name in self.clean_modified_info.copy():
                if name not in self.files:
                    del self.clean_modified_info[name]
            # For all files added to the watchlist that we were not given a
            # clean_modified_info for, set it based on their info now:
            for name in self.files - initial_files:
                if name in clean_modified_info:
                    self.clean_modified_info[name] = clean_modified_info[name]
                elif name not in self.clean_modified_info:
                    self.clean_modified_info[name] = self._modified_info_of_file(name)


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

    test_files = ['filewatcher_test.txt', 'foo/bar.txt']
    test_folder = 'foo'

    f = FileWatcher(
        callback,
        files=test_files[0],
        folders=test_folder,
        hashable_types=['.py', '.ini', '.txt'],
        interval=2,
    )


    for path in test_files:
        folder, _ = os.path.split(path)
        if not os.path.exists(path):
            if folder and not os.path.exists(folder):
                os.makedirs(folder)
            with open(path, 'w') as f:
                print('Created file {}'.format(path))
    
