#####################################################################
#                                                                   #
# /setup_logging.py                                                 #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

import sys, os
from socket import gethostbyname
import logging, logging.handlers
import zmq
from labscript_utils.ls_zprocess import Handler, ProcessTree 

import zprocess.zlog
from zprocess import start_daemon
import __main__


_connected_to_zlog = False


def ensure_connected_to_zlog():
    """Ensure we are connected to a zlog server. If one is not running and we are the
    top-level process, start a zlog server configured according to LabConfig."""
    global _connected_to_zlog
    if _connected_to_zlog:
        return
    # setup connection with the zlog server:
    client = ProcessTree.instance().zlog_client
    if gethostbyname(client.host) == gethostbyname('localhost'):
        try:
            # short connection timeout if localhost, don't want to
            # waste time:
            client.ping(timeout=0.05)
        except zmq.ZMQError:
            # No zlog server running on localhost. Start one. It will run forever, even
            # after this program exits. This is important for other programs which might
            # be using it. I don't really consider this bad practice since the server is
            # typically supposed to be running all the time:
            start_daemon([sys.executable, '-m', 'labscript_utils.zlog'])
            # Try again. Longer timeout this time, give it time to start up:
            client.ping(timeout=15)
    else:
        client.ping()
    _connected_to_zlog = True


class LessThanFilter(logging.Filter):
    def __init__(self, less_than):
        self.less_than = less_than
        logging.Filter.__init__(self)
    def filter(self, record):
        return record.levelno < self.less_than


def setup_logging(program_name, log_level=logging.DEBUG, terminal_level=logging.INFO, maxBytes=1024*1024*50, backupCount=1):
    # MayBytes and backupCount args ignored, these are now set in labconfig since they
    # are settings to the server rather than individual logging handlers. Args are left
    # in the function signature for backward compatibility.
    ensure_connected_to_zlog()
    logger = logging.getLogger(program_name)
    # Clear any previously added handlers from the logger:
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    try:
        try:
            program_module = __import__(program_name)
        except ImportError:
            program_module = __import__(program_name.lower())
        main_path = program_module.__file__
    except ImportError:
        main_path = __main__.__file__ if hasattr(__main__, '__file__') else __file__

    log_dir = os.path.dirname(os.path.realpath(main_path))
    log_path = os.path.join(log_dir, '%s.log' % program_name)
    # Add a network logging handler from zprocess:
    handler = Handler(log_path)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logger.addHandler(handler)
    if sys.stdout is not None and sys.stdout.fileno() >= 0:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        stdout_handler.setLevel(terminal_level)
        logger.addHandler(stdout_handler)
        if sys.stderr is not None and sys.stderr.fileno() >= 0:
            # Send warnings and greater to stderr instead of stdout:
            stdout_handler.addFilter(LessThanFilter(logging.WARNING))
            sterr_handler = logging.StreamHandler(sys.stderr)
            sterr_handler.setFormatter(formatter)
            sterr_handler.setLevel(logging.WARNING)
            logger.addHandler(sterr_handler)
    else:
        # Prevent bug on windows where writing to stdout without a command
        # window causes a crash:
        sys.stdout = sys.stderr = open(os.devnull, 'w')
    logger.setLevel(logging.DEBUG)
    return logger
