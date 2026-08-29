#####################################################################
#                                                                   #
# labconfig.py                                                      #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import configparser
import os
import warnings
from ast import literal_eval
from pathlib import Path

from labscript_utils import dedent
from labscript_profile import (
    LABSCRIPT_SUITE_PROFILE,
    default_labconfig_path,
    ensure_labconfig,
)
from labscript_profile.toml_config import (
    TomlBasicInterpolation,
    TomlConfigParser,
    dump_toml_file,
    load_toml_file,
)


default_config_path = default_labconfig_path()


def format_path_for_display(path):
    """Return an absolute path with the user's home abbreviated for display."""
    absolute_path = os.path.abspath(os.path.expanduser(os.fspath(path)))
    home_path = str(Path.home())
    normalized_path = os.path.normcase(os.path.normpath(absolute_path))
    normalized_home = os.path.normcase(os.path.normpath(home_path))
    display_home = '%USERPROFILE%' if os.name == 'nt' else '~'
    if normalized_path == normalized_home:
        return display_home
    home_prefix = normalized_home + os.path.sep
    if normalized_path.startswith(home_prefix):
        relative_path = os.path.relpath(absolute_path, home_path)
        separator = '\\' if os.name == 'nt' else '/'
        return display_home + separator + relative_path.replace(os.path.sep, separator)
    return absolute_path


def get_default_appconfig_file(
    exp_config, app_name, config_filename, ensure_directory=False
):
    try:
        default_path = os.path.join(exp_config.get('default', 'app_saved_configs'), app_name)
    except (LabConfig.NoOptionError, LabConfig.NoSectionError):
        exp_config.set(
            'default',
            'app_saved_configs',
            os.path.join(
                '%(labscript_suite)s',
                'userlib',
                'app_saved_configs',
                '%(apparatus_name)s',
            ),
        )
        default_path = os.path.join(exp_config.get('default', 'app_saved_configs'), app_name)
    if ensure_directory:
        os.makedirs(default_path, exist_ok=True)
    return os.path.join(default_path, config_filename)


class LabscriptApplication(object):
    app_name = None
    default_config_filename = None

    def init_config_window_title(self):
        self.base_window_title = self.ui.windowTitle().split(' - ', 1)[0]

    def get_default_config_file(self, ensure_directory=False):
        if self.app_name is None or self.default_config_filename is None:
            raise NotImplementedError(
                'LabscriptApplication requires app_name and default_config_filename'
            )
        return get_default_appconfig_file(
            self.exp_config,
            self.app_name,
            self.default_config_filename,
            ensure_directory=ensure_directory,
        )

    def set_config_window_title(self, filename):
        self.ui.setWindowTitle(
            f'{self.base_window_title} - {format_path_for_display(filename)}'
        )


class EnvInterpolation(TomlBasicInterpolation):
    """Interpolation that expands environment variables after TOML/basic interpolation."""

    def before_get(self, *args):
        value = super(EnvInterpolation, self).before_get(*args)
        if isinstance(value, str):
            return os.path.expandvars(value)
        return value


class LabConfig(TomlConfigParser):
    """TOML labconfig reader with the small ConfigParser-like API used by the suite."""

    NoOptionError = configparser.NoOptionError
    NoSectionError = configparser.NoSectionError
    DuplicateSectionError = configparser.DuplicateSectionError

    def __init__(
        self, config_path=default_config_path, required_params=None, defaults=None,
    ):
        if required_params is None:
            required_params = {}
        if defaults is None:
            defaults = {}
        else:
            defaults = dict(defaults)
        defaults['labscript_suite'] = str(LABSCRIPT_SUITE_PROFILE)
        if isinstance(config_path, list):
            config_paths = list(config_path)
            if config_paths:
                if config_paths[0] == default_config_path:
                    config_paths[0] = ensure_labconfig()
                self.config_path = config_paths[0]
            else:
                self.config_path = None
        else:
            self.config_path = ensure_labconfig() if config_path == default_config_path else config_path
            config_paths = [self.config_path]

        self.file_format = ""
        for section, options in required_params.items():
            self.file_format += "[%s]\n" % section
            for option in options:
                self.file_format += "%s = <value>\n" % option

        TomlConfigParser.__init__(
            self,
            defaults=defaults,
            interpolation=EnvInterpolation(),
        )
        for path in config_paths:
            self._read_path(path)

        experiment_name = self.get("default", "experiment_name", fallback=None)
        if experiment_name:
            msg = """The experiment_name keyword has been renamed apparatus_name in
                labscript_utils 3.0, and will be removed in a future version. Please
                update your labconfig to use the apparatus_name keyword."""
            warnings.warn(dedent(msg), FutureWarning)
            if self.get("default", "apparatus_name", fallback=None):
                msg = """You have defined both experiment_name and apparatus_name in
                    your labconfig. Please omit the deprecate experiment_name
                    keyword."""
                raise Exception(dedent(msg))
            self.set("default", "apparatus_name", experiment_name)

        try:
            for section, options in required_params.items():
                section = self._canonical_section_name(section)
                for option in options:
                    self.get(section, option)
        except (configparser.NoOptionError, configparser.NoSectionError):
            msg = f"""The experiment configuration file located at {config_path} does
                not have the required keys. Make sure the config file contains the
                following structure:\n{self.file_format}"""
            raise Exception(dedent(msg))

    def _read_path(self, path):
        """Read a TOML labconfig, or temporarily fall back to legacy INI."""
        if path is None:
            return
        path = Path(path)
        if not path.exists():
            return
        if path.suffix.lower() == '.toml':
            self.read_toml(path)
            return
        # LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        if path.suffix.lower() == '.ini':
            msg = """INI labconfig support is deprecated and slated for removal soon.
                Convert this file to TOML."""
            warnings.warn(dedent(msg), FutureWarning)
            self.read(path)
            return
        msg = f"Unsupported labconfig format for {path}. Expected a .toml or .ini file."
        raise RuntimeError(msg)


# LEGACY INI COMPATIBILITY. The '.ini' entry is deprecated and will be removed.
APPCONFIG_SUFFIXES = ('.toml', '.ini')


def appconfig_path_with_suffix(path, suffix):
    """Return ``path`` carrying ``suffix``.

    ``Path.with_suffix()`` replaces everything after the last dot, which is only
    correct when the path already ends in an app config extension. App config
    paths are routinely built from names that legitimately contain dots, such as
    an analysis script called ``rb.87.imaging``, where replacing would silently
    address a different file. Append in that case instead.
    """
    path = Path(path)
    if path.suffix.lower() in APPCONFIG_SUFFIXES:
        return path.with_suffix(suffix)
    return path.with_name(path.name + suffix)


def _resolve_appconfig_load_path(filename):
    path = Path(filename)
    toml_path = appconfig_path_with_suffix(path, '.toml')
    if toml_path.exists():
        return toml_path
    # LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
    legacy_path = appconfig_path_with_suffix(path, '.ini')
    if legacy_path.exists():
        return legacy_path
    return toml_path


def _resolve_appconfig_save_path(filename):
    return appconfig_path_with_suffix(filename, '.toml')

# LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
def backup_legacy_config(path):
    """Rename a migrated legacy config file to ``.old`` without clobbering backups."""
    path = Path(path)
    if not path.exists():
        return None
    backup_path = Path(str(path) + '.old')
    index = 1
    while backup_path.exists():
        backup_path = Path(str(path) + '.old' + str(index))
        index += 1
    try:
        path.rename(backup_path)
    except OSError:
        return None
    return backup_path


def _to_toml_compatible(value, location='value'):
    if isinstance(value, dict):
        converted = {}
        for key, child in value.items():
            if not isinstance(key, str):
                msg = f"{location} contains a non-string dict key {key!r}"
                raise TypeError(msg)
            converted[key] = _to_toml_compatible(child, f"{location}.{key}")
        return converted
    if isinstance(value, (list, tuple)):
        return [
            _to_toml_compatible(child, f"{location}[{index}]")
            for index, child in enumerate(value)
        ]
    if isinstance(value, (str, bool, int, float)):
        return value
    if value is None:
        # A None option is dropped by save_appconfig(), which never reaches
        # here. Inside a list there is no way to drop one without shifting
        # every later index, so that stays an error.
        msg = f"{location} is None, which a TOML list cannot represent"
        raise TypeError(msg)
    msg = f"{location} value {value!r} is not representable in TOML app config"
    raise TypeError(msg)

# LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
def _load_legacy_appconfig_value(value):
    """Temporary legacy INI app-config decoder. Slated for removal soon."""
    if not isinstance(value, str):
        return value
    try:
        return literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def save_appconfig(filename, data):
    """Save a dictionary as a TOML app config.

    TOML has no null, and represents absence by omitting the key. Options whose
    value is ``None`` are therefore left out; ``load_appconfig()`` returns a
    mapping, so callers reading them back with ``.get()`` see ``None`` again.
    """
    data = {
        section_name: {
            name: _to_toml_compatible(value, f"{section_name}/{name}")
            for name, value in section.items()
            if value is not None
        }
        for section_name, section in data.items()
    }
    filename = _resolve_appconfig_save_path(filename)
    filename.parent.mkdir(parents=True, exist_ok=True)
    dump_toml_file(filename, data)
    return str(filename)


def load_appconfig(filename, return_save_path=False):
    """Load a TOML app config, or a legacy INI app config if required.

    If a legacy INI file is loaded, a sibling TOML file is immediately written and can be
    returned as the canonical save path via ``return_save_path=True``. After successful
    conversion, the legacy INI file is moved aside to ``.old`` so future loads prefer the
    canonical TOML file. Legacy INI support here is temporary and slated for removal soon.
    """
    requested_path = Path(filename)
    filename = _resolve_appconfig_load_path(filename)
    save_path = _resolve_appconfig_save_path(requested_path)
    # LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
    if filename.suffix.lower() == '.ini':
        c = configparser.ConfigParser(interpolation=None)
        c.optionxform = str
        if filename.exists():
            c.read(filename)
        data = {
            section_name: {
                name: _load_legacy_appconfig_value(value)
                for name, value in c.items(section_name, raw=True)
            }
            for section_name in c.sections()
        }
        if filename.exists():
            save_path = Path(save_appconfig(save_path, data))
            backup_legacy_config(filename)
    else:
        raw = load_toml_file(filename) if filename.exists() else {}
        # Every table is returned, including one named 'default'. App configs
        # are plain section/option documents with no DEFAULT inheritance, so
        # dropping that name here would silently discard a section
        # save_appconfig() had just written.
        data = {
            section_name: dict(section.items())
            for section_name, section in raw.items()
            if isinstance(section, dict)
        }
        if filename.suffix.lower() == '.toml':
            save_path = filename
    if return_save_path:
        return data, str(save_path)
    return data
