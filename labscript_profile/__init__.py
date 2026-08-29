import site
import sys
import os
import configparser
from ast import literal_eval
from pathlib import Path
from subprocess import check_output
import socket
from getpass import getuser

from .toml_config import (
    TomlConfigParser,
    as_config_list,
    dump_toml_file,
    load_toml_file,
)

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
    return LABSCRIPT_SUITE_PROFILE / 'labconfig' / f'{hostname()}.toml'

# LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
def legacy_labconfig_path():
    """Temporary legacy INI labconfig location. Slated for removal soon."""
    if LABSCRIPT_SUITE_PROFILE is None:
        return None
    return LABSCRIPT_SUITE_PROFILE / 'labconfig' / f'{hostname()}.ini'


def add_userlib_and_pythonlib():
    """Find the users's labconfig file, read the userlib and pythonlib keys, and add
    those directories to the Python search path. This function intentionally
    re-implements finding and reading the config file so as to not import
    labscript_utils, since we dont' want to import something like labscript_utils every
    time the interpreter starts up"""
    labconfig = ensure_labconfig()
    if labconfig is None:
        return
    if not labconfig.exists():
        return
    config = TomlConfigParser(defaults={'labscript_suite': str(LABSCRIPT_SUITE_PROFILE)})
    config.read_toml(labconfig)
    for option in ['userlib', 'pythonlib']:
        try:
            paths = config.get('default', option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            paths = ''
        for path in as_config_list(paths):
            site.addsitedir(path)


def ensure_labconfig():
    """Return the TOML labconfig path, converting a legacy INI file if needed.

    The legacy conversion path is temporary and slated for removal soon.
    """
    labconfig = default_labconfig_path()
    if labconfig is None:
        return None
    if labconfig.exists():
        return labconfig
    # LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
    legacy = legacy_labconfig_path()
    if legacy is None or not legacy.exists():
        return labconfig
    _convert_legacy_labconfig(legacy, labconfig)
    return labconfig


def _example_labconfig_data():
    if LABSCRIPT_SUITE_PROFILE is not None:
        profile_example = LABSCRIPT_SUITE_PROFILE / 'labconfig' / 'example.toml'
        if profile_example.exists():
            return load_toml_file(profile_example)
    bundled_example = Path(__file__).resolve().parent / 'default_profile' / 'labconfig' / 'example.toml'
    if bundled_example.exists():
        return load_toml_file(bundled_example)
    return {}

# LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
def _coerce_legacy_value(value, template_value):
    if template_value is None:
        return value
    if isinstance(template_value, bool):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in configparser.ConfigParser.BOOLEAN_STATES:
                return configparser.ConfigParser.BOOLEAN_STATES[lowered]
        return value
    if isinstance(template_value, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if isinstance(template_value, float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if isinstance(template_value, list):
        if not isinstance(value, str):
            return value
        try:
            parsed = literal_eval(value)
        except (SyntaxError, ValueError):
            return value
        if not isinstance(parsed, (list, tuple)):
            return value
        if not template_value:
            return list(parsed)
        template_item = template_value[0]
        return [_coerce_legacy_value(item, template_item) for item in parsed]
    return value

# LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
def _convert_legacy_labconfig(legacy_path, toml_path):
    """Temporary legacy migration path from INI to TOML. Slated for removal soon."""
    config = configparser.ConfigParser(interpolation=None)
    config.read(legacy_path)
    template_data = _example_labconfig_data()
    default_template = template_data.get('default', {})
    data = {
        'default': {
            key: _coerce_legacy_value(value, default_template.get(key))
            for key, value in config.defaults().items()
        }
    }
    for section in config.sections():
        canonical_section = section.lower()
        section_items = dict(config._sections[section])
        section_items.pop('__name__', None)
        autoload = section_items.get('autoload_config_file')
        # LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        if isinstance(autoload, str) and autoload.lower().endswith('.ini'):
            section_items['autoload_config_file'] = autoload[:-4] + '.toml'
        section_template = template_data.get(canonical_section, {})
        data[canonical_section] = {
            key: _coerce_legacy_value(value, section_template.get(key))
            for key, value in section_items.items()
        }
    toml_path.parent.mkdir(parents=True, exist_ok=True)
    dump_toml_file(toml_path, data)
