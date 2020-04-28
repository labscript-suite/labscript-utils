#####################################################################
#                                                                   #
# testing_utils.py                                                  #
#                                                                   #
# Copyright 2017, Chris Billington                                  #
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

import os
import sys
import time
import threading
import unittest
if PY2:
    import Queue as queue
    import mock
else:
    import queue
    import unittest.mock as mock

from unittest import TestCase


class monkeypatch(object):
    """Context manager to temporarily monkeypatch an object attribute with
    some mocked attribute"""

    def __init__(self, obj, name, mocked_attr):
        self.obj = obj
        self.name = name
        self.real_attr = getattr(obj, name)
        self.mocked_attr = mocked_attr

    def __enter__(self):
        setattr(self.obj, self.name, self.mocked_attr)

    def __exit__(self, *args):
        setattr(self.obj, self.name, self.real_attr)


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Any(object):
    """A class whose instances equal any object of the given type or tuple of
    types. For use with mock.Mock.assert_called_with when you don't care what
    some of the arguments are"""
    def __init__(self, types=object):
        if isinstance(types, type):
            self.types = (types,)
        else:
            self.types = types

    def __eq__(self, other):
        return any(isinstance(other, type_) for type_ in self.types)

# Instance of Any() that does not specify type:
ANY = Any()


class ThreadTestCase(TestCase):
    """Test case that runs tests in a new thread whilst providing a mainloop
    that allows running scripts in the current thread. Those scripts can then
    be tested from the testing thread."""

    def __init__(self, *args, **kwargs):
        TestCase.__init__(self, *args, **kwargs)
        self._thread_return_value = queue.Queue()
        self._command_queue = queue.Queue()

    def run_script_as_main(self, filepath):
        globals_dict = dotdict()
        self._command_queue.put([filepath, globals_dict])
        return globals_dict

    def quit_mainloop(self):
        self._command_queue.put([None, None])

    def _run(self, *args, **kwargs):
        """Called in a thread to run the tests"""
        exception = None
        try:
            print('about to run')
            result = TestCase.run(self, *args, **kwargs)
        except:
            print('got exception')
            self.quit_mainloop()
            # Store for re-raising the exception in the calling thread:
            exception = sys.exc_info()
            result = None
        finally:
            self._thread_return_value.put([result, exception])

    def run(self, *args, **kwargs):
        test_thread = threading.Thread(target=self._run, args=args, kwargs=kwargs)
        test_thread.start()
        self._mainloop()
        test_thread.join()
        result, exception = self._thread_return_value.get()
        if exception is not None:
            type, value, traceback = exception
            if PY2:
                exec('raise type, value, traceback')
            else:
                raise value.with_traceback(traceback)
        return result

    def _mainloop(self):
        while True:
            filepath, globals_dict = self._command_queue.get()
            if filepath is None:
                break
            
            if PY2:
                filepath_native_string = filepath.encode(sys.getfilesystemencoding())
            else:
                filepath_native_string = filepath

            globals_dict['__name__'] ='__main__'
            globals_dict['__file__']= os.path.basename(filepath_native_string)
                                       
            # Save the current working directory before changing it to the
            # location of the script:
            cwd = os.getcwd()
            os.chdir(os.path.dirname(filepath))

            # Run the script:
            try:
                with open(filepath) as f:
                    code = compile(f.read(), os.path.basename(filepath_native_string),
                                   'exec', dont_inherit=True)
                    exec(code, globals_dict)
            finally:
                os.chdir(cwd)

    @staticmethod
    def wait_for(condition_func, timeout=5,
                 initial_poll_interval=0.005, max_poll_interval=0.5):
        """Busy wait for a condition to be true. Uses exponential backoff so
        it's fast when things are fast and not a complete hog when they're
        not"""
        poll_interval = initial_poll_interval
        start_time = time.time()
        while not condition_func():
            if time.time() - start_time > timeout:
                raise Exception
            time.sleep(poll_interval)
            poll_interval = min(2*poll_interval, max_poll_interval)
