#####################################################################
#                                                                   #
# detuning.py                                                       #
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

class detuning(UnitConversion):
    base_unit = 'Hz'
    derived_units = ['MHz', 'd_MHz', 'linewidths']
    
    def __init__(self, calibration_parameters=None):            
        self.parameters = calibration_parameters
        
        self.parameters.setdefault('pass', 1)        # specify single- or double-pass with sign
        self.parameters.setdefault('detuning_0', 0)  # detuning of input light in MHz
        self.parameters.setdefault('gamma', 6.065)   # natural linewidth in MHz
        self.parameters.setdefault('aom_f0', False)  # rf frequency corrresponding to resonance in MHz
        
        UnitConversion.__init__(self,self.parameters)

    def MHz_to_base(self, aom_frequency_MHz):
        return 1e6*aom_frequency_MHz
        
    def MHz_from_base(self, aom_frequency):
        return 1e-6*aom_frequency
        
    def d_MHz_to_base(self, detuning_MHz):
        if not self.parameters['aom_f0']:
            aom_frequency_MHz = (detuning_MHz - self.parameters['detuning_0'])/self.parameters['pass']
        else:
            aom_frequency_MHz = detuning_MHz/self.parameters['pass'] + self.parameters['aom_f0']
        return self.MHz_to_base(aom_frequency_MHz)
        
    def d_MHz_from_base(self, aom_frequency):
        aom_frequency_MHz = self.MHz_from_base(aom_frequency)
        if not self.parameters['aom_f0']:
            detuning_MHz = self.parameters['pass']*aom_frequency_MHz + self.parameters['detuning_0']
        else:
            detuning_MHz = self.parameters['pass']*(aom_frequency_MHz - self.parameters['aom_f0']) 
        return detuning_MHz
        
    def linewidths_to_base(self, linewidths):
        aom_frequency = self.d_MHz_to_base(self.parameters['gamma'] * linewidths)
        return aom_frequency
        
    def linewidths_from_base(self, aom_frequency):
        linewidths = self.d_MHz_from_base(aom_frequency) / self.parameters['gamma']
        return linewidths
