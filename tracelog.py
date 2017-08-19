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
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

import os, sys
import inspect
import threading
from datetime import datetime
import traceback 

def log(log_path=None, module_names=(), sub=False, all=False, mode='w'):
    """Trace and log Python execution.
    
    output includes the time, thread name, containing function name, line number and source line. 
    Indentation before the thread name represents stack depth, indentation before source line is as in the source line itself.
    
    log_path: the path of the desired output file to write to, or None for stdout (default=None)
    module_names: list of module names that tracing is desired for (default=())
    sub: whether submodules of the above modules should be traced (default=False)
    all: whether all modules should be traced, in which case module_names is ignored (default=False)
    mode: mode to open the output file in, if log_path is not None (default='w')
    """
    
    if log_path is None:
        outfile = sys.stdout
    else:
        outfile = open(log_path, mode, 1)
    
    threadlocal = threading.local()
    
    def per_thread_init():
        threadlocal.stack_depth = 0
        threadlocal.threadname = threading.current_thread().name
        threadlocal.is_initialised = True
        
    def write(module_name, lineno, function, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] # chop microseconds to milliseconds
        indentation = ' '*(2*threadlocal.stack_depth - 1)
        output = "[%s]%s%s: %s:%s in %s: " % (timestamp, indentation, threadlocal.threadname, module_name, lineno, function)
        if isinstance(message, list):
            indent = len(output)
            output += message[0]
            for line in message[1:]:
                output += ' '*indent + line
        else:
            output += message + '\n'
        
        # This is atomic, thanks to the GIL, so we don't need to serialise access from multiple threads:
        outfile.write(output)
        
    def traceit(frame, event, arg):
        if sys is None:
            # Interpreter is shutting down
            return
        try:
            assert threadlocal.is_initialised
        except AttributeError:
            per_thread_init()
        if event == "call":
            threadlocal.stack_depth += 1
        elif event == "return":
            threadlocal.stack_depth -= 1
        else:
            filename, lineno, function, code_context, index = inspect.getframeinfo(frame, context=1)
            try:
                module_name = frame.f_globals["__name__"]
            except KeyError:
                module_name = '<string>'
            if module_name in module_names or all or (sub and any([module_name.startswith(s) for s in module_names])):
                line = code_context[0].rstrip() if code_context else '<within exec() or eval()>'
                if event == 'line':
                    write(module_name, lineno, function, line)
                elif event == 'exception':
                    exc_type, exc_value, _ = arg
                    exception = traceback.format_exception_only(exc_type, exc_value)
                    write(module_name, lineno, function, exception)
        return traceit
             
    per_thread_init()
    write('tracelog','','','\n\n***starting***\n')
    threading.settrace(traceit)
    sys.settrace(traceit)
    
    
    
    

