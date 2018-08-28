#####################################################################
#                                                                   #
# linear_coil_driver.py                                             #
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
import numpy as np

class BidirectionalCoilDriver(UnitConversion):
    base_unit = 'V'
    derived_units = ['A']
    
    def __init__(self, calibration_parameters=None):
        # These parameters are loaded from a globals.h5 type file automatically
        if calibration_parameters is None:
            calibration_parameters = {}
        self.parameters = calibration_parameters
        
        # I[A] = slope * V[V] + shift
        # Saturates at saturation Volts
        self.parameters.setdefault('slope', 1) # A/V
        self.parameters.setdefault('shift', 0) # A
        self.parameters.setdefault('saturation', 10) # V
        
        UnitConversion.__init__(self,self.parameters)
        # We should probably also store some hardware limits here, and use them accordingly 
        # (or maybe load them from a globals file, or specify them in the connection table?)

    def A_to_base(self,amps):
        #here is the calibration code that may use self.parameters
        volts = (amps - self.parameters['shift']) / self.parameters['slope']
        return volts
        
    def A_from_base(self,volts):
        volts = np.minimum(volts, self.parameters['saturation'])
        amps = self.parameters['slope'] * volts + self.parameters['shift']
        return amps 
        
        
class UnidirectionalCoilDriver(BidirectionalCoilDriver):
    
    def A_to_base(self,amps):
        return BidirectionalCoilDriver.A_to_base(self, amps)* np.int16(amps>0)
        
    def A_from_base(self,volts):
        return BidirectionalCoilDriver.A_from_base(self, volts)* np.int16(volts>0)