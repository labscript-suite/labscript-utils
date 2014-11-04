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

__version__ = '2.1.1'


class VersionException(Exception):
    pass

    
def check_version(module_name, at_least, less_than, version=None):

    def get_version_tuple(version_string):
        version_tuple = [int(v.replace('+', '-').split('-')[0]) for v in version_string.split('.')]
        while len(version_tuple) < 3:
            version_tuple += (0,)
        return version_tuple

    if version is None:
        version = __import__(module_name).__version__
    at_least_tuple, less_than_tuple, version_tuple = [get_version_tuple(v) for v in [at_least, less_than, version]]
    if not at_least_tuple <= version_tuple < less_than_tuple:
        raise VersionException(
            '{module_name} {version} found. {at_least} <= {module_name} < {less_than} required.'.format(**locals()))