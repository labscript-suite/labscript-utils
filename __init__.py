import sys
import linecache
import logging, logging.handlers
import threading

def log(log_path, module_names):
    def get_logger ():
        logger = logging.getLogger('TRACER')
        handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=1024*1024*50)
        formatter = logging.Formatter('%(asctime)s: %(threadName)s: %(message)s')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        return logger
    
    
    def traceit(frame, event, arg):
        if event == "line":
            lineno = frame.f_lineno
            filename = frame.f_globals["__file__"]
            if (filename.endswith(".pyc") or
                filename.endswith(".pyo")):
                filename = filename[:-1]
            name = frame.f_globals["__name__"]
            if name in module_names:
                line = linecache.getline(filename, lineno)
                logger.debug("%s:%s: %s" % (name, lineno, line.rstrip()))
        return traceit
    
    logger = get_logger()
    logger.debug('\n*****STARTING*****\n')
    sys.settrace(traceit)
    threading.settrace(traceit)

