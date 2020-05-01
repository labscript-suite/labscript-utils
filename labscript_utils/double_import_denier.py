#####################################################################
#                                                                   #
# double_import_denier.py                                           #
#                                                                   #
# Copyright 2018, Chris Billington                                  #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import sys
import os
import traceback
import re
import importlib.util


DEBUG = False
# Tensorflow contains true double imports. This is arguably a bug in tensorflow,
# (reported here: https://github.com/tensorflow/tensorflow/issues/35369), but let's work
# around it since tensorflow is not our problem:
WHITELIST = ['tensorflow', 'tensorflow_core']


class DoubleImportDenier(object):
    """A module finder that tracks what's been imported and disallows multiple
    imports of the same module under different names, raising an exception
    upon detecting that this has occured"""
    def __init__(self):
        self.enabled = False
        self.names_by_filepath = {}
        self.tracebacks = {}
        UNKNOWN = ('<unknown: imported prior to double_import_denier.enable()>\n')
        for name, module in list(sys.modules.items()):
            if getattr(module, '__file__', None) is not None:
                path = os.path.realpath(module.__file__)
                if os.path.splitext(os.path.basename(path))[0] == '__init__':
                    # Import path for __init__.py is actually the folder they're in, so
                    # use that instead
                    path = os.path.dirname(path)
                self.names_by_filepath[path] = name
                self.tracebacks[path] = [UNKNOWN, '']

        self.stack = set()

    def find_spec(self, fullname, path=None, target=None):
        # Prevent recursion. If importlib.util.find_spec was called by us and is looking
        # through sys.meta_path for finders, return None so it moves on to the other
        # loaders.
        dict_key = (fullname, tuple(path) if path is not None else None)
        if dict_key in self.stack:
            return
        self.stack.add(dict_key)
        try:
            spec = importlib.util.find_spec(fullname, path)
        except Exception as e:
            if DEBUG: print('Exception in importlib.util.find_spec ' + str(e))
            return
        finally:
            self.stack.remove(dict_key)

        if spec is not None and spec.origin is not None and spec.origin != "built-in":
            path = os.path.realpath(spec.origin)
            if DEBUG: print('loading', fullname, 'from', path)
            tb = traceback.format_stack()
            other_name = self.names_by_filepath.get(path, None)
            if fullname.split('.', 1)[0] not in WHITELIST:
                if other_name is not None and other_name != fullname:
                    other_tb = self.tracebacks[path]
                    self._raise_error(path, fullname, tb, other_name, other_tb)
            self.names_by_filepath[path] = fullname
            self.tracebacks[path] = tb
        return spec

    def _format_tb(self, tb):
        """Take a formatted traceback as returned by traceback.format_stack()
        and remove lines that are solely about us and the Python machinery,
        leaving only lines pertaining to the user's code"""
        frames = [frame for frame in tb[:-1]
                  if 'importlib._bootstrap' not in frame
                  and 'imp.load_module' not in frame
                  and not ('imp.py' in frame
                           and ('load_module' in frame
                                or 'load_source' in frame
                                or 'load_package' in frame))]
        return ''.join(frames)

    def _restore_tracebacklimit_after_exception(self):
        """Record the current value of sys.tracebacklimit, if any, and set a
        temporary sys.excepthook to restore it to that value (or delete it)
        after the next exception."""
        orig_excepthook = sys.excepthook
        exists = hasattr(sys, 'tracebacklimit')
        orig_tracebacklimit = getattr(sys, 'tracebacklimit', None)
        def excepthook(*args, **kwargs):
            # Raise the error normally
            orig_excepthook(*args, **kwargs)
            # Restore sys.tracebacklimit
            if exists:
                sys.tracebacklimit = orig_tracebacklimit
            else:
                del sys.tracebacklimit
            # Restore sys.excepthook:
            sys.excepthook = orig_excepthook
        sys.excepthook = excepthook

    def _raise_error(self, path, name, tb, other_name, other_tb):
        msg = """Double import! The same file has been imported under two
        different names, resulting in two copies of the module. This is almost
        certainly a mistake. If you are running a script from within a package
        and want to import another submodule of that package, import it by its
        full path: 'import module.submodule' instead of just 'import
        submodule.'"""

        msg = re.sub(' +',' ', ' '.join(msg.splitlines()))

        tb = self._format_tb(tb)
        other_tb = self._format_tb(other_tb)
        msg += "\n\nPath imported: %s\n\n" % path
        msg += "Traceback (first time imported, as %s):\n" % other_name
        msg += "------------\n%s------------\n\n" % other_tb
        msg += "Traceback (second time imported, as %s):\n" % name
        msg += "------------\n%s------------" % tb

        # We set sys.tracebacklimit to a small number to not print all the
        # nonsense from the import machinary in the traceback, it is not
        # useful to the user in reporting this exception. But we have to jump
        # through this hoop to make sure sys.tracebacklimit is restored after
        # our exception is raised, since putting it in a finally: block
        # doesn't work:
        self._restore_tracebacklimit_after_exception()

        sys.tracebacklimit = 2
        raise RuntimeError(msg) from None


_denier = None

def enable():
    if '--allow-double-imports' in sys.argv:
        # Calls to enable/disable the double import denier are ignored if this
        # command line argument is present.
        return
    global _denier
    if _denier is None:
        _denier = DoubleImportDenier()
    if _denier.enabled:
        raise RuntimeError('already enabled')
    # This is here because it actually happened:
    for importer in sys.meta_path:
        if importer.__class__.__name__ == DoubleImportDenier.__name__:
            msg = 'Two DoubleImportDenier instances in sys.meta_path!'
            raise AssertionError(msg)
    sys.meta_path.insert(0, _denier)
    _denier.enabled = True


def disable():
    if '--allow-double-imports' in sys.argv:
        # Calls to enable/disable the double import denier are ignored if this
        # command line argument is present.
        return
    if not _denier.enabled:
        raise RuntimeError('not enabled')
    sys.meta_path.remove(_denier)
    _denier.enabled = False


if __name__ == '__main__':
    # Run from this directory as __main__:
    enable()

    def test1():
        # Import numpy.linalg twice under different names:
        import numpy as np
        np.linalg.__file__ = None
        # Add the numpy folder to the search path:
        sys.path.append(os.path.dirname(np.__file__))
        import linalg

    def test2():
        # This also gets detected, since this module already exists as
        # __main__ but this line would import it as double_import_denier.
        import double_import_denier

    test1()
    test2()
