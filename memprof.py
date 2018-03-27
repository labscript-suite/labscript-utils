#####################################################################
#                                                                   #
# memprof.py                                                        #
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

import gc

class MemoryProfiler(object):
    """Class to count number instances of each type in the interpreter in order to
    detect Python memory leaks"""
    def __init__(self):
        self.filepath = None
        self.initial_counts = None

    def count_types(self):
        types = {}
        for obj in gc.get_objects():
            try:
                c = obj.__class__
            except AttributeError:
                c = type(obj)
            try:
                types[c] += 1
            except KeyError:
                types[c] = 1
        self.write_to_file(types)
        return types
        
    def write_to_file(self, types):
        with open(self.filepath, 'w') as f:
            names = list(types.keys())
            names.sort(key=lambda name: -types[name])
            for name in names:
                f.write(str(name).rjust(60) + ' ' +
                        str(types[name]).rjust(8) + '\n')
                
    def start(self, filepath='memprof.txt'):
        self.filepath = filepath
        self.initial_counts = self.count_types()
              
    def check(self):
        diffs = {}
        types = self.count_types()
        for type_ in types:
            try:
                diffs[type_] = types[type_] - self.initial_counts[type_]
            except KeyError:
                diffs[type_] = types[type_]
        self.write_to_file(diffs)
        return True
    

_memory_profiler = MemoryProfiler()
start = _memory_profiler.start
check = _memory_profiler.check
