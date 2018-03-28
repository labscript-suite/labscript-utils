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

__version__ = '2.7.1'


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

# Enforce that the same file can't be imported under multiple names, to help
# prevent subtle bugs:
import labscript_utils.double_import_denier
labscript_utils.double_import_denier.enable()

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

