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

import threading
import os
import time
import hashlib
import inspect

# Files with the following extensions will be watched via their MD5 hash
# and we can therefore determine whether the file has been restored
hashable_types = ['.py', '.txt', '.ini']

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
    def __init__(self, callback, files=None, folders=None, modified_info=None, **kwargs):
        # To implement restoration events, callback should have args ['name', 'info', 'event']
        # For backwards compatability, allow callback to have only the first two args
        if len(inspect.getargspec(callback)[0]) > 2:
            self.callback = callback
        else:
            self.callback = lambda name, info, event: callback(name, info)
        self.lock = threading.Lock()
        
        self.files = set()
        self.folders = set()
        if files:
            self.add_files(files)
        if folders:
            self.add_folders(folders)
        
        # restore modified info
        if 'modified_times' in kwargs and modified_info is None:
            modified_info = kwargs['modified_times']
        elif modified_info is None:
            modified_info = {}
        self.modified_info_original = modified_info.copy()
        self.modified_info = modified_info.copy()
        self.update_files(trigger_callback=False)
        
        # remove entries in self.modified times that are not in files
        for name in self.modified_info.copy():
            if name not in self.files:
                del self.modified_info[name]
        
        self.main = threading.Thread(target = self.mainloop)
        self.main.daemon = True
        self.running = True
        self.main.start()
        
    def mainloop(self):
        while self.running:
            time.sleep(1)
            with self.lock:
                self.update_files()
                self.check()
    
    def update_files(self, folders=None, trigger_callback=True):
        if folders is None:
            folders = self.folders
        for folder in folders:
            try:
                for name in os.listdir(folder):
                    path = os.path.join(folder, name)
                    if os.path.isdir(path):
                        self.update_files([path], trigger_callback)
                    else:
                        if not path in self.files:
                            self.files.add(path)
                            if trigger_callback:
                                self.callback(path, os.path.getmtime(path), 'created')
            except OSError:
                # Folder has been deleted. File deletion will still be
                # detected, so we can ignore this.
                continue

    
    def check(self):
        for name in self.files:
            try:
                if os.path.splitext(name)[-1] in hashable_types:
                    modified_info = hash_bytestr_iter(file_as_blockiter(open(name, 'rb')), hashlib.md5())
                else:
                    modified_info = os.path.getmtime(name)
            except OSError:
                if not os.path.exists(name):
                    modified_info = None
                else:
                    # If we couldn't get the modified time but the path does exist,
                    # there was probablly some race condition with the path becoming unavailable briefly
                    # we'll skip the rest of the check for now, and leave it up to the next call of check()
                    # to catch any file modification
                    continue
            original_modified_info = self.modified_info_original.setdefault(name, modified_info)
            previous_modified_info = self.modified_info.setdefault(name, modified_info)
            self.modified_info[name] = modified_info
            if modified_info != previous_modified_info:
                if modified_info == original_modified_info:
                    self.callback(name, modified_info, 'restored')     
                elif name in self.modified_info:
                    del self.modified_info[name]
                    self.callback(name, modified_info, 'modified')
                                    
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
        
    def add_files(self,files):
        with self.lock:
            if isinstance(files,str):
                self.files.add(files)
            else:
               self.files = self.files.union(set(files)) 
    
    def add_folders(self,folders):
        with self.lock:
            if isinstance(folders,str):
                self.folders.add(folders)
            else:
               self.folders = self.folders.union(set(folders))
            self.update_files(trigger_callback=False)
            
   
if __name__ == '__main__':
    # Example usage
    
    def callback(name, modified, event='modified'):
        if modified is None:
            print(name, 'has been deleted')
        # else:
        #     print(name, 'was modified at', modified)
        elif event == 'modified':
            print(name, 'was modified at', modified)
        elif event == 'created':
            print(name, 'was modified at', created)
        else:
            print(name, 'was restored (hash {})'.format(modified))

    f = FileWatcher(callback, files='test.txt', folders='foobar')
    
