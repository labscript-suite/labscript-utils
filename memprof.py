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

import gc

def count_types():
    types = {}
    for object in gc.get_objects():
        try:
            c = object.__class__
        except AttributeError:
            c = type(object)
        try:
            types[c] += 1
        except KeyError:
            types[c] = 1
    write_to_file(types)
    return types
    
def write_to_file(types):
    with open('memprof.txt','w') as f:
        names = types.keys()
        names.sort(key=lambda name: -types[name])
        for name in names:
            f.write(str(name).rjust(60) + ' ' + str(types[name]).rjust(8) + '\n')
            
def start():
    global initial_counts
    initial_counts = count_types()
          
def check():
    diffs = {}
    types = count_types()
    for type in types:
        try:
            diffs[type] = types[type] - initial_counts[type]
        except KeyError:
            diffs[type] = types[type]
    write_to_file(diffs)
    return True
    
start()

