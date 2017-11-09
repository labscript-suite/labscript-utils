#####################################################################
#                                                                   #
# horrible_dtypes_hack.py                                           #
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


def dtypeslist2dict(list_):
    dtypes = {'names': [], 'formats': []}
    for name, type in list_:
        dtypes['names'].append(name)
        dtypes['formats'].append(type)
    return dtypes
