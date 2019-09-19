#####################################################################
#                                                                   #
# versions.py                                                       #
#                                                                   #
# Copyright 2019, Chris Billington                                  #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from __future__ import print_function, unicode_literals, absolute_import, division
import sys
import os
import importlib
import tokenize
import ast
from distutils.version import LooseVersion

PY2 = sys.version_info.major == 2
if PY2:
    str = unicode
    import imp


# Lazy import so that labscript applications' excepthook is present before we
# raise errors about not having a new enough importlib_metadata.
importlib_metadata = None


def _initialise():
    global importlib_metadata
    if importlib_metadata is not None:
        return
    # The following import looks pointless, but is required for its side effects. Finders
    # are added to sys.meta_path that we use:
    try:
        # This will be in the standard library in Python 3.8:
        import importlib.metadata as importlib_metadata
    except ImportError:
        # This is the backport of the Python 3.8 stdlib module,
        import importlib_metadata

    # Check the version of the importlib_metatata package we have imported, so that we know
    # we can actually use it to check versions. Trust importlib_metadata.__version__ for
    # now, to avoid using importlib_metadata itself until we know it is new enough:
    check_version(
        'importlib_metadata', '0.17', '2.0', version=importlib_metadata.__version__
    )

    # Now that we know we have a new enough version of importlib_metadata imported, confirm
    # that result using importlib_metadata itself. This will detect broken installations
    # (where the metadata does not agree with the imported package, or if the same package
    # is installed multiple times to different paths) whereas the above check will not.
    check_version('importlib_metadata', '0.17', '2.0')


class NotFound(object):
    pass


class NoVersionInfo(object):
    pass


class VersionException(RuntimeError):
    pass


class BrokenInstall(RuntimeError):
    pass


ERR_BROKEN_INSTALL = """Multiple metadata files for {package} found in {path}; cannot
reliably get version information. This indicates a previous version of the package was
not properly removed. You may want to uninstall the package, manually delete remaining
metadata files/folders, then reinstall the package.""".replace('\n', ' ')


def _get_import_path(import_name):
    """Get which entry in sys.path a module would be imported from, without importing
    it."""
    if PY2:
        _, location, _ = imp.find_module(import_name)
        return os.path.dirname(location)
    spec = importlib.util.find_spec(import_name)
    if spec is None:
        raise ModuleNotFoundError(import_name)
    location = spec.origin
    if location is None:
        # A namespace package
        msg = "Version checking of namespace packages not implemented"
        raise NotImplementedError(msg)
    if spec.parent:
        # A package:
        return os.path.dirname(os.path.dirname(location))
    else:
        # A single-file module:
        return os.path.dirname(location)


def _get_metadata_version(project_name, import_path):
    """Return the metadata version for a package with the given project name located at
    the given import path, or None if there is no such package."""
    
    for finder in sys.meta_path:
        if hasattr(finder, 'find_distributions'):
            if LooseVersion(importlib_metadata.__version__) >= LooseVersion('0.21'):
                context = importlib_metadata.DistributionFinder.Context(
                    name=project_name, path=[import_path]
                )
                dists = finder.find_distributions(context)
            else:
                # TODO: once importlib_metadata >=0.21 is in anaconda repositories, depend
                # on it and remove this backward compatibility:
                dists = finder.find_distributions(name=project_name, path=[import_path])
            dists = list(dists)
            if len(dists) > 1:
                msg = ERR_BROKEN_INSTALL.format(package=project_name, path=import_path)
                raise BrokenInstall(msg)
            if dists:
                return dists[0].version


def _get_literal_version(filename):
    """Tokenize a source file and return any __version__ = <version> literal defined in
    it.
    """
    if not os.path.exists(filename):
        return None
    with open(filename, 'r') as f:
        try:
            tokens = list(tokenize.generate_tokens(f.readline))
        except tokenize.TokenError:
            tokens = []
        for i, token in enumerate(tokens[:-2]):
            token_type, token_str, _, _, _ = token
            if token_type == tokenize.NAME and token_str == '__version__':
                next_token_type, next_token_str, _, _, _ = tokens[i + 1]
                if next_token_type == tokenize.OP and next_token_str == '=':
                    next_next_token_type, next_next_token_str, _, _, _ = tokens[i + 2]
                    if next_next_token_type == tokenize.STRING:
                        try:
                            version = ast.literal_eval(next_next_token_str)
                            if version is not None:
                                return version
                        except (SyntaxError, ValueError):
                            continue


def get_version(import_name, project_name=None):
    """Try very hard to get the version of a package without importing it. First find
    where it would be imported from, without importing it. Then look for metadata in the
    same import path with the given project name (note: this is not always the same as
    the import name, it is the name for example you would ask pip to install). If that
    is found, return the version info from it. Otherwise look for a __version__.py file
    in the package directory, or a __version__ = <version> literal defined in the
    package sournce (without executing it).

    Return NotFound if the package cannot be found, and NoVersionInfo if the version
    cannot be obtained in the above way, or if it was found but was None."""
    _initialise()
    if project_name is None:
        project_name = import_name
    if '.' in import_name:
        msg = "Version checking of top-level packages only implemented"
        raise NotImplementedError(msg)
    # Find the path where the module lives:
    try:
        import_path = _get_import_path(import_name)
    except ImportError:
        return NotFound
    # Check if pkg_resources knows about this module:
    version = _get_metadata_version(project_name, import_path)
    if version is not None:
        return version
    # Check if it has a version literal defined in a __version__.py file:
    version_dot_py = os.path.join(import_path, import_name, '__version__.py')
    version = _get_literal_version(version_dot_py)
    if version is not None:
        return version
    # check if it has a __version__ literal defined in its main module.
    pkg = os.path.join(import_path, import_name)
    if os.path.isdir(pkg):
        module_file = os.path.join(pkg, '__init__.py')
    else:
        module_file = pkg + '.py'
    version = _get_literal_version(module_file)
    if version is not None:
        return version
    return NoVersionInfo


def check_version(module_name, at_least, less_than, version=None, project_name=None):
    """Check that the version of the given module is at least and less than the given
    version strings, and raise VersionException if not. Raise VersionException if the
    module was not found or its version could not be determined. This function uses
    get_vrsion to determine version numbers without importing modules. In order to do
    this, project_name must be provided if it differs from module_name. For example,
    pyserial is imported as 'serial', but the project name, as passed to a 'pip install'
    command, is 'pyserial'. Therefore to check the version of pyserial, pass in
    module_name='serial' and project_name='pyserial'. You can also pass in a version
    string yourself, in which case no inspection of packages will take place.
    """
    _initialise()
    if version is None:
        version = get_version(module_name, project_name)

    if version is NotFound:
        raise VersionException('Module {} not found'.format(module_name))

    if version is NoVersionInfo:
        raise VersionException(
            'Could not get version info from module {}'.format(module_name)
        )

    at_least_version, less_than_version, installed_version = [
        LooseVersion(v) for v in [at_least, less_than, version]
    ]

    if not at_least_version <= installed_version < less_than_version:
        msg = (
            '{module_name} {version} found. '
            + '{at_least} <= {module_name} < {less_than} required.'
        )
        raise VersionException(msg.format(**locals()))


if __name__ == '__main__':
    assert get_version('subprocess') == NoVersionInfo
    assert get_version('plsgtbg') == NotFound
    assert type(get_version('labscript_utils')) in [str, bytes]
    assert type(get_version('numpy')) in [str, bytes]
    assert type(get_version('serial', 'pyserial')) in [str, bytes]
