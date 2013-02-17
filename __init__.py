import os
from LabConfig import LabConfig

_config = LabConfig(required_params={'paths':['shared_drive']})
prefix = _config.get('paths','shared_drive')

def path_to_agnostic(path):
    path = os.path.abspath(path)
    if path.startswith(prefix):
        path = os.path.sep.join(path.split(prefix)[1:])
        path = os.path.join('Z:', path)
        path = path.replace(os.path.sep,'\\')
    return path
    
def path_to_local(path):
    if path.startswith('Z:'):
        path = '\\'.join(path.split('Z:\\')[1:])
        path = path.replace('\\', os.path.sep)
        path = os.path.join(prefix, path)
    return path
    
path = os.path.join(prefix, 'foo/bar/baz/qux')
x = path_to_agnostic(path)
y = path_to_local(x)
