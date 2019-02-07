#####################################################################
#                                                                   #
# qtwidgets/outputbox.py                                            #
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

from labscript_utils import check_version

check_version('qtutils', '2.2.4', '3')

import qtutils.outputbox

from labscript_utils.ls_zprocess import get_config

class OutputBox(qtutils.outputbox.OutputBox):
    """A subclass of qtutils.OutputBox configured with security from labconfig.
    A bit of magic happens at instantiation time to make it actually a subclass of
    OutputBox, because we don't want this module to depend """

    def __init__(self, container, scrollback_lines=1000):
        config = get_config()

        if config['listen_localhost_only']:
            bind_address='tcp://127.0.0.1'
        else:
            bind_address='tcp://0.0.0.0'
        qtutils.outputbox.OutputBox.__init__(
            self,
            container=container,
            scrollback_lines=scrollback_lines,
            bind_address=bind_address, 
            shared_secret=config['shared_secret'],
            allow_insecure=config['allow_insecure']
        )
