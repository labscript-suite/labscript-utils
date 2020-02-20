#####################################################################
#                                                                   #
# numpy_dtype_workaround.py                                         #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2

def dtype_workaround(dtypes):
    """Convert names specified in compound datatype tuples to the native
    string type. This is a workaround for numpy issue #2407 until the fix
    becomes available:
    https://github.com/numpy/numpy/issues/2407
    """
    if PY2:
        return [(bytes(name), dtype) for name, dtype in dtypes]
    return dtypes