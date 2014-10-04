#####################################################################
#                                                                   #
# aom.py                                                            #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

from UnitConversionBase import *
from NovaTechDDS9m import NovaTechDDS9mAmpConversion
from numpy import *

class SineAom(NovaTechDDS9mAmpConversion):
    """
    AOM calibration P(A) is very close to a sine for dipole trap AOM!
    """
    base_unit = "Arb"

    def __init__(self, calibration_parameters=None):
        # These parameters are loaded from a globals.h5 type file automatically
        self.parameters = calibration_parameters        
        self.derived_units = ["Power", "fraction"]
        # P(x) = A * cos(2*pi*f * x + phase) + c
        # Saturates at saturation Volts
        self.parameters.setdefault('A', 1.969)
        self.parameters.setdefault('f', 0.527)
        self.parameters.setdefault('phase', 3.262)
        self.parameters.setdefault('c', 1.901)
        
        self.parameters['phase'] = self.parameters['phase']%(2*pi)
        
        NovaTechDDS9mAmpConversion.__init__(self,self.parameters)

    def Power_to_base(self, power):
        A = self.parameters["A"]
        f = self.parameters["f"]
        phase = self.parameters["phase"]
        c = self.parameters["c"]
        if ((phase / pi) % 2) == 0:
            phi = (arccos((power - c) / A) - phase) % (2*pi)
        else:
            phi = (2*pi - arccos((power - c) / A) - phase) % (2*pi)
        return phi / (2*pi*f)
    
    def Power_from_base(self, amp):
        A = self.parameters["A"]
        f = self.parameters["f"]
        phase = self.parameters["phase"]
        c = self.parameters["c"]

        return A * cos(2*pi*f*amp + phase) + c        

    def fraction_to_base(self, fraction):
        Pmax = self.parameters["A"] + self.parameters["c"]
        Pmin = max(self.parameters["c"] - self.parameters["A"], 0)
        P = (Pmax - Pmin) * fraction + Pmin
        Amp = self.Power_to_base(P)
        return Amp
    
    def fraction_from_base(self, amp):
        f = self.parameters["f"]
        phase = self.parameters["phase"]
        
        if 2*pi*f*amp + phase > 2*pi:
            amp = (2*pi - phase) / (2*pi*f)
        
        P = self.Power_from_base(amp)
        Pmax = self.parameters["A"] + self.parameters["c"]
        Pmin = max(self.parameters["c"] - self.parameters["A"], 0)
        fraction = (P - Pmin) / (Pmax - Pmin)
        return fraction

