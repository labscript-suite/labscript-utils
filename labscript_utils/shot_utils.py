#####################################################################
#                                                                   #
# __init__.py                                                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

import h5py
import numpy as np

def get_shot_globals(filepath):
    """Returns the evaluated globals for a shot, for use by labscript or lyse.
    Simple dictionary access as in dict(h5py.File(filepath).attrs) would be fine
    except we want to apply some hacks, so it's best to do that in one place."""
    params = {}
    with h5py.File(filepath, 'r') as f:
        for name, value in f['globals'].attrs.items():
            # Convert numpy bools to normal bools:
            if isinstance(value, np.bool_):
                value = bool(value)
            # Convert null HDF references to None:
            if isinstance(value, h5py.Reference) and not value:
                value = None
            # Convert numpy strings to Python ones.
            # DEPRECATED, for backward compat with old files.
            if isinstance(value, np.str_):
                value = str(value)
            if isinstance(value, bytes):
                value = value.decode()
            params[name] = value
    return params