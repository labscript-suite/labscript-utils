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
import sys
import os
import configparser

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

        try:
            for section, options in required_params.items():
                for option in options:
                    self.get(section, option)
        except configparser.NoOptionError:
            msg = f"""The experiment configuration file located at {config_path} does
                not have the required keys. Make sure the config file containes the
                following structure:\n{self.file_format}"""
            raise Exception(dedent(msg))
