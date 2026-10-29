#####################################################################
#                                                                   #
# programs.py                                                       #
#                                                                   #
# Copyright 2026, Monash University and contributors                #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
"""Opening files in the programs that the labconfig names in its `[programs]` section"""
import os
import subprocess
import sys


def open_file(path, program, labconfig):
    """Open the file at `path` in the program that `labconfig` gives for `program`,
    which is `'text_editor'` or `'hdf5_viewer'`. The labconfig value of
    `<program>_arguments` gives the program's arguments, separated by spaces, in which
    `{file}` is replaced by the path. If the arguments do not contain `{file}`, the path
    is the first argument.

    If the program is empty, the file is opened in the operating system's default
    program for the file type, and a file opened with `'text_editor'` is opened for
    editing: on Windows with the "edit" action of the file type, or in Notepad if the
    file type has none, and on macOS in the default text editor.

    On Linux and macOS, the program is started in a new session, so that it does not
    receive signals sent to the terminal of the application.

    Raises `OSError` if the program cannot be started."""
    executable = labconfig.get('programs', program)
    if executable:
        arguments = labconfig.get('programs', f'{program}_arguments').split()
        if any('{file}' in arg for arg in arguments):
            arguments = [arg.replace('{file}', path) for arg in arguments]
        else:
            arguments = [path] + arguments
        _start([executable] + arguments)
    elif sys.platform == 'win32':
        if program == 'text_editor':
            try:
                os.startfile(path, 'edit')
            except OSError:
                _start(['notepad.exe', path])
        else:
            os.startfile(path)
    elif sys.platform == 'darwin':
        if program == 'text_editor':
            _start(['open', '-t', path])
        else:
            _start(['open', path])
    else:
        _start(['xdg-open', path])


def _start(args):
    subprocess.Popen(args, start_new_session=True)
