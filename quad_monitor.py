from UnitConversionBase import *
class quad_monitor(UnitConversion):
    base_unit = 'V'
    derived_units = ['A', 'Gcm']
    
    def __init__(self,calibration_parameters = {'A_per_V':20.032, 'Gcm_per_A':1.88679, 'A_offset':0.0968}):            
        self.parameters = calibration_parameters
     
        self.parameters.setdefault('A_per_V',20.032)
        self.parameters.setdefault('Gcm_per_A',1.88679)
        self.parameters.setdefault('A_offset',0.0968)
        
        UnitConversion.__init__(self,self.parameters)

    def A_to_base(self,amps):
        volts = (amps - self.parameters['A_offset'])/self.parameters['A_per_V']
        return volts
    def A_from_base(self,volts):
        amps = volts * self.parameters['A_per_V'] + self.parameters['A_offset']
        return amps
    def Gcm_to_base(self,gauss_per_cm):
        volts = gauss_per_cm/(self.parameters['Gcm_per_A'] * self.parameters['A_per_V'])
        return volts
    def Gcm_from_base(self,volts):
        gauss_per_cm = self.parameters['Gcm_per_A'] * self.parameters['A_per_V'] * volts
        return gauss_per_cm
        
