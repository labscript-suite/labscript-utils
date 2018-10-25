#####################################################################
#                                                                   #
# modulewatcher.py                                                  #
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

import sys
import threading
import time
import os
import imp

class ModuleWatcher(object):
    def __init__(self, debug=False):
        self.debug = debug
        # A lock to hold whenever you don't want modules unloaded:
        self.lock = threading.Lock()
            
        # The whitelist is the list of names of currently loaded modules:
        self.whitelist = set(sys.modules)
        self.meta_whitelist = list(sys.meta_path)
        self.modified_times = {}
        self.main = threading.Thread(target=self.mainloop)
        self.main.daemon = True
        self.main.start()
        
    def mainloop(self):
        while True:
            time.sleep(1)
            with self.lock:
                self.check_and_unload()
            
    def check_and_unload(self):
        # Look through currently loaded modules:
        for name, module in sys.modules.copy().items():
            # Look only at the modules not in the the whitelist:
            if name not in self.whitelist and hasattr(module,'__file__'):
                # Only consider modules which are .py files, no C extensions or builtin
                # modules:
                if module.__file__ is None:
                    continue
                module_file = module.__file__
                if module_file.endswith('.pyc'):
                    module_file = os.path.splitext(module_file)[0] + '.py'
                if not module_file.endswith('.py') or not os.path.exists(module_file):
                    continue
                # Check and store the modified time of the .py file:
                modified_time = os.path.getmtime(module_file)
                previous_modified_time = self.modified_times.setdefault(name, modified_time)
                self.modified_times[name] = modified_time
                if modified_time != previous_modified_time:
                    # A module has been modified! Unload all modules
                    # not in the whitelist:
                    message = '%s modified: all modules will be reloaded next run.\n'%module_file
                    sys.stderr.write(message)
                    if self.debug:
                        print("ModuleWatcher: whitelist is:")
                        for name in sorted(self.whitelist):
                            print("    " + name)
                        print("\nModuleWatcher: modules unloaded:")
                    # Acquire the import lock so that we don't unload
                    # modules whilst an import is in progess:
                    imp.acquire_lock()
                    try:
                        for name in sorted(sys.modules):
                            if name not in self.whitelist:
                                # This unloads a module. This is slightly
                                # more general than reload(module), but
                                # has the same caveats regarding existing
                                # references. This also means that any
                                # exception in the import will occur later,
                                # once the module is (re)imported, rather
                                # than now where catching the exception
                                # would have to be handled differently.
                                del sys.modules[name]
                                if name in self.modified_times:
                                    del self.modified_times[name]
                                if self.debug:
                                    print("    " + name)
                        # Replace sys.meta_path with the cached whitelist,
                        # effectively removing all since-added entries from
                        # it. Replacement is done in-place in case other code
                        # holds references to sys.meta_path, and to preserve
                        # order, since order is relevant.
                        sys.meta_path[:] = self.meta_whitelist
                    finally:
                        # We're done mucking around with the cached
                        # modules, normal imports in other threads
                        # may resume:
                        imp.release_lock()
                            
                            
