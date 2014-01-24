#####################################################################
#                                                                   #
# example.py                                                        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

from __future__ import division
from UnitConversionBase import *

class example1(UnitConversion):
    # This must be defined outside of init, and must match the default hardware unit specified within the BLACS tab
    base_unit = 'V'
    
    # You can pass a dictionary at class instantiation with some parameters to use in your unit converstion.
    # You can also place a list of "order of magnitude" prefixes (eg, k, m, M, u, p) you also want available
    # and the UnitConversion class will automatically generate the conversion function based on the functions 
    # you specify for the "derived units". This list should be stored in the 'magnitudes' key of the parameters
    # dictionary
    
    def __init__(self,calibration_parameters = None):            
        self.parameters = calibration_parameters
        
        self.derived_units = ['A', 'Gauss']
        
        # Set default parameters if they are not speficied in calibration_parameters
        self.parameters.setdefault('a',2)
        self.parameters.setdefault('b',3)        
        
        UnitConversion.__init__(self,self.parameters)

    def A_to_base(self,amps):
        #here is the calibration code that may use self.parameters
        volts = amps/self.parameters['a']
        return volts
    def A_from_base(self,volts):
        #here is the calibration code that may use self.parameters
        amps = volts * self.parameters['a']
        return amps
    def Gauss_to_base(self,gauss):
        #here is the calibration code that may use self.parameters
        volts = gauss/self.parameters['b']
        return volts
    def Gauss_from_base(self,volts):
        #here is the calibration code that may use self.parameters
        gauss = (volts)*self.parameters['b']
        return gauss
        
class example2(UnitConversion):
    # This must be defined outside of init, and must match the default hardware unit specified within the BLACS tab
    base_unit = 'MHz'
    
    # You can pass a dictionary at class instantiation with some parameters to use in your unit converstion.
    # You can also place a list of "order of magnitude" prefixes (eg, k, m, M, u, p) you also want available
    # and the UnitConversion class will automatically generate the conversion function based on the functions 
    # you specify for the "derived units". This list should be stored in the 'magnitudes' key of the parameters
    # dictionary
    
    def __init__(self,calibration_parameters = None):            
        self.parameters = calibration_parameters
        
        self.derived_units = ['detuned_MHz']
        
        # Set default parameters if they are not speficied in calibration_parameters
        self.parameters.setdefault('offset',32.7)      
        
        UnitConversion.__init__(self,self.parameters)

    def detuned_MHz_to_base(self,d_mhz):
        #here is the calibration code that may use self.parameters
        mhz = d_mhz - self.parameters['offset']
        return mhz
    def detuned_MHz_from_base(self,mhz):
        #here is the calibration code that may use self.parameters
        d_mhz = mhz + self.parameters['offset']
        return d_mhz

class example3(UnitConversion):
    # This must be defined outside of init, and must match the default hardware unit specified within the BLACS tab
    base_unit = 'Vpp'
    
    # You can pass a dictionary at class instantiation with some parameters to use in your unit converstion.
    # You can also place a list of "order of magnitude" prefixes (eg, k, m, M, u, p) you also want available
    # and the UnitConversion class will automatically generate the conversion function based on the functions 
    # you specify for the "derived units". This list should be stored in the 'magnitudes' key of the parameters
    # dictionary
    
    def __init__(self,calibration_parameters = None):            
        self.parameters = calibration_parameters
        
        self.derived_units = ['W']
        
        # Set default parameters if they are not speficied in calibration_parameters
        self.parameters.setdefault('grad',2)      
        self.parameters.setdefault('int',0.05)      
        
        UnitConversion.__init__(self,self.parameters)

    def W_to_base(self,watts):
        #here is the calibration code that may use self.parameters
        vpp = float(watts - self.parameters['int'])/self.parameters['grad']
        return vpp
    def W_from_base(self,vpp):
        #here is the calibration code that may use self.parameters
        watts = self.parameters['grad']*vpp + self.parameters['int']
        return watts
