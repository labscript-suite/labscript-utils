#####################################################################
#                                                                   #
# zlog.py                                                           #
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

import sys
from os import execv
from labscript_utils.ls_zprocess import get_config
from zprocess import start_daemon

"""Script to run a zlog server configured according to LabConfig. Run with:

    python -m labscript_utils.zlog [--daemon]

if --daemon is specified, the zlog server will be started in the background.
"""


def main():
    config = get_config()

    cmd = [
        sys.executable,
        '-m',
        'zprocess.zlog',
        '--port',
        str(config['zlog_port']),
        '--cls',
        'RotatingFileHandler',
        '--maxBytes',
        str(config['logging_maxBytes']),
        '--backupCount',
        str(config['logging_backupCount']),
    ]
    if config['shared_secret_file'] is not None:
        cmd += ['--shared-secret-file', config['shared_secret_file']]
    if config['allow_insecure']:
        cmd += ['--allow-insecure']

    if '--daemon' in sys.argv:
        start_daemon(cmd)
    else:
        execv(sys.executable, cmd)


if __name__ == '__main__':
    main()
