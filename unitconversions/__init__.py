#####################################################################
#                                                                   #
# __init__.py                                                       #
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

import os
import importlib
from labscript_utils import PY2
from .UnitConversionBase import UnitConversion


class _All(object):
    """Backward compatibility for importers importing * from here and expecting to be
    able to access all unit conversion classes that way. For performance reasons we
    don't want to import everything unless someone actually does this, so we replace
    __all__ with a custom object so we can detect when someone does an import * and
    only import all the classes if this occurs"""

    __all__ = None

    def __getitem__(self, ix):
        if self.__all__ is None:
            self.__all__ = []
            self._import_all()
        return self.__all__[ix]

    def _import_all(self):
        """imports all unit conversion classes in module within this subpackage into
        this module's globals. This is used only for backward compatibility with unit
        conversion classes that were not specified with a fully qualified name"""
        for filename in os.listdir(os.path.split(__file__)[0]):
            if filename.endswith('.py') and filename != '__init__.py':
                module = filename[:-3]
                result = {}
                import_line = 'from labscript_utils.unitconversions.%s import *'
                exec(import_line % module, result, result)
                for name, value in result.items():
                    globals()[name] = value
                    if isinstance(value, type) and issubclass(value, UnitConversion):
                        self.__all__.append(name)
                        # Also add the class to the globals dict under its full name.
                        # This is a little odd, but ensures that if an unaware version
                        # of BLACS is dealing with fully qualified class names, it will
                        # still find them by looking them up in our globals dict. This
                        # is a backward compatibility hack only and may be removed in
                        # future.
                        fullname = 'labscript_utils.unitconversions.%s.%s'
                        fullname = fullname % (module, name)
                        if PY2:
                            fullname = fullname.encode('utf8')
                        globals()[fullname] = value


__all__ = _All()


def get_unit_conversion_class(fullname):
    """import and return the unit conversion class with the given name. Ideally this is
    a fully qualified class name with an absolute import path, i.e.
    path.to.some.module.ClassName. But if it is just a single name, we fall back to
    looking through all classes defined in submodules. This allows backward
    compatibility with old shot files that do not have the full name saved."""
    if '.' not in fullname:
        # It's just a class name, no import path. Fall back to importing everything to
        # find it:
        if __all__.__all__ is None:
            __all__._import_all()
        return globals()[fullname]
    # Otherwise, import the module and return the class
    split = fullname.split('.')
    module_name = '.'.join(split[:-1])
    class_name = split[-1]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)
