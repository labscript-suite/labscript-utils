# -*- coding: UTF-8 -*-
#####################################################################
#                                                                   #
# UnitConversionBase.py                                             #
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

import copy
from types import MethodType
import math
from numpy import iterable, array


class _MultiplicativeConversion(object):
    """Callable for conversion functions that are just multiplicative
       transformations of another conversion function"""
    def __init__(self, name, unprefixed_method, factor, to_base):
        self.unprefixed_method = unprefixed_method
        self.factor = float(factor)
        self.to_base = bool(to_base)
        self.__name__ = name

    def __get__(self, instance, class_):
        """Bind like an instance method"""
        return MethodType(self, instance)

    def __call__(self, value):
        if self.to_base:
            return self.unprefixed_method(value) * self.factor
        else:
            return self.unprefixed_method(value / self.factor)


def vectorise(method):
    def f(instance, arg):
        if iterable(arg):
            return array([method(instance, el) for el in arg])
        else:
            return method(instance, arg)
    return f
            

class UnitConversion(object):
    _magnitude_list = {'p': 1e-12,'n':1e-9, 'u':1e-6,'m': 1e-3,
                       'k': 1e3, 'M': 1e6,'G': 1e9,'T': 1e12}

    unit_list = _magnitude_list # alias for backward compat

    def __init__(self, params):
        magnitudes = params.get('magnitudes', [])
        
        # Convert any unicode 'mu' symbol to a 'u':
        magnitudes = [p if p != '\u03bc' else 'u' for p in magnitudes]
        self._magnitudes = {prefix: self._magnitude_list[prefix] for prefix in magnitudes}

        # A list of tuples we will use to sort the list of derived units once
        # we produce the units for the provided magnitudes:
        derived_units_sortlist = []

        for i, derived_unit in enumerate(self.derived_units):
            # Append the unit magnitude derived unit to the list:
            sortinfo = (i, 1)
            derived_units_sortlist.append((sortinfo, derived_unit))

            # Dynamically create instance methods for each other magnitude:
            unprefixed_to_base = getattr(self, derived_unit + "_to_base")
            unprefixed_from_base = getattr(self, derived_unit + "_from_base")
            for prefix, factor in self._magnitudes.items():
                unit = prefix + derived_unit
                to_base_name = unit + "_to_base"
                from_base_name = unit + "_from_base"
                self.__dict__[to_base_name] = _MultiplicativeConversion(to_base_name, unprefixed_to_base, factor, to_base=True)
                self.__dict__[from_base_name] = _MultiplicativeConversion(from_base_name, unprefixed_from_base, factor, to_base=False)

                # Append to the sortlist:
                sortinfo = (i, factor)
                derived_units_sortlist.append((sortinfo, unit))

        # Sort derived units first by position of the unit in the original
        # list of derived_units without prefixes, then by magnitude:
        derived_units_sortlist.sort()
        self.derived_units = [unit for sortinfo, unit in derived_units_sortlist]

        self.units = self._magnitudes # alias for backward compat
