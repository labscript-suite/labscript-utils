from redis import Redis
from redis.client import Lock

# Ensure locks get released at sysexit:
Lock.__del__ = Lock.release

def set_server(host):
    global redis
    redis = Redis(host)
    
def set_lock(name):
    global lock
    lock = redis.lock(name)
    
def acquire_lock():
    lock.acquire()
    
def release_lock():
    lock.release()
    

