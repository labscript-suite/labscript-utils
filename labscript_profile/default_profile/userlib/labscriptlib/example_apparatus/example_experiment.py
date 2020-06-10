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
# A timing variable t is used for convenience
# start() elicits the commencement of the shot
t = 0
add_time_marker(t, "Start", verbose=True)
start()

# Wait for 1 second with all devices in their default state
t += 1

# Change the state of digital_out, and denote this using a time marker
add_time_marker(t, "Toggle digital_out (high)", verbose=True)
digital_out.go_high(t)

# Wait for 0.5 seconds
t += 0.5

# Change the state of digital_out, and denote this using a time marker
add_time_marker(t, "Toggle digital_out (low)", verbose=True)
digital_out.go_low(t)

# Wait for 0.5 seconds
t += 0.5

# Stop the experiment shot with stop()
stop(t)
