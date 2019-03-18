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
from __future__ import division, unicode_literals, print_function, absolute_import

__version__ = '2.12.0'


import sys
import os
import traceback

PY2 = sys.version_info[0] == 2

for path in sys.path:
    if os.path.exists(os.path.join(path, '.is_labscript_suite_install_dir')):
        labscript_suite_install_dir = path
        break
else:
    labscript_suite_install_dir = None


def import_or_reload(modulename):
    """
    Behaves like 'import modulename' would, excepts forces the imported 
    script to be rerun
    """
    # see if the proposed module is already loaded
    # if so, we will need to re-run the code contained in it
    import importlib
    if not PY2:
        reload = importlib.reload
    if modulename in sys.modules.keys():
        reload(sys.modules[modulename])
        return sys.modules[modulename]
    module = importlib.import_module(modulename)
    return module

class VersionException(Exception):
    pass

def _get_version(module_name):
    """return the version string module.__version__ by importing the module,
    and the exc_info for the exception (if any) raised during import, or None
    if there was no exception. If the version string is defined prior to the
    exception during import, then it will still be returned. Otherwise None
    will be returned in its place. This can be useful since having
    incompatible versions of packages can itself be the cause of exceptions
    during import, so it is preferable to raise a 'wrong version' in addition
    to, or instead of the exception that was raised during import"""

    from labscript_utils.brute_import import brute_import

    try:
        module = __import__(module_name)
        exc_info = None
    except Exception:
        exc_info = sys.exc_info()
        # brute_import returns the exception, but if for some reason it's
        # different we should return the one we got at the first atttempted
        # import:
        module, _ = brute_import(module_name)
    return getattr(module, '__version__', None), exc_info


def _reraise(exc_info):
    type, value, traceback = exc_info
    # handle python2/3 difference in raising exception        
    if PY2:
        exec('raise type, value, traceback', globals(), locals())
    else:
        raise value.with_traceback(traceback)


def check_version(module_name, at_least, less_than, version=None):
    from distutils.version import LooseVersion

    if version is None:
        version, exc_info = _get_version(module_name)

    if version is not None:
        at_least_version, less_than_version, installed_version = [LooseVersion(v) for v in [at_least, less_than, version]]
        if not at_least_version <= installed_version < less_than_version:
            msg = '{module_name} {version} found. {at_least} <= {module_name} < {less_than} required.'.format(**locals())
            if exc_info is not None:
                msg += '\n\n === In addition, the below exception was raised during import of {}: ===\n\n'.format(module_name)
                msg += ''.join(traceback.format_exception(*exc_info))
            raise VersionException(msg)

    # Correct version string, but failed import:
    if exc_info is not None:
        _reraise(exc_info)

    # Successful import but no version string:
    if version is None:
        raise ValueError('Invalid version string from package {}: {}'.format(module_name, version))


def dedent(s):
    """Remove leading spaces from the first line of a string, all common leading
    indentation (spaces only) from subsequent lines, strip trailing spaces from all
    lines and replace single newlines prior to lines with the common indentation with
    spaces. Lines with additional indentation are kept verbatim. Good for unwrapping
    error messages etc that are in code as multiline triple-quoted strings."""
    # Strip trailing whitespace:
    lines = [line.rstrip(' ') for line in s.splitlines()]
    # Get common indentation from lines other than the first one:
    indentation = float('inf')
    for line in lines[1:]:
        if line:
            indentation = min(indentation, len(line) - len(line.lstrip(' ')))
    if not lines[1:]:
        indentation = 0
    # Dedent the lines:
    dedented_lines = []
    for i, line in enumerate(lines):
        if i == 0:
            dedented_line = line.lstrip(' ')
        else:
            dedented_line = line[indentation:]
        dedented_lines.append(dedented_line)
    # Then add newline characters where we are going to keep them:
    unwrapped_lines = []
    for i, line in enumerate(dedented_lines):
        if i == 0:
            unwrapped_lines.append(line)
        else:
            previous_line = dedented_lines[i - 1]
            # If either this line or the previous line is blank or starts with custom
            # indentation, put this line on a newline rather than unwrapping it:
            if any(not l or l.startswith(' ') for l in [line, previous_line]):
                unwrapped_lines.append('\n' + line)
            else:
                unwrapped_lines.append(' ' + line)
    return ''.join(unwrapped_lines)


# Enforce that the same file can't be imported under multiple names, to help
# prevent subtle bugs:
import labscript_utils.double_import_denier
labscript_utils.double_import_denier.enable()


# Disable the 'quick edit' feature of Windows' cmd.exe, which causes console applicatons
# to freeze if their console windows are merely clicked on. This causes all kinds of
# headaches, so we disable it in all labscript programs:
check_version('zprocess', '2.10.0', '3.0')
import zprocess
zprocess.disable_quick_edit()

