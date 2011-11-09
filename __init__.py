import threading, sys, os, traceback, subprocess
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
    
def gtkhandler(exceptclass,exception,exec_info):
    if exceptclass in [KeyboardInterrupt, SystemExit]:
        sys.__excepthook__(exceptclass,exception,exec_info)
    else:
        message = ''.join(traceback.format_exception(exceptclass,exception,exec_info))
        subprocess.Popen(['python','-m''excepthook.gtk_exception',
                          os.path.basename(sys.argv[0]), 
                          '%s: %s' % (exceptclass.__name__, exception),
                          message])
        sys.__excepthook__(exceptclass,exception,exec_info)
    
sys.excepthook = gtkhandler
install_thread_excepthook()

