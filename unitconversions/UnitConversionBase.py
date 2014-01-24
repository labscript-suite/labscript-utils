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

import copy
import new
import math
from numpy import iterable, array

def vectorise(method):
    def f(instance, arg):
        if iterable(arg):
            return array([method(instance, el) for el in arg])
        else:
            return method(instance, arg)
    return f
            
class UnitConversion(object):
    unit_list = {'p':'10**-12','n':'10**-9','u':'10**-6','m':'10**-3',
                 'k':'10**3','M':'10**6','G':'10**9','T':'10**12'}
    def __init__(self,params):
        magnitudes = []
        if 'magnitudes' in params:
            magnitudes = params['magnitudes']
        
        # order the unit order of magnitudes
        # We want lowest (negative) to -3 and then largest positive to 3
        temp_units = []
        for unit in magnitudes:
            try:
                if unit == u'\u03bc': # a unicode 'mu' symbol
                    unit = 'u'
                magnitude = math.log10(eval(self.unit_list[unit]))
                if magnitude < 0:
                    position = 0
                    for u in temp_units:
                        if math.log10(eval(u[1])) > magnitude:
                            break
                        else:
                            position += 1
                    
                else:
                    position = 0
                    for u in temp_units:                        
                        if math.log10(eval(u[1])) < 0:
                            position += 1
                        elif math.log10(eval(u[1])) > magnitude:
                            position += 1
                        else:
                            break
                
                temp_units.insert(position,(unit,self.unit_list[unit]))
            except Exception, e:
                print e
                pass
                
        self.units = temp_units
        
        for unit in self.units:
            for derived_unit in self.derived_units:
                #if derived_unit == unit[2]:
                exec("def "+unit[0]+derived_unit+"_to_base(self,value): return self."+derived_unit+"_to_base(value)*"+unit[1])
                exec ("a="+unit[0]+derived_unit+"_to_base")
                self.__dict__[unit[0]+derived_unit+"_to_base"] = new.instancemethod(a,self,UnitConversion)
                exec("def "+unit[0]+derived_unit+"_from_base(self,value): return self."+derived_unit+"_from_base(value/float("+unit[1]+"))")
                exec ("a="+unit[0]+derived_unit+"_from_base")
                self.__dict__[unit[0]+derived_unit+"_from_base"] = new.instancemethod(a,self,UnitConversion)
        
        # Make another loop to stop infinite regression!
        derived_copy = copy.copy(self.derived_units)
        for unit in self.units:
            for derived_unit in derived_copy:        
                # Add unit to derived unit list (put in correct order)
                # Find derived unit location in list
                pos = self.derived_units.index(derived_unit)
                if math.log10(eval(unit[1])) > 0:
                    pos+=1
                # Is this unit a negative or positive order of magnitude?
                
                #if unit[0] == 'u':
                #    self.derived_units.insert(pos,'µ'+derived_unit)
                #else:
                self.derived_units.insert(pos,unit[0]+derived_unit)
