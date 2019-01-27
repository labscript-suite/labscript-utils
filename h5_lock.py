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

import os
import sys
import socket
import threading
import subprocess
import weakref
from distutils.version import LooseVersion

import zmq
import zprocess.locking
from zprocess.locking import set_default_timeout
from labscript_utils import check_version

check_version('zprocess', '2.2.0', '3.0.0')
from zprocess import start_daemon

from labscript_utils.shared_drive import path_to_agnostic
from labscript_utils.labconfig import LabConfig
from labscript_utils import PY2
if PY2:
    str = unicode

if 'h5py' in sys.modules:
    raise ImportError('h5_lock must be imported prior to importing h5py')
        
import h5py
# This module used to contain a monkeypatch to work around an issue now fixed in h5py.
# Depend on the fix since we no longer have the monkeypatch.
check_version('h5py', '2.9', '3')

DEFAULT_TIMEOUT = 45
_server_supports_readwrite = False

def hack_locks_onto_h5py():
    def __init__(self, name, mode=None, driver=None, libver=None, **kwds):
        if not isinstance(name, h5py._objects.ObjectID):
            kwargs = {}
            if _server_supports_readwrite and mode == 'r':
                kwargs['read_only'] = True
            self.zlock = zprocess.locking.Lock(path_to_agnostic(name), **kwargs)
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

def connect_to_zlock_server():
    # setup connection with the zprocess.locking server, depending on labconfig settings: 
    config = LabConfig(required_params={'ports':['zlock'],'servers':['zlock']})
    host = config.get('servers','zlock')
    port = config.get('ports','zlock')
    if socket.gethostbyname(host) == socket.gethostbyname('localhost'):
        try:
            # short connection timeout if localhost, don't want to
            # waste time:
            zprocess.locking.connect(host,port,timeout=0.05)
        except zmq.ZMQError:
            # No zprocess.locking server running on localhost. Start one. It will run
            # forever, even after this program exits. This is important for
            # other programs which might be using it. I don't really consider
            # this bad practice since the server is typically supposed to
            # be running all the time:
            start_daemon([sys.executable, '-m', 'zprocess.locking'])
            # Try again. Longer timeout this time, give it time to start up:
            zprocess.locking.connect(host,port,timeout=15)
    else:
        zprocess.locking.connect(host, port)

    # Check if the zlock server supports read-write locks:
    global _server_supports_readwrite
    if hasattr(zprocess.locking, 'get_protocol_version'):
        version = zprocess.locking.get_protocol_version()
        if LooseVersion(version) >= LooseVersion('1.1.0'):
            _server_supports_readwrite = True

    # The user can call these functions to change the timeouts later if they
    # are not to their liking:
    set_default_timeout(DEFAULT_TIMEOUT)


connect_to_zlock_server()
hack_locks_onto_h5py()
