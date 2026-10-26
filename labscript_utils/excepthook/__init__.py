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

import sys
import os
import threading
import traceback
import subprocess
import warnings

# The maximum number of windows the excepthook will spawn:
MAX_WINDOWS = 10

# If this environment variable is set to a value other than '' or '0', exceptions are
# printed to stderr instead of being shown in a window:
DISABLE_ENV_VAR = 'LABSCRIPT_DISABLE_GRAPHICAL_EXCEPTHOOK'

subprocess_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tk_exception.py')


class l:
    logger = None

child_processes = []
_installed = False
_show_windows = False
_original_showwarning = warnings.showwarning


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
        l.logger.error('Got an exception:\n%s', longmessage)
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
        if not _show_windows:
            reraise = True
        elif len(child_processes) < MAX_WINDOWS + 1:
            process = subprocess.Popen([sys.executable, subprocess_script_path, script, shortmessage, longmessage])
            child_processes.append(process)
        if reraise:
            sys.__excepthook__(exceptclass, exception, exec_info)


def logwarning(message, category, filename, lineno, file=None, line=None):
    logmessage = warnings.formatwarning(message, category, filename, lineno, line)
    l.logger.warn(logmessage)
    _original_showwarning(message, category, filename, lineno, file, line)


def set_logger(logger):
    l.logger = logger
    warnings.showwarning = logwarning

def install():
    """Set `sys.excepthook` to a handler that logs exceptions and shows each one in a
    window, and make uncaught exceptions in threads call `sys.excepthook`. Exceptions
    are printed to stderr instead of being shown in a window if tkinter is not installed
    or if the environment variable `LABSCRIPT_DISABLE_GRAPHICAL_EXCEPTHOOK` is set to a
    value other than '' or '0'. Calls after the first have no effect."""
    global _installed, _show_windows
    if _installed:
        return
    _installed = True
    if os.environ.get(DISABLE_ENV_VAR, '') in ('', '0'):
        # tkinter is part of the standard library but is a separate package on Debian
        # and Ubuntu, so it may be missing:
        try:
            import tkinter
        except ImportError:
            warnings.warn(
                "tkinter is not installed, so exceptions will be printed to stderr "
                "instead of being shown in a window. Install the python3-tk package for "
                "the error windows."
            )
        else:
            _show_windows = True
    sys.excepthook = tkhandler
    install_thread_excepthook()


# TODO: remove this call in a future release, so that importing this module does not
# install the handler. Programs that use the handler call install() themselves.
install()
