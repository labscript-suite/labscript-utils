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
from __future__ import division, unicode_literals, print_function, absolute_import

import sys
import os
import socket
import subprocess
import errno

from labscript_utils import PY2
if PY2:
    import ConfigParser as configparser
else:
    import configparser

from labscript_utils import labscript_suite_install_dir
# Look for a 'labconfig' folder in the labscript install directory:
if labscript_suite_install_dir is not None:
    config_prefix = os.path.join(labscript_suite_install_dir, 'labconfig')
else:
    # No labscript install directory found? Revert to system defaults
    if os.name == 'nt':
        config_prefix = os.path.abspath(r'C:\labconfig')
    else:
        config_prefix = os.path.join(os.getenv('HOME'),'labconfig')
        if not os.path.exists(config_prefix):
            config_prefix='/etc/labconfig/'

if not os.path.exists(config_prefix):
    message = (r"Couldn't find labconfig folder. Please ensure it exists. " +
               r"If the labscript suite is installed, labconfig must be <labscript_suite_install_dir>/labconfig/. " +
               r"If the labscript suite is not installed, then C:\labconfig\ is checked on Windows, " +
               r" and $HOME/labconfig/ then /etc/labconfig/ checked on unix.")
    raise IOError(message)

config_prefix = os.path.abspath(config_prefix)

if sys.platform == 'darwin':
    hostname = subprocess.check_output(['scutil', '--get', 'LocalHostName']).decode('utf8').strip()
else:
    hostname = socket.gethostname()
default_config_path = os.path.join(config_prefix,'%s.ini'%hostname)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class LabConfig(configparser.SafeConfigParser):
    NoOptionError = configparser.NoOptionError
    NoSectionError = configparser.NoSectionError

    def __init__(self,config_path=default_config_path,required_params={},defaults={}):
        if isinstance(config_path,list):
            self.config_path = config_path[0]
        else:
            self.config_path = config_path

        self.file_format = ""
        for section, options in required_params.items():
            self.file_format += "[%s]\n"%section
            for option in options:
                self.file_format += "%s = <value>\n"%option

        # Ensure the folder exists:
        mkdir_p(os.path.dirname(self.config_path))

        # If the file doesn't exist, create it
        if not os.path.exists(self.config_path):
            with open(self.config_path,'a+') as f:
                f.write(self.file_format)

        # Load the config file
        configparser.SafeConfigParser.__init__(self,defaults)
        self.read(config_path) #read all files in the config path if it is a list (self.config_path only contains one string)

        try:
            for section, options in required_params.items():
                for option in options:
                    self.get(section,option)

        except configparser.NoOptionError as e:
            raise Exception('The experiment configuration file located at %s does not have the required keys. Make sure the config file containes the following structure:\n%s'%(config_path, self.file_format))


    # Overwrite the add_section method to only attempt to add a section if it doesn't
    # exist. We don't ever care whether a section exists or not, only that it does exist
    # when we try and save an attribute into it.
    def add_section(self,section):
        # Create the group if it doesn't exist
        if not section.lower() == 'default' and not self.has_section(section):
            configparser.SafeConfigParser.add_section(self, section)

    # Overwrite the set method so that it adds the section if it doesn't exist,
    # and immediately saves the data to the file (to avoid data loss on program crash)
    def set(self, section, option, value):
        self.add_section(section)
        configparser.SafeConfigParser.set(self,section,option,value)
        self.save()

    # Overwrite the remove section function so that it immediately saves the change to disk
    def remove_section(self,section):
        configparser.SafeConfigParser.remove_section(self,section)
        self.save()

    # Overwrite the remove option function so that it immediately saves the change to disk
    def remove_option(self,section,option):
        configparser.SafeConfigParser.remove_option(self,section,option)
        self.save()

    # Provide a convenience method to save the contents of the ConfigParser to disk
    def save(self):
        with open(self.config_path, 'w+') as f:
            self.write(f)
