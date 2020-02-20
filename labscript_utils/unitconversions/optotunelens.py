#####################################################################
#                                                                   #
# optotunelens.py                                                   #
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

from .UnitConversionBase import *
from scipy.special import lambertw
from numpy import exp, abs
class OptotuneLens(UnitConversion):
    base_unit = 'V'
    derived_units = ['distance','I']
    
    def __init__(self, calibration_parameters=None):
        # These parameters are loaded from a globals.h5 type file automatically
        self.parameters = calibration_parameters
        
        # I[A] = slope * V[V] + shift
        # Saturates at saturation Volts
        self.parameters.setdefault('current_cal', 0.05) # A/V
        self.parameters.setdefault('I_Max', 0.3)
        
        # we fit the function Pos(I) = a*exp(b*I)+c*I+d
        self.parameters.setdefault('a', 0)
        self.parameters.setdefault('b', 0)
        self.parameters.setdefault('c', 0)
        
        UnitConversion.__init__(self,self.parameters)
        # We should probably also store some hardware limits here, and use them accordingly 
        # (or maybe load them from a globals file, or specify them in the connection table?)

    def distance_to_base(self,percentage):
        #here is the calibration code that may use self.parameters
        
        # The inverse function is I = 1/(b*c)(-c*W((a*b/c)*exp((b/c)*P+a))+b/P+ba)
        # Where W is the product log (Lambert W) function
        
        amps = 1.0/(self.parameters['b']*self.parameters['c']) \
        *(-self.parameters['c']*lambertw((self.parameters['a']*self.parameters['b']/self.parameters['c'])*exp((self.parameters['b']/self.parameters['c'])*(percentage+self.parameters['a']))) \
        +self.parameters['b']*percentage \
        +self.parameters['b']*self.parameters['a'])
        
        volts = amps/ self.parameters['current_cal']
        return (volts > 0) * abs(volts)
        
    def distance_from_base(self,volts):
        amps = max(min(self.parameters['current_cal'] * volts,self.parameters['I_Max']),0)
        
        percentage = self.parameters['a']*exp(self.parameters['b']*amps) + self.parameters['c']*amps - self.parameters['a']
        
        return percentage

    def I_to_base(self,current):
        return current/self.parameters['current_cal']
        
    def I_from_base(self,volts):
        return volts*self.parameters['current_cal']