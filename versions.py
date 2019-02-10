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
import pkg_resources
import importlib
import tokenize
import ast
from distutils.version import LooseVersion

PY2 = sys.version_info.major == 2
if PY2:
    import imp

    str = unicode


class NotFound(object):
    pass


class NoVersionInfo(object):
    pass


class VersionException(Exception):
    pass


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


def _get_pkg_resources_version(project_name, import_path):
    """Return the pkg_resources version for a package with the given project name
    located at the given import path, or None if there is no such package."""
    for pkg in pkg_resources.working_set:
        if pkg.project_name == project_name and pkg.location == import_path:
            return pkg.version


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
        for i, token in enumerate(tokens):
            token_type, token_str, _, _, _ = token
            if token_type == tokenize.NAME and token_str == '__version__':
                try:
                    next_token = tokens[i + 1]
                except IndexError:
                    continue
                if next_token[0] != tokenize.OP or next_token[1] != '=':
                    continue
                try:
                    next_token = tokens[i + 2]
                except IndexError:
                    continue
                try:
                    version = ast.literal_eval(next_token[1])
                    if version is not None:
                        return version
                except (SyntaxError, ValueError):
                    continue


def get_version(import_name, project_name=None):
    """Try very hard to get the version of a package without importing it. First find
    where it would be imported from, without importing it. Then look for a pkg_resources
    entry in the same import path with the given project name (note: this is not always
    the same as the import name, it is the name for example you would ask pip to
    install). If that is found, return the version info from it. Otherwise look for a
    __version__.py file in the package directory, or a __version__ = <version>
    literal defined in the package sournce (without executing it).

    Return NotFound if the package cannot be found, and NoVersionInfo if the version
    cannot be obtained in the above way, or if it was found but was None."""
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
    version = _get_pkg_resources_version(project_name, import_path)
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
        msg = '{module_name} {version} found. {at_least} <= {module_name} < {less_than} required.'.format(
            **locals()
        )
        raise VersionException(msg)


if __name__ == '__main__':
    assert get_version('subprocess') == NoVersionInfo
    assert get_version('plsgtbg') == NotFound
    assert type(get_version('labscript_utils')) in [str, bytes]
    assert type(get_version('numpy')) in [str, bytes]
