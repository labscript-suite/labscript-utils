import lyse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import h5py

# Is this script being run from within an interactive lyse session?
if lyse.spinning_top:
    # If so, use the filepath of the current shot
    h5_path = lyse.path
else:
    # If not, get the filepath of the last shot of the lyse DataFrame
    df = lyse.data()
    h5_path = df.filepath.iloc[-1]

# Instantiate a lyse.Run object for this shot
run = lyse.Run(h5_path)

# Get a dictionary of the global variables used in this shot
run_globals = run.get_globals()

# Open experiment file to pull variables from
with h5py.File(h5_path, 'r') as h:
    
    devices = h['devices']
    
    outputs = devices['intermediate_device']['OUTPUTS']
    pulse = devices['pseudoclock']['PULSE_PROGRAM'] # unused
    
    analog_data = outputs[:]['analog_out']
    digital_data = outputs[:]['digital_out']

plt.figure()    
plt.plot(np.array(analog_data), 'b.', label='analog_out')
plt.plot(np.array(digital_data), 'r.', label='digital_out')
plt.xlabel('time (ms)')
plt.ylabel('intermediate device output')

# # Label the plot with a unique string representing the shot
plt.title(Path(run.h5_path).name)

# Plot adornments
plt.legend(loc='lower left')
plt.grid()

# Show the plot
plt.show()

# Compute a result based on the image processing and save it to the 'results' group of
# the shot file
result = {}
result['analog_data'] = analog_data
result['digital_data'] = digital_data
run.save_result('foobar', result)
