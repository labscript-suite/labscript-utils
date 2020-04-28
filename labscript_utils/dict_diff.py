#####################################################################
#                                                                   #
# /dict_diff.py                                                     #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript_utils, in the labscript suite  #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import numpy as np

def dict_diff(dict1, dict2):
    """Return the difference between two dictionaries as a dictionary of key: [val1, val2] pairs.
    Keys unique to either dictionary are included as key: [val1, '-'] or key: ['-', val2]."""
    diff_keys = []
    common_keys = np.intersect1d(list(dict1.keys()), list(dict2.keys()))
    for key in common_keys:
        if np.iterable(dict1[key]):
            if np.any(dict1[key] != dict2[key]):
                diff_keys.append(key)
        else:
            if dict1[key] != dict2[key]:
                diff_keys.append(key)

    dict1_unique = [key for key in dict1.keys() if key not in common_keys]    
    dict2_unique = [key for key in dict2.keys() if key not in common_keys]
                
    diff = {}
    for key in diff_keys:
        diff[key] = [dict1[key], dict2[key]]
    
    for key in dict1_unique:
        diff[key] = [dict1[key], '-']
        
    for key in dict2_unique:
        diff[key] = ['-', dict2[key]]       

    return diff