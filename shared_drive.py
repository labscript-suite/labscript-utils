#####################################################################
#                                                                   #
# shared_drive.py                                                   #
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
from labscript_utils.labconfig import LabConfig

_config = LabConfig(required_params={'paths':['shared_drive']})
prefix = _config.get('paths','shared_drive')

# ensure prefix ends with a slash:
if not prefix.endswith(os.path.sep):
    prefix += os.path.sep
    
def path_to_agnostic(path):
    path = os.path.abspath(path)
    if path.startswith(prefix):
        path = path.split(prefix, 1)[1]
        path = os.path.join('Z:\\', path)
        path = path.replace(os.path.sep, '\\')
    return path
    
def path_to_local(path):
    if path.startswith('Z:'):
        path = path.split('Z:\\', 1)[1]
        path = path.replace('\\', os.path.sep)
        path = os.path.join(prefix, path)
    return path

if __name__ == '__main__':
    # test: 
    path = os.path.join(prefix, 'foo','bar','baz')
    agnostic_path = path_to_agnostic(path)
    local_path = path_to_local(agnostic_path)
    assert local_path == path
