#####################################################################
#                                                                   #
# clean_repo_hook.py                                                #
#                                                                   #
# Copyright 2019, Chris Billington                                  #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from __future__ import print_function, unicode_literals, division, absolute_import

"""
This module contains a mercurial hook to delete all .pyc files and empty folders within
non-hidden directories inside a hg repository, as well as a function to add the hook to
the hgrc of the labscript repositories.

The hook can be installed by running install_hook(repo_path). This will write a .sh or
.bat file within th .hg directory of the repo, copy this script to the .hg directory as
well, and add a hook to the hgrc file there. The hook will run the .bat or .sh file,
which in turn will run the python script. This indirection is due to the fact that on
windows, we won't have a Python interpreter in our PATH, and so the batch script will
look up in the labscript suite install directory what the path to a Python interpreter
is, so that it can execute the script. And on non-windows we just keep the structure the
same with a .sh file for consistency. Whilst mercurual can run python-based hooks within
its own interpreter, these must either be in the PYTHONPATH or specified with an
absolute path, which is too fragile. So we do this indirection to make sure it will keep
working no matter how the repo is moved around.

When using mercurial to upgrade and downgrade labscript suite repositories, untracked
.pyc files from one revision may remain after updating to a different revision. This is
usually not a problem since Python will just regenerate them. However it can be a
problem if code is attempting to import a module whose .pyc file is present even though
the .py file is not. We would like this to result in an ImportError, not to import a
module from an unrelated revision, which may not be compatible with the current
revision. If running the same repository with multiple Python versions, one can even get
a "wrong magic number" error when importing such .pyc files.

Some applications distribute only .pyc files - this is why they are still importable.
The labscript suite is not such an application, so we delete these errant .pyc files.

Application behaviour may also differ based on the presence of directories, such as
expecting them to contain plugins. We delete empty directories too.
"""

import os
import sys
import shutil
import subprocess

PY2 = sys.version_info.major == 2
if PY2:
    str = unicode
    from ConfigParser import ConfigParser
else:
    from configparser import ConfigParser

THIS_FILE = os.path.abspath(__file__)
PYTHON_HOOK_PATH = os.path.join('.hg', 'clean_repo_hook.py')
HOOK_NAME = 'update.clean_repo'

BASH_HOOK = "#!/bin/sh\npython '{}'\n".format(PYTHON_HOOK_PATH)

BAT_HOOK = """@echo off
if exist "{python}" (
    "{python}" "{hook}"
) else (
    echo {hook_name} hook: "Python interpreter {python} not found; skipping.
    echo     Reinstall hook to reactivate. This will happen automatically when
    echo     registering the labscript suite install with a new Python environment.
)
""".format(python=sys.executable, hook=PYTHON_HOOK_PATH, hook_name=HOOK_NAME)


if os.name == 'nt':
    SHELL_HOOK = BAT_HOOK
    SHELL_HOOK_PATH = os.path.join('.hg', 'clean_repo_hook.bat')
else:
    SHELL_HOOK = BASH_HOOK
    SHELL_HOOK_PATH = os.path.join('.hg', 'clean_repo_hook.sh')


def _chmod_plus_x(path):
    if os.name == 'nt':
        return
    # This is so much simpler than the os module calls neccesary to do the same:
    subprocess.run(['chmod', '+x', path])


def install_hook(repo_path):
    """Add the update hook to the hgrc of the given repo. On Windows, the hook will
    include the path to the current Python interpreter, and so the hook will stop
    working if Python is uninstalled, and will print a warning instead. Call this
    function again to reinstall the hook for a new Python interpreter."""
    repo_path = os.path.abspath(repo_path)
    dot_hg = os.path.join(repo_path, '.hg')
    if not os.path.isdir(dot_hg):
        raise ValueError('no hg repository here')
    hgrc = os.path.join(dot_hg, 'hgrc')
    config = ConfigParser()
    if os.path.exists(hgrc):
        config.read(hgrc)
    if not config.has_section('hooks'):
        config.add_section('hooks')
    config.set('hooks', HOOK_NAME, SHELL_HOOK_PATH)
    with open(hgrc, 'w') as f:
        config.write(f)
    shell_hook_path = os.path.join(repo_path, SHELL_HOOK_PATH)
    # Write the shell script to the .hg folder:
    with open(shell_hook_path, 'w') as f:
        f.write(SHELL_HOOK)
    # Give it execute permissions if necessary:
    _chmod_plus_x(shell_hook_path)
    # Copy this script into the hgrc folder
    shutil.copy(THIS_FILE, dot_hg)


def clean_pyc_files_and_empty_dirs(repo_path):
    """Delete all .pyc files and empty folders within non-hidden directories inside a hg
    repository."""

    # Make sure we're not running outside a hg repository:
    if not os.path.exists(os.path.join(repo_path, '.hg')):
        raise ValueError('no hg repository here')

    # First pass, breadth first, to delete .pyc files without entering hidden
    # directories:
    print("%s hook: " % HOOK_NAME, end='')
    n_files = 0
    n_dirs = 0
    for folder, subfolders, files in os.walk(os.getcwd(), topdown=True):
        for subfolder in subfolders[:]:
            if subfolder.startswith('.'):
                # Do not recurse into hidden directories:
                subfolders.remove(subfolder)
        for file in files:
            path = os.path.join(folder, file)
            if path.endswith('.pyc'):
                os.unlink(path)
                n_files += 1

    # Second pass, depth-first, to find empty folders. This will find results in hidden
    # folders, which we don't want to delete, so we don't delete them quite yet:
    empty_folders = []
    for folder, subfolders, files in os.walk(repo_path, topdown=False):
        if all(f in empty_folders for f in subfolders) and not files:
            # Folder is either empty, or contains only a tree of empty dirs:
            empty_folders.append(folder)

    # Third pass, breadth-first again, to delete empty folders found in the previous
    # pass, but without recursing into hidden folders.
    for folder, subfolders, files in os.walk(repo_path, topdown=True):
        for subfolder in subfolders[:]:
            if subfolder.startswith('.'):
                # Do not recurse into hidden directories:
                subfolders.remove(subfolder)
        if folder in empty_folders:
            shutil.rmtree(folder)
            n_dirs += 1
    print("cleaned %d .pyc file(s) and %d empty folder(s)" % (n_files, n_dirs))


if __name__ == '__main__':
    if os.getenv('HG_HOOKNAME', None) == HOOK_NAME:
        # We are running as a hg hook. Do the cleaning:
        clean_pyc_files_and_empty_dirs(os.getcwd())
