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

__version__ = '2.14.1'


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


from labscript_utils.versions import get_version, VersionException, check_version


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

try:
    # If zprocess is new enough, disable the 'quick edit' feature of Windows' cmd.exe,
    # which causes console applicatons to freeze if their console windows are merely
    # clicked on. This causes all kinds of headaches, so we disable it in all labscript
    # programs:
    import zprocess
    if hasattr(zprocess, 'disable_quick_edit'):
        # Feature is present in zprocess > 2.10.0, but if not present we just ignore.
        zprocess.disable_quick_edit()
except ImportError:
    pass
