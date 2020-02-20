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
import site
import distutils.sysconfig


# Directories in which the standard library and installed packages may be located.
# Modules in these locations will be whitelisted:
PKGDIRS = [
    distutils.sysconfig.get_python_lib(plat_specific=True, standard_lib=True),
    distutils.sysconfig.get_python_lib(plat_specific=True, standard_lib=False),
    distutils.sysconfig.get_python_lib(plat_specific=False, standard_lib=True),
    distutils.sysconfig.get_python_lib(plat_specific=False, standard_lib=False),
    site.getusersitepackages(),
]
PKGDIRS += site.getsitepackages()
PKGDIRS = set(PKGDIRS)


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
                # Acquire the import lock so that we don't unload modules whilst an
                # import is in progess:
                imp.acquire_lock()
                try:
                    if self.check():
                        self.unload()
                finally:
                    # We're done mucking around with the cached modules, normal imports
                    # in other threads may resume:
                    imp.release_lock()

    def check(self):
        unload_required = False
        # Look through currently loaded modules:
        for name, module in sys.modules.copy().items():
            # Look only at the modules not in the the whitelist:
            if name not in self.whitelist:
                # Only consider modules which have a non-None __file__ attribute, are
                # .py (or .pyc) files (no C extensions or builtin modules), that exist
                # on disk, and that aren't in standard package directories. Add modules
                # we won't consider to the whitelist so that we don't consider them in
                # future calls.
                if getattr(module, '__file__', None) is None:
                    self.whitelist.add(name)
                    continue
                module_file = module.__file__
                if module_file.endswith('.pyc'):
                    module_file = os.path.splitext(module_file)[0] + '.py'
                if not module_file.endswith('.py') or not os.path.exists(module_file):
                    self.whitelist.add(name)
                    continue
                if any(module_file.startswith(s + os.path.sep) for s in PKGDIRS):
                    # Whitelist modules in package install directories:
                    self.whitelist.add(name)
                    continue
                # Check and store the modified time of the .py file:
                modified_time = os.path.getmtime(module_file)
                previous_modified_time = self.modified_times.setdefault(
                    name, modified_time
                )
                self.modified_times[name] = modified_time
                if modified_time != previous_modified_time:
                    # A module has been modified! Unload all modules not in the
                    # whitelist:
                    unload_required = True
                    message = (
                        '%s modified: all non-whitelisted modules ' % module_file
                        + 'will be reloaded next run.\n'
                    )
                    sys.stderr.write(message)
        return unload_required

    def unload(self):
        if self.debug:
            print("ModuleWatcher: whitelist is:")
            for name in sorted(self.whitelist):
                print("    " + name)
            print("\nModuleWatcher: modules unloaded:")
        for name in sorted(sys.modules):
            if name not in self.whitelist:
                # This unloads a module. This is slightly more general than
                # reload(module), but has the same caveats regarding existing
                # references. This also means that any exception in the import will
                # occur later, once the module is (re)imported, rather than now
                # where catching the exception would have to be handled differently.
                del sys.modules[name]
                if name in self.modified_times:
                    del self.modified_times[name]
                if self.debug:
                    print("    " + name)
        # Replace sys.meta_path with the cached whitelist, effectively removing all
        # since-added entries from it. Replacement is done in-place in case other
        # code holds references to sys.meta_path, and to preserve order, since order
        # is relevant.
        sys.meta_path[:] = self.meta_whitelist
