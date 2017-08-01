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

__version__ = '2.4.0'


import sys
import os

PY2 = sys.version_info[0] == 2

for path in sys.path:
    if os.path.exists(os.path.join(path, '.is_labscript_suite_install_dir')):
        labscript_suite_install_dir = path
        break
else:
    labscript_suite_install_dir = None


class VersionException(Exception):
    pass


def check_version(module_name, at_least, less_than, version=None):

    from distutils.version import LooseVersion

    if version is None:
        version = __import__(module_name).__version__
    if version is None:
        raise ValueError('Invalid version string from package {}: {}'.format(module_name, version))
    at_least_version, less_than_version, installed_version = [LooseVersion(v) for v in [at_least, less_than, version]]
    if not at_least_version <= installed_version < less_than_version:
        raise VersionException(
            '{module_name} {version} found. {at_least} <= {module_name} < {less_than} required.'.format(**locals()))

