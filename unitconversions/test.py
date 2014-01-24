#####################################################################
#                                                                   #
# test.py                                                           #
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
class test(UnitConversion):
    # This must be defined outside of init, and must match the default hardware unit specified within the BLACS tab
    base_unit = 'MHz'
    derived_units = ['A', 'Gauss']
    
    # You can pass a dictionary at class instantiation with some parameters to use in your unit converstion.
    # You can also place a list of "order of magnitude" prefixes (eg, k, m, M, u, p) you also want available
    # and the UnitConversion class will automatically generate the conversion function based on the functions 
    # you specify for the "derived units". This list should be stored in the 'magnitudes' key of the parameters
    # dictionary
    
    def __init__(self,calibration_parameters = None):            
        # These parameters are loaded from a globals.h5 type file automatically
        self.parameters = calibration_parameters
        
        self.parameters.setdefault('a',2)
        self.parameters.setdefault('b',3)        
        
        UnitConversion.__init__(self,self.parameters)
        # We should probably also store some hardware limits here, and use them accordingly 
        # (or maybe load them from a globals file, or specify them in the connection table?)

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
        
