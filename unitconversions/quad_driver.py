#####################################################################
#                                                                   #
# quad_driver.py                                                    #
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

class quad_driver(UnitConversion):
    base_unit = 'V'
    derived_units = ['A', 'Gcm']
    
    def __init__(self,calibration_parameters = {'A_per_V':19.9757, 'Gcm_per_A':1.88679, 'A_offset':-0.642724, 'A_min':-0.09}):            
        self.parameters = calibration_parameters
     
        self.parameters.setdefault('A_per_V',19.9757)
        self.parameters.setdefault('Gcm_per_A',1.88679)
        self.parameters.setdefault('A_offset',-0.642724)
        self.parameters.setdefault('A_min',-0.09)
        
        UnitConversion.__init__(self,self.parameters)

    @vectorise
    def A_to_base(self,amps):
        V_min = (self.parameters['A_min'] - self.parameters['A_offset'])/self.parameters['A_per_V']
        if amps < 0.001:
            volts = 0
        elif amps <= self.parameters['A_min']:
            volts = V_min
        else:
            volts = (amps - self.parameters['A_offset'])/self.parameters['A_per_V']
        return volts
    def A_from_base(self,volts):
        amps = max(volts * self.parameters['A_per_V'] + self.parameters['A_offset'], self.parameters['A_min'])
        return amps
    def Gcm_to_base(self,gauss_per_cm):
        volts = self.A_to_base(gauss_per_cm/self.parameters['Gcm_per_A'])
        return volts
    def Gcm_from_base(self,volts):
        gauss_per_cm = self.parameters['Gcm_per_A'] * self.A_from_base(volts)
        return gauss_per_cm
        
