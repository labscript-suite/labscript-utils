import os
import sys
import socket
import subprocess

import zmq

import zlock
import shared_drive
from LabConfig import LabConfig

if 'h5py' in sys.modules:
    raise ImportError('h5_lock must be imported prior to importing h5py')
        
import h5py

def __init__(self, name, mode=None, driver=None, libver=None, **kwds):
    key = shared_drive.path_to_agnostic(name)
    self.zlock = zlock.Lock(key)
    self.zlock.acquire()
    _orig_init(self, name, mode, driver, libver, **kwds)

def close(self):
    self.zlock.release()
    _orig_close(self)
    
_orig_init = h5py.File.__init__
_orig_close = h5py.File.close
    
# setup connection with the zlock server, depending on labconfig settings: 
config = LabConfig(required_params={'ports':['zlock'],'servers':['zlock']})
host = config.get('servers','zlock')
port = config.get('ports','zlock')
if socket.gethostbyname(host) == socket.gethostbyname('localhost'):
    try:
        # short connection timeout if localhost, don't want to
        # waste time:
        zlock.connect(host,port,timeout=0.1)
    except zmq.ZMQError:
        # No zlock server running on localhost. Start one:
        devnull = open(os.devnull,'w')
        global _server_process
        _server_process = subprocess.Popen([sys.executable,'-m','zlock',port], stdout=devnull, stderr=devnull)
        # Try again. Longer timeout this time, give it time to start up:
        zlock.connect(host,port,timeout=15)
else:
    zlock.connect(host, port)
        
# Replace the h5py File open and close methods with our own, brand
# new shiny locking ones:
h5py.File.__init__ = __init__
h5py.File.close = close 
            
def set_default_timeout(t):
    zlock.set_default_timeout(t)

# 30 seconds seems like a good timeout. The user can increase by calling
# set_default_timeout themselves:

set_default_timeout(30)


