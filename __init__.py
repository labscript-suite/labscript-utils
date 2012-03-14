import os,sys,subprocess,time,itertools

def get_prefix_linux(share):
    home = os.environ['HOME']
    gvfs = os.path.join(home,'.gvfs')
    for mount in os.listdir(gvfs):
        thisshare, on, thisserver = mount.split()
        if thisshare == share:
            return os.path.join(gvfs,mount)
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
            return drive_letter
    raise RuntimeError('Share isn\'t mounted')
    
def get_prefix(share):
    if os.name == 'nt':
        return get_prefix_win(share)
    elif 'linux' in sys.platform:
        return get_prefix_linux(share)
    else:
        raise OSError('Can\'t get shareed drive prefix on this platform')
if __name__ == '__main__':
    print 'monashbec prefix is:', get_prefix('monashbec')
