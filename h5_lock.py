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

from labscript_utils.ls_zprocess import Lock, connect_to_zlock_server

from labscript_utils import check_version

from labscript_utils.shared_drive import path_to_agnostic
from labscript_utils import PY2
if PY2:
    str = unicode

if 'h5py' in sys.modules:
    raise ImportError('h5_lock must be imported prior to importing h5py')
        
import h5py
# This module used to contain a monkeypatch to work around an issue now fixed in h5py.
# Depend on the fix since we no longer have the monkeypatch.
check_version('h5py', '2.9', '3')

def hack_locks_onto_h5py():
    def __init__(self, name, mode=None, driver=None, libver=None, **kwds):
        if not isinstance(name, h5py._objects.ObjectID):
            kwargs = {}
            if mode == 'r':
                kwargs['read_only'] = True
            self.zlock = Lock(path_to_agnostic(name), **kwargs)
            self.zlock.acquire()
        try:
            _orig_init(self, name, mode, driver, libver, **kwds)
        except:
            if hasattr(self, 'zlock'):
                self.zlock.release()
            raise

    def close(self):
        _orig_close(self)
        if hasattr(self, 'zlock'):
            self.zlock.release()

    # Store the original open and close methods so they can still be called
    # by our replacements:
    _orig_init = h5py.File.__init__
    _orig_close = h5py.File.close

    # Replace the h5py File open and close methods with our own, brand
    # new shiny locking ones:
    h5py.File.__init__ = __init__
    h5py.File.close = close 


connect_to_zlock_server()
hack_locks_onto_h5py()
