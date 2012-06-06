import sys
from redis import Redis

def turn_locks_on(redis_server='localhost'):

    if 'h5py' in sys.modules:
        raise ImportError('h5_lock.turn_locks_on must be celled prior to importing h5py')
        
    import h5py

    _orig_init = h5py.File.__init__
    _orig_close = h5py.File.close
    
    def __init__(self, name, mode=None, driver=None, libver=None, **kwds):
        self.redislock = None
        if mode != 'r':
            self.redislock = redis.lock(name)
            self.redislock.acquire()
        _orig_init(self, name, mode=None, driver=None, libver=None, **kwds)

    def close(self):
        if self.redislock is not None:
            self.redislock.release()
        _orig_close(self)  
        
    redis = Redis(redis_server)
    h5py.File.__init__ = __init__
    h5py.File.close = close        

if __name__ == '__main__':
    import time
    turn_locks_on()
    import h5py
    with h5py.File('a') as f:
        print 'starting!'
        time.sleep(5)
        print 'ending!'
