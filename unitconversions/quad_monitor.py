#####################################################################
#                                                                   #
# quad_monitor.py                                                   #
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
class quad_monitor(UnitConversion):
    base_unit = 'V'
    derived_units = ['A', 'Gcm']
    
    def __init__(self,calibration_parameters = {'A_per_V':20.032, 'Gcm_per_A':1.88679, 'A_offset':0.0968-0.14}):            
        self.parameters = calibration_parameters
     
        self.parameters.setdefault('A_per_V',20.032)
        self.parameters.setdefault('Gcm_per_A',1.88679)
        self.parameters.setdefault('A_offset',0.0968-0.14)
        
        UnitConversion.__init__(self,self.parameters)

    def A_to_base(self,amps):
        volts = (amps - self.parameters['A_offset'])/self.parameters['A_per_V']
        return volts
    def A_from_base(self,volts):
        amps = volts * self.parameters['A_per_V'] + self.parameters['A_offset']
        return amps
    def Gcm_to_base(self,gauss_per_cm):
        volts = self.A_to_base(gauss_per_cm/self.parameters['Gcm_per_A'])
        return volts
    def Gcm_from_base(self,volts):
        gauss_per_cm = self.parameters['Gcm_per_A'] * self.A_from_base(volts)
        return gauss_per_cm
        
