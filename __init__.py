import os,sys,subprocess,time,itertools

def get_prefix_linux(share):
    home = os.environ['HOME']
    gvfs = os.path.join(home, '.gvfs')
    # check if gvfs has been used to mount the filesystem
    if os.path.exists(gvfs):
        for mount in os.listdir(gvfs):
            if share in mount:
                return os.path.join(gvfs, mount)
    # otherwise check conventional locations
    with open('/proc/mounts') as f:
        mounts = f.read().split('\n')
    for mount in mounts:
        if len(mount.split()) > 1:
            file_system, mount_point = mount.split()[:2]
            if share in file_system:
                return mount_point
    raise RuntimeError('Share isn\'t mounted')
    
def get_prefix_win(share):
    import win32com.client
    def grouper(n, iterable, fillvalue=None):
        "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return itertools.izip_longest(fillvalue=fillvalue, *args)
    network = win32com.client.Dispatch('WScript.Network')            
    drives = network.EnumNetworkDrives()
    result = dict(grouper(2, drives))
    for drive_letter,network_path in result.items():        
        if drive_letter and share in network_path:
            return drive_letter + os.sep
    raise RuntimeError('Share isn\'t mounted')

def get_prefix_macos(share):
    volumes = os.path.join('/Volumes')
    # check if gvfs has been used to mount the filesystem
    for mount in os.listdir(volumes):
        if share in mount:
            return os.path.join(volumes, mount)
    raise RuntimeError('Share isn\'t mounted')
        
def get_prefix(share):
    if os.name == 'nt':
        return get_prefix_win(share)
    elif 'linux' in sys.platform:
        return get_prefix_linux(share)
    elif 'darwin' in sys.platform:
        return get_prefix_macos(share)
    else:
        raise OSError('Can\'t get shareed drive prefix on this platform')
    
if __name__ == '__main__':
    print 'monashbec prefix is:', get_prefix('monashbec')
