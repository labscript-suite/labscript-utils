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

import sys, os
import threading
import traceback
import subprocess
import warnings

subprocess_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tk_exception.py')

class l:
    logger = None

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
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # Cull the top frame so the user doesn't see this wrapping code in their traceback:
            exc_traceback = exc_traceback.tb_next                    
            sys.excepthook(exc_type, exc_value, exc_traceback)
    threading.Thread.run = run
    
def tkhandler(exceptclass,exception,exec_info,reraise=True):
    message = ''.join(traceback.format_exception(exceptclass,exception,exec_info))
    if l.logger:
        l.logger.error('Got an exception:\n%s'%message)
    if exceptclass in [KeyboardInterrupt, SystemExit]:
        sys.__excepthook__(exceptclass,exception,exec_info)
    else:
        subprocess.Popen([sys.executable, subprocess_script_path,
                          os.path.basename(sys.argv[0]), 
                          '%s: %s' % (exceptclass.__name__, exception),
                          message])
        if reraise:
            sys.__excepthook__(exceptclass,exception,exec_info)

def logwarning(message, category, filename, lineno, file=None, line=None):
    logmessage = warnings.formatwarning(message, category, filename, lineno, line)
    l.logger.warn(logmessage)
    warnings._showwarning(message, category, filename, lineno, file, line)

def set_logger(logger):   
    l.logger = logger 
    warnings._showwarning = warnings.showwarning
    warnings.showwarning = logwarning
 
try:
    sys.excepthook = tkhandler
    install_thread_excepthook()
except:
    pass
