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
import qtutils.outputbox

from labscript_utils.ls_zprocess import Context


class OutputBox(qtutils.outputbox.OutputBox):
    """A subclass of qtutils.outputbox.OutputBox configured with security from
    labconfig."""

    def __init__(self, container, scrollback_lines=1000):
        context = Context.instance()
        # Since we are using our Context, which is a subclass of
        # zprocess.security.SecureContext, we can listen on public interfaces. Insecure
        # messages arriving from external interfaces will be disacarded
        qtutils.outputbox.OutputBox.__init__(
            self,
            container=container,
            scrollback_lines=scrollback_lines,
            zmq_context=context,
            bind_address='tcp://0.0.0.0',
        )
