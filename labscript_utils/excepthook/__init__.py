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
import sys
import os
import threading
import traceback
import subprocess
import warnings

# The maximum number of windows the excepthook will spawn:
MAX_WINDOWS = 10

subprocess_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tk_exception.py')


class l:
    logger = None

child_processes = []


def install_thread_excepthook():
    """
    Workaround for sys.excepthook thread bug
    (https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1230540&group_id=5470).
    Call once from __main__ before creating any threads.
    """
    run_old = threading.Thread.run

    def run(*args, **kwargs):
        try:
            run_old(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if sys is None:
                # Interpreter is shutting down. Don't display graphical error.
                # Let the threading module's code handle this however it normally does.
                raise
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # Cull the top frame so the user doesn't see this wrapping code in their traceback:
            exc_traceback = exc_traceback.tb_next
            sys.excepthook(exc_type, exc_value, exc_traceback)
    threading.Thread.run = run


def tkhandler(exceptclass, exception, exec_info, reraise=True):
    script = os.path.basename(sys.argv[0])
    if not script:
        script = 'python interactive shell'
    shortmessage = '%s: %s' % (exceptclass.__name__, exception)
    longmessage = ''.join(traceback.format_exception(exceptclass, exception, exec_info))
    if l.logger:
        l.logger.error('Got an exception:\n%s' % longmessage)
    if exceptclass in [KeyboardInterrupt, SystemExit]:
        sys.__excepthook__(exceptclass, exception, exec_info)
    else:
        for previous_process in child_processes[:]:
            if previous_process.poll() is not None:
                child_processes.remove(previous_process)
        if len(child_processes) >= MAX_WINDOWS:
            shortmessage = "Too many errors"
            longmessage = ("Too many errors: Further errors will " +
                           "not be shown graphically until some error windows are closed")
        if len(child_processes) < MAX_WINDOWS + 1:
            process = subprocess.Popen([sys.executable, subprocess_script_path, script, shortmessage, longmessage])
            child_processes.append(process)
        if reraise:
            sys.__excepthook__(exceptclass, exception, exec_info)


def logwarning(message, category, filename, lineno, file=None, line=None):
    logmessage = warnings.formatwarning(message, category, filename, lineno, line)
    l.logger.warn(logmessage)
    warnings._showwarning(message, category, filename, lineno, file, line)


def set_logger(logger):
    l.logger = logger
    warnings._showwarning = warnings.showwarning
    warnings.showwarning = logwarning

# Check for tkinter availability. Tkinter is frustratingly not available
# by default for python 3.x on Debian systems, despite being considered
# part of the Python standard library. I'll make it a dependency for
# packaging, but this is an extra check at runtime so that if something
# goes wrong with that we get an error at import rather than later:
if sys.version_info[0] == 2:
    import Tkinter
else:
    import tkinter
sys.excepthook = tkhandler
install_thread_excepthook()
