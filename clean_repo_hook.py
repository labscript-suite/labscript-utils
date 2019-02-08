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
PY2 = sys.version_info.major == 2
if PY2:
    str = unicode
    from ConfigParser import ConfigParser
else:
    from configparser import ConfigParser

REPOS = ['runmanager', 'runviewer', 'blacs', 'labscript', 'lyse', 'labscript_utils']

THIS_FILE = os.path.abspath(__file__)
HOOK = 'python:%s:clean_pyc_files_and_empty_dirs' % THIS_FILE


def _ensure_update_hook_repo(repo_path):
    """Add the update hook to the hgrc of the specifc repo. Do nothing if the path is
    not a repo. Do nothing if there is already an update hook, unless it looks like this
    hook but with a different filepath, in which case update it (the user may have moved
    their labscript suite install dir on disk, though this is unlikely). Do nothing if
    we do not have write access to the hgrc file."""
    dot_hg = os.path.join(repo_path, '.hg')
    if not os.path.isdir(dot_hg):
        # No repo here.
        return
    hgrc = os.path.join(dot_hg, 'hgrc')
    config = ConfigParser()
    if os.path.exists(hgrc):
        config.read(hgrc)
    if not config.has_section('hooks'):
        config.add_section('hooks')
    if not config.has_option('hooks', 'update'):
        config.set('hooks', 'update', HOOK)
    elif 'clean_pyc_files_and_empty_dirs' in config.get('hooks', 'update'):
        config.set('hooks', 'update', HOOK)
    try:
        with open(hgrc, 'w') as f:
            config.write(f)
    except (OSError, IOError):
        # Do nothing if we can't write the config file
        pass


def ensure_update_hook(labscript_suite_install_dir):
    """Ensure the mercurial repositories for labscript applications within the given
    labscript suite install dir have a mercurial hook to run clean_pyc_files upon
    updating"""

    # Do nothing if it doesn't look like we're running from within a regular install:
    if labscript_suite_install_dir is None:
        return
    if not THIS_FILE.startswith(labscript_suite_install_dir):
        return

    for repo in REPOS:
        repo_path = os.path.join(labscript_suite_install_dir, repo)
        _ensure_update_hook_repo(repo_path)


def clean_pyc_files_and_empty_dirs(ui, repo, hooktype, **kwargs):
    """Delete all .pyc files and empty folders within non-hidden directories inside a hg
    repository."""

    # First pass, breadth first, to delete .pyc files without entering hidden
    # directories:
    print("labscript_utils.clean_repo_hook: ", end='')
    n_files = 0
    n_dirs = 0
    for folder, subfolders, files in os.walk(repo.root, topdown=True):
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
    for folder, subfolders, files in os.walk(repo.root, topdown=False):
        if all(f in empty_folders for f in subfolders) and not files:
            # Folder is either empty, or contains only a tree of empty dirs:
            empty_folders.append(folder)

    # Third pass, breadth-first again, to delete empty folders found in the previous
    # pass, but without recursing into hidden folders.
    for folder, subfolders, files in os.walk(repo.root, topdown=True):
        for subfolder in subfolders[:]:
            if subfolder.startswith('.'):
                # Do not recurse into hidden directories:
                subfolders.remove(subfolder)
        if folder in empty_folders:
            os.rmdir(folder)
            n_dirs += 1
    print("cleaned %d .pyc files and %d empty_folders" % (n_files, n_dirs))

