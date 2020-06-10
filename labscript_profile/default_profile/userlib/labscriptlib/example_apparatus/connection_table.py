from labscript import start, stop, add_time_marker, DigitalOut
from labscript_devices.DummyPseudoclock.labscript_devices import DummyPseudoclock
from labscript_devices.DummyIntermediateDevice import DummyIntermediateDevice

# Use a virtual, or 'dummy', device for the psuedoclock
DummyPseudoclock(name='pseudoclock')

# An output of this DummyPseudoclock is its 'clockline' attribute, which we use
# to trigger children devices
DummyIntermediateDevice(name='intermediate_device', parent_device=pseudoclock.clockline)

# Create a DigitalOut child of the DummyIntermediateDevice
DigitalOut(name='digital_out', parent_device=intermediate_device, connection='do0')

# Begin issuing labscript primitives
# start() elicits the commencement of the shot
start()

# Stop the experiment shot with stop()
stop(1.0)
