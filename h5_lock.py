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

import os
import sys
import socket
import threading
import subprocess
import weakref

import zmq
import zprocess.locking
from zprocess.locking import set_default_timeout

import shared_drive
from labscript_utils.labconfig import LabConfig

if 'h5py' in sys.modules:
    raise ImportError('h5_lock must be imported prior to importing h5py')
        
import h5py

DEFAULT_TIMEOUT = 45

def NetworkOnlyLock(name):
    return zprocess.locking.NetworkOnlyLock(shared_drive.path_to_agnostic(name))
    
def hack_locks_onto_h5py():
    def __init__(self, name, mode=None, driver=None, libver=None, **kwds):
        self.zlock = zprocess.locking.Lock(shared_drive.path_to_agnostic(name))
        self.zlock.acquire()
        _orig_init(self, name, mode, driver, libver, **kwds)

    def close(self):
        _orig_close(self)
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
            devnull = open(os.devnull,'w')
            subprocess.Popen([sys.executable,'-m','zprocess.locking'], stdout=devnull, stderr=devnull)
            # Try again. Longer timeout this time, give it time to start up:
            zprocess.locking.connect(host,port,timeout=15)
    else:
        zprocess.locking.connect(host, port)

    # The user can call these functions to change the timeouts later if they
    # are not to their liking:
    set_default_timeout(DEFAULT_TIMEOUT)


connect_to_zlock_server()
hack_locks_onto_h5py()


# begin hack that makes strings fixed-length by default:
from labscript_utils.horrible_fixed_length_strings_hack import horribly_hack_fixed_length_strings
horribly_hack_fixed_length_strings()
# end hack that makes strings fixed-length by default
