import os
from LabConfig import LabConfig

_config = LabConfig(required_params={'paths':['shared_drive']})
_prefix = _config.get('paths','shared_drive')

def path_to_agnostic(path):
    path = os.path.abspath(path)
    if path.startswith(_prefix):
        path = path.replace(_prefix,'Z:')
    path = path.replace(os.path.sep,'\\')
    return path
    
def path_to_local(path):
    path = path.replace('\\', os.path.sep)
    if path.startswith('Z:'):
        path = path.replace('Z:',_prefix)
    return path
