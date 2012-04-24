from UnitConversionBase import *
class quad_driver(UnitConversion):
    base_unit = 'V'
    derived_units = ['A', 'Gcm']
    
    def __init__(self,calibration_parameters = None):            
        self.parameters = calibration_parameters
     
        self.parameters.setdefault('A_per_V',1/0.059)
        self.parameters.setdefault('Gcm_per_A',1.8)        
        
        UnitConversion.__init__(self,self.parameters)

    def A_to_base(self,amps):
        volts = amps/self.parameters['A_per_V']
        return volts
    def A_from_base(self,volts):
        amps = volts * self.parameters['A_per_V']
        return amps
    def Gcm_to_base(self,gauss_per_cm):
        volts = gauss_per_cm/(self.parameters['Gcm_per_A'] * self.parameters['A_per_V'])
        return volts
    def Gcm_from_base(self,volts):
        gauss_per_cm = self.parameters['Gcm_per_A'] * self.parameters['A_per_V'] * volts
        return gauss_per_cm
        
