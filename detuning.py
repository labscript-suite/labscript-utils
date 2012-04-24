from UnitConversionBase import *
class detuning(UnitConversion):
    base_unit = 'MHz'
    derived_units = ['d_MHz', 'linewidths']
    
    def __init__(self,calibration_parameters = None):            
        self.parameters = calibration_parameters
        
        self.parameters.setdefault('pass',1)        # specify single- or double-pass with sign
        self.parameters.setdefault('detuning_0',0)  # detuning of input light
        self.parameters.setdefault('gamma',6.065)   # natural linewidth in MHz
        self.parameters.setdefault('aom_f0',False)    # rf frequency corrresponding to resonance
        
        UnitConversion.__init__(self,self.parameters)

    def d_MHz_to_base(self,detuning):
        if not self.parameters['aom_f0']:
            aom_frequency = (detuning - self.parameters['detuning_0']) / self.parameters['pass']
        else:
            aom_frequency = detuning / self.parameters['pass'] + self.parameters['aom_f0']
        return aom_frequency
        
    def d_MHz_from_base(self,aom_frequency):
        if not self.parameters['aom_f0']:
            detuning = self.parameters['pass'] * aom_frequency + self.parameters['detuning_0']
        else:
            detuning = self.parameters['pass'] * (aom_frequency - self.parameters['aom_f0']) 
        return detuning
        
    def linewidths_to_base(self,linewidths):
        aom_frequency = self.d_MHz_to_base(self.parameters['gamma'] * linewidths)
        return aom_frequency
        
    def linewidths_from_base(self,aom_frequency):
        linewidths = self.d_MHz_from_base(aom_frequency) / self.parameters['gamma']
        return linewidths
