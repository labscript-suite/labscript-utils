#####################################################################
#                                                                   #
# h5_lock.py                                                        #
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
import os
import traceback

from labscript_utils.ls_zprocess import Lock, connect_to_zlock_server, kill_lock

from labscript_utils import check_version, dedent

from labscript_utils.shared_drive import path_to_agnostic
from labscript_utils import PY2
if PY2:
    str = unicode

if 'h5py' in sys.modules:
    import labscript_utils.double_import_denier
    import h5py
    denier = labscript_utils.double_import_denier._denier
    if denier is not None and denier.enabled:
        tb = denier._format_tb(denier.tracebacks[os.path.dirname(h5py.__file__)])
        msg = """Error importing h5_lock: h5py has already been imported. h5_lock must
            be imported before any code imports h5py. The above traceback shows where
            h5_lock was imported, and the below traceback shows where h5py was imported
            prior."""
        msg = dedent(msg)
        msg += "\n\nTraceback (h5py import):\n"
        msg += "------------\n%s------------" % tb
        raise ImportError(msg)
    else:
        raise ImportError('h5_lock must be imported prior to importing h5py')
        
import h5py
# This module used to contain a monkeypatch to work around an issue now fixed in h5py.
# Depend on the fix since we no longer have the monkeypatch.
check_version('h5py', '2.9', '3')

_File = h5py.File
class File(_File):
    def __init__(self, name, mode=None, driver=None, libver=None, **kwds):
        if not isinstance(name, h5py._objects.ObjectID):
            kwargs = {}
            if mode == 'r':
                kwargs['read_only'] = True
            # Do not terminate upon SIGTERM while the file is open:
            self.kill_lock = kill_lock
            self.kill_lock.acquire()
            # Ask other zlock users not to open the file while we have it open:
            self.zlock = Lock(path_to_agnostic(name), **kwargs)
            self.zlock.acquire()
        try:
            _File.__init__(self, name, mode, driver, libver, **kwds)
        except:
            if hasattr(self, 'zlock'):
                self.zlock.release()
            if hasattr(self, 'kill_lock'):
                self.kill_lock.release()
            raise

    def close(self):
        _File.close(self)
        if hasattr(self, 'zlock'):
            self.zlock.release()
        if hasattr(self, 'kill_lock'):
            self.kill_lock.release()

    # Overriding __exit__ is crucial. Since h5py.File.__exit__() holds h5py's
    # library-wide lock "phil", it calls close() whilst holding that lock. Our close()
    # method does not need the lock (h5py.File.close() does, but it acquires it itself
    # as needed), but this means they we're holding phil when we call
    # kill_lock.release(), which, in order to be thread-safe, attempts to aquire
    # kill_lock._lock, briefly. If another thread holds kill_lock._lock at the time, and
    # whilst holding it, Python garbage collection runs in that thread, and there are
    # HDF5 objects waiting to be deallocated, then Python deadlocks. This is beause the
    # deallocation in h5py is done while holding phil. But phil is held by our close()
    # method, so deallocation must wait for our close method to return. However our
    # close method is waiting to acquire kill_lock._lock, which will not be released by
    # the other thread until garbage collection is complete. Python hangs.
    #
    # The solution is just not not hold phil in __exit__. It does not appear to be
    # necessary. I will report this as an issue in h5py, and will remove this workaround
    # if it is fixed in a future version.
    def __exit__(self, *args):
        self.close()


def hack_locks_onto_h5py():
    # Monkeypatch h5py so all files are locked:
    h5py.File = File


connect_to_zlock_server()
hack_locks_onto_h5py()
