import os, sys
import linecache
import logging, logging.handlers
import threading
from datetime import datetime

def log(log_path, module_names, sub = False, all=False):

    # Append if file is under 50MB, else replace it with a new file:
    if os.path.exists(log_path) and os.path.getsize(log_path) < 50*1024*1024:
        outfile = open(log_path, 'a',0)
    else:
        outfile = open(log_path, 'w',0)
    
    # For well formed lines in multithreaded programs:
    writelock = threading.Lock()
    
    def write(module_name, lineno, line):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] # chop microseconds to milliseconds
        threadname = threading.current_thread().name
        message = "[%s] %s: %s:%s: %s\n" % (timestamp, threadname, module_name, lineno, line)
        with writelock:
            outfile.write(message)
        
    def traceit(frame, event, arg):
        if event == "line":
            lineno = frame.f_lineno
            try:
                filename = frame.f_globals["__file__"]
            except KeyError:
                filename = '<string>'
            if (filename.endswith(".pyc") or
                filename.endswith(".pyo")):
                filename = filename[:-1]
            try:
                module_name = frame.f_globals["__name__"]
            except KeyError:
                module_name = '<string>'
            if module_name in module_names or all or (sub and sub in module_name):
                line = linecache.getline(filename, lineno)
                write(module_name, lineno, line.rstrip())
        return traceit
                    
    write('tracelog','','\n\n***starting***\n')
    sys.settrace(traceit)
    threading.settrace(traceit)
    

