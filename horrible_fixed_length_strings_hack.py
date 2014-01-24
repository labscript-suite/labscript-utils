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

import h5py

def horribly_hack_fixed_length_strings():
    _guess_dtype = h5py._hl.base.guess_dtype

    def guess_dtype(data):
        if type(data) not in [bytes, unicode]:
            return _guess_dtype(data)
            
    # I feel dirty:
    h5py._hl.base.guess_dtype = guess_dtype
