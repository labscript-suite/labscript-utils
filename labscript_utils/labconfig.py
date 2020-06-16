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
import os
import configparser
from ast import literal_eval
from pprint import pformat
from pathlib import Path
import warnings

from labscript_utils import dedent
from labscript_profile import default_labconfig_path, LABSCRIPT_SUITE_PROFILE

default_config_path = default_labconfig_path()


class EnvInterpolation(configparser.BasicInterpolation):
    """Interpolation which expands environment variables in values,
    by post-filtering BasicInterpolation.before_get()"""

    def before_get(self, *args):
        value = super(EnvInterpolation, self).before_get(*args)
        return os.path.expandvars(value)


class LabConfig(configparser.ConfigParser):
    NoOptionError = configparser.NoOptionError
    NoSectionError = configparser.NoSectionError

    def __init__(
        self, config_path=default_config_path, required_params=None, defaults=None,
    ):
        if required_params is None:
            required_params = {}
        if defaults is None:
            defaults = {}
        defaults['labscript_suite'] = LABSCRIPT_SUITE_PROFILE
        if isinstance(config_path, list):
            self.config_path = config_path[0]
        else:
            self.config_path = config_path

        self.file_format = ""
        for section, options in required_params.items():
            self.file_format += "[%s]\n" % section
            for option in options:
                self.file_format += "%s = <value>\n" % option

        # Load the config file
        configparser.ConfigParser.__init__(
            self, defaults=defaults, interpolation=EnvInterpolation()
        )
        # read all files in the config path if it is a list (self.config_path only
        # contains one string):
        self.read(config_path)

        # Rename experiment_name to apparatus_name and raise a DeprectionWarning
        experiment_name = self.get("DEFAULT", "experiment_name", fallback=None)
        if experiment_name:
            msg = """The experiment_name keyword has been renamed apparatus_name in
                labscript_utils 3.0, and will be removed in a future version. Please
                update your labconfig to use the apparatus_name keyword."""
            warnings.warn(dedent(msg), FutureWarning)
            if self.get("DEFAULT", "apparatus_name", fallback=None):
                msg = """You have defined both experiment_name and apparatus_name in
                    your labconfig. Please omit the deprecate experiment_name
                    keyword."""
                raise Exception(dedent(msg))
            else:
                self.set("DEFAULT", "apparatus_name", experiment_name)

        try:
            for section, options in required_params.items():
                for option in options:
                    self.get(section, option)
        except configparser.NoOptionError:
            msg = f"""The experiment configuration file located at {config_path} does
                not have the required keys. Make sure the config file contains the
                following structure:\n{self.file_format}"""
            raise Exception(dedent(msg))


def save_appconfig(filename, data):
    """Save a dictionary as an ini file. The keys of the dictionary comprise the section
    names, and the values must themselves be dictionaries for the names and values
    within each section. All section values will be converted to strings with
    pprint.pformat()."""
    # Error checking
    for section_name, section in data.items():
        for name, value in section.items():
            try:
                valid = value == literal_eval(pformat(value))
            except (ValueError, SyntaxError):
                valid = False
            if not valid:
                msg = f"{section_name}/{name} value {value} not a Python built-in type"
                raise TypeError(msg)
    data = {
        section_name: {name: pformat(value) for name, value in section.items()}
        for section_name, section in data.items()
    }
    c = configparser.ConfigParser(interpolation=None)
    c.optionxform = str  # preserve case
    c.read_dict(data)
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, 'w') as f:
        c.write(f)


def load_appconfig(filename):
    """Load an .ini file and return a dictionary of its contents. All values will be
    converted to Python objects with ast.literal_eval(). All keys will be lowercase
    regardless of the written contents on the .ini file."""
    c = configparser.ConfigParser(interpolation=None)
    c.optionxform = str  # preserve case
    # No file? No config - don't crash.
    if Path(filename).exists():
        c.read(filename)
    return {
        section_name: {name: literal_eval(value) for name, value in section.items()}
        for section_name, section in c.items()
    }
