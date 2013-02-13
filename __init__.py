import os
from LabConfig import LabConfig

_config = LabConfig(required_params={'paths':['shared_drive']})
prefix = _config.get('paths','shared_drive')

Z = 'Z:\\\\'
def path_to_agnostic(path):
    path = os.path.abspath(path)
    if path.startswith(prefix):
        path = os.path.sep.join(path.split(prefix)[1:])
        while path.startswith(os.path.sep):
            path = path[1:]
        path = path.replace(os.path.sep,'\\')
        path = Z + path
    return path
    
def path_to_local(path):
    if path.startswith(Z):
        path = '\\'.join(path.split(Z)[1:])
        path = path.replace('\\', os.path.sep)
        path = os.path.join(prefix, path)
    return path
    
