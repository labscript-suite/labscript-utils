import os
import sys
import socket
import threading
import subprocess
import weakref

import zmq
import zlock
from zlock import set_default_timeout, set_cache_time

import shared_drive
from LabConfig import LabConfig

if 'h5py' in sys.modules:
    raise ImportError('h5_lock must be imported prior to importing h5py')
        
import h5py

DEFAULT_TIMEOUT = 15
MIN_CACHE_TIME = 0.1
MAX_CACHE_TIME = 1

def hack_locks_onto_h5py():
    def __init__(self, name, mode=None, driver=None, libver=None, **kwds):
        self.zlock = zlock.Lock(shared_drive.path_to_agnostic(name))
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
    # setup connection with the zlock server, depending on labconfig settings: 
    config = LabConfig(required_params={'ports':['zlock'],'servers':['zlock']})
    host = config.get('servers','zlock')
    port = config.get('ports','zlock')
    if socket.gethostbyname(host) == socket.gethostbyname('localhost'):
        try:
            # short connection timeout if localhost, don't want to
            # waste time:
            zlock.connect(host,port,timeout=0.05)
        except zmq.ZMQError:
            # No zlock server running on localhost. Start one. It will run
            # forever, even after this program exits. This is important for
            # other programs which might be using it. I don't really consider
            # this bad practice since the server is typically supposed to
            # be running all the time:
            devnull = open(os.devnull,'w')
            subprocess.Popen([sys.executable,'-m','zlock'], stdout=devnull, stderr=devnull)
            # Try again. Longer timeout this time, give it time to start up:
            zlock.connect(host,port,timeout=15)
    else:
        zlock.connect(host, port)

    # The user can call these functions to change the timeouts later if they
    # are not to their liking:
    set_default_timeout(DEFAULT_TIMEOUT)
    set_cache_time(MIN_CACHE_TIME, MAX_CACHE_TIME)


#connect_to_zlock_server()
#hack_locks_onto_h5py()


# begin hack that makes strings fixed-length by default:
from horrible_fixed_length_strings_hack import horribly_hack_fixed_length_strings
horribly_hack_fixed_length_strings()
# end hack that makes strings fixed-length by default
