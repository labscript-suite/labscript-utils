#####################################################################
#                                                                   #
# brute_import.py                                                   #
#                                                                   #
# Copyright 2017, Chris Billington                                  #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################


import sys
import os
import types
import imp
import marshal


def _fallback(module_name):
    # No module code to execute? Just import the usual way then and return an
    # empty module upon exception:
    try:
        module = __import__(module_name)
        return module, None
    except Exception:
        module = types.ModuleType(module_name)
        return module, sys.exc_info()


def brute_import(module_name):
    """Execute a module as if it were being imported, catch exceptions, and
    return the (possibly only partially initialised) module object as well as
    the exc_info for the exception (or None if there was no exception). This
    is useful for say, inspecting the __version__ string of a module that is
    failing to import in order to raise a potentially more useful exception if
    the module is failing to import *because* it is the wrong version."""

    sourcefile, pathname, (_, _, module_type) = imp.find_module(module_name)
    module = types.ModuleType(module_name)
    sys.modules[module_name] = module

    if module_type in [imp.PY_SOURCE, imp.PY_COMPILED]:
        module.__file__ = pathname
    elif module_type == imp.PKG_DIRECTORY:
        module.__path__ = [pathname]
        module.__file__ = os.path.join(pathname, '__init__.py')
        sourcefile = open(module.__file__)
    else:
        return _fallback(module_name)

    if module_type in [imp.PY_SOURCE, imp.PKG_DIRECTORY]:
        code = compile(sourcefile.read(), module.__file__, 'exec', dont_inherit=True)
    elif module_type == imp.PY_COMPILED:
        if sourcefile.read(4) != imp.get_magic():
            # Different python version, we can't execute:
            return _fallback(module_name)
        # skip timestamp:
        _ = sourcefile.read(4)
        code = marshal.load(sourcefile)
    else:
        # Some C extension or something. No code for us to execute.
        return _fallback(module_name)
        
    try:
        # Execute the module code in its namespace:
        exec(code, module.__dict__)
        return module, None
    except Exception:
        exc_info = sys.exc_info()
        return module, sys.exc_info()
