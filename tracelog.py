#####################################################################
#                                                                   #
# tracelog.py                                                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

import os, sys
import inspect
import linecache
import logging, logging.handlers
import threading
from datetime import datetime

def set_file(log_path):
    # Append if file is under 50MB, else replace it with a new file:
    global outfile
    if log_path is None:
        outfile = sys.stdout
    elif os.path.exists(log_path) and os.path.getsize(log_path) < 50*1024*1024:
        outfile = open(log_path, 'a',0)
    else:
        outfile = open(log_path, 'w',0)
        
def log(log_path, module_names=[], sub = False, all=False):
    
    # For well formed lines in multithreaded programs:
    writelock = threading.Lock()
    
    set_file(log_path)
    
    def write(module_name, lineno, function, line):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] # chop microseconds to milliseconds
        threadname = threading.current_thread().name
        message = "[%s] %s: %s:%s in %s: %s\n" % (timestamp, threadname, module_name, lineno, function, line)
        with writelock:
            outfile.write(message)
        
    def traceit(frame, event, arg):
        if event == "line":
            filename, lineno, function, code_context, index = inspect.getframeinfo(frame, context=1)
            try:
                module_name = frame.f_globals["__name__"]
            except KeyError:
                module_name = '<string>'
            if module_name in module_names or all or (sub and any([module_name.startswith(s) for s in module_names])):
                line = code_context[0].rstrip() if code_context else '<within exec() or eval()>'
                write(module_name, lineno, function, line)
        return traceit
                    
    write('tracelog','','','\n\n***starting***\n')
    threading.settrace(traceit)
    sys.settrace(traceit)
    

