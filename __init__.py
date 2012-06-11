import sys, os
import threading
import traceback
import subprocess
import warnings

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
            sys.excepthook(*sys.exc_info())
    threading.Thread.run = run
    
def gtkhandler(exceptclass,exception,exec_info,reraise=True):
    message = ''.join(traceback.format_exception(exceptclass,exception,exec_info))
    if l.logger:
        l.logger.error('Got an exception:\n%s'%message)
    if exceptclass in [KeyboardInterrupt, SystemExit]:
        sys.__excepthook__(exceptclass,exception,exec_info)
    else:
        subprocess.Popen(['python','-m''excepthook.gtk_exception',
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
    
sys.excepthook = gtkhandler
install_thread_excepthook()

