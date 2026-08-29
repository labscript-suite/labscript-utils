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

__all__ = ['FILEPATH_COLUMN', 'ShotQueueTreeView', 'ShotQueueWidget']


def __getattr__(name):
    if name not in __all__:
        raise AttributeError("module %r has no attribute %r" % (__name__, name))

    from .shotqueue import FILEPATH_COLUMN, ShotQueueTreeView, ShotQueueWidget

    exports = {
        'FILEPATH_COLUMN': FILEPATH_COLUMN,
        'ShotQueueTreeView': ShotQueueTreeView,
        'ShotQueueWidget': ShotQueueWidget,
    }
    globals().update(exports)
    return exports[name]


def __dir__():
    return sorted(list(globals().keys()) + __all__)
