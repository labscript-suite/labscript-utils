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

class FileWatcher(object):
    def __init__(self, callback, files=None, folders=None, modified_times=None):
        self.callback = callback
        self.lock = threading.Lock()
        
        self.files = set()
        self.folders = set()
        if files:
            self.add_files(files)
        if folders:
            self.add_folders(folders)
        
        # restore modified times
        if modified_times is None:
            modified_times = {}
        self.modified_times = modified_times.copy()
        self.update_files(trigger_callback=False)
        
        # remove entries in self.modified times that are not in files
        for name in self.modified_times.copy():
            if name not in self.files:
                del self.modified_times[name]
        
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
    
    def update_files(self,folders=None,trigger_callback=True):
        if folders is None:
            folders = self.folders
        for folder in folders:
            try:
                for name in os.listdir(folder):
                    path = os.path.join(folder,name)
                    if os.path.isdir(path):
                        self.update_files([path],trigger_callback)
                    else:
                        if not path in self.files:
                            self.files.add(path)
                            if trigger_callback:
                                self.callback(path,os.path.getmtime(path))
            except OSError:
                # Folder has been deleted. File deletion will still be
                # detected, so we can ignore this.
                continue
    
    def check(self):
        for name in self.files:
            try:
                modified_time = os.path.getmtime(name)
            except OSError:
                if not os.path.exists(name):
                    modified_time = None
                else:
                    # If we couldn't get the modified time but the path does exist,
                    # there was probablly some race condition with the path becoming unavailable briefly
                    # we'll skip the rest of the check for now, and leave it up to the next call of check()
                    # to catch any file modification
                    continue
            previous_modified_time = self.modified_times.setdefault(name, modified_time)
            self.modified_times[name] = modified_time
            if modified_time != previous_modified_time:
                if name in self.modified_times:
                    del self.modified_times[name]
                    self.callback(name,modified_time)
                                    
    def stop(self):
        self.running = False
    
    def add_file(self, path):
        self.add_files(path)
        
    def get_modified_times(self):
        with self.lock:
            times = self.modified_times.copy()
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
    
    def callback(name,modified):
        if modified is None:
            print(name,'has been deleted')
        else:
            print(name, 'was modified at',modified)

    f = FileWatcher(callback, files='test.txt',folders='foobar')
    time.sleep(60)
    
