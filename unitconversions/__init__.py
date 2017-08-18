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
from __future__ import division, unicode_literals, print_function, absolute_import

import os
for module in os.listdir(os.path.split(__file__)[0]):
    if module.endswith('.py'):
        exec('from .%s import *'%module[:-3])
del module
