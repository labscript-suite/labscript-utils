#####################################################################
#                                                                   #
# horrible_fixed_length_strings_hack.py                             #
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
if PY2:
    str = unicode

import h5py

def horribly_hack_fixed_length_strings():
    _guess_dtype = h5py._hl.base.guess_dtype

    def guess_dtype(data):
        if type(data) not in [bytes, str]:
            return _guess_dtype(data)
            
    # I feel dirty:
    h5py._hl.base.guess_dtype = guess_dtype
