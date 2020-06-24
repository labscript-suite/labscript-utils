import site
import sys
import os
from configparser import ConfigParser, NoSectionError, NoOptionError
from pathlib import Path
from subprocess import check_output
import socket
from getpass import getuser


# The contents of this file are imported every time the Python interpreter starts up,
# owing to our custom .pth file that runs the below two functions. This ensures that
# user code, the location of which is configured under pythonlib and userlib in their
# labconfig file, is importable no matter whether they are running code from within a
# labscript suite application or not.
#
# Since this code runs every startup, code in this module should be side-effect free,
# relatively lean, and fairly bomb-proof.


# This construction instead of simply Path.home() ensures we get the users home
# directory instead of /root if we are running with sudo (such as at install time for a
# system-wide install).
try:
    LABSCRIPT_SUITE_PROFILE = Path("~" + getuser()).expanduser() / 'labscript-suite'
except Exception:
    # Python starting up in some funky environment? Not our problem, be silent.
    LABSCRIPT_SUITE_PROFILE = None


def hostname():
    if sys.platform == 'darwin':
        return check_output(['scutil', '--get', 'LocalHostName']).decode('utf8').strip()
    else:
        return socket.gethostname()


def default_labconfig_path():
    if LABSCRIPT_SUITE_PROFILE is None:
        return None
    return LABSCRIPT_SUITE_PROFILE / 'labconfig' / f'{hostname()}.ini'


def add_userlib_and_pythonlib():
    """Find the users's labconfig file, read the userlib and pythonlib keys, and add
    those directories to the Python search path. This function intentionally
    re-implements finding and reading the config file so as to not import
    labscript_utils, since we dont' want to import something like labscript_utils every
    time the interpreter starts up"""
    labconfig = default_labconfig_path()
    if labconfig is not None and labconfig.exists():
        config = ConfigParser(defaults={'labscript_suite': LABSCRIPT_SUITE_PROFILE})
        config.read(labconfig)
        for option in ['userlib', 'pythonlib']:
            try:
                paths = config.get('DEFAULT', option).split(',')
            except (NoSectionError, NoOptionError):
                paths = []
            for path in paths:
                site.addsitedir(path)
