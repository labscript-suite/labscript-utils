from UnitConversionBase import *
from numpy import *

class SineAom(UnitConversionBase):
    """
    AOM calibration P(A) is very close to a sine for dipole trap AOM!
    """
    base_unit = "Arb"
    derived_units = ["Power"]

    def __init__(self, calibration_parameters=None):
        # These parameters are loaded from a globals.h5 type file automatically
        self.parameters = calibration_parameters
        
        # P(x) = A * cos(2*pi*f * x + phase) + c
        # Saturates at saturation Volts
        self.parameters.setdefault('A', 0)
        self.parameters.setdefault('f', 0)
        self.parameters.setdefault('phase', 0)
        self.parameters.setdefault('c', 0)
        
        UnitConversion.__init__(self,self.parameters)

    def Power_to_base(self, power):
        A = self.parameters["A"]
        f = self.parameters["f"]
        phase = self.parameters["phase"]
        c = self.parameters["c"]
        return (arccos((power - c) / A) - phase) / (2*pi*f)

    def Power_from_base(self, amp):
        A = self.parameters["A"]
        f = self.parameters["f"]
        phase = self.parameters["phase"]
        c = self.parameters["c"]

        return A * cos(2*pi*f*amp + phase) + c
