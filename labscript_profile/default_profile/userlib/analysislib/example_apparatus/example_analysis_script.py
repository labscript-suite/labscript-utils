import lyse
from pathlib import Path
import matplotlib.pyplot as plt
import h5py

# Within lyse, lyse.path is the filepath of the shot being analysed. Outside lyse it is
# None, and we use the filepath of the last shot of the lyse DataFrame instead.
h5_path = lyse.path
if h5_path is None:
    df = lyse.data()
    h5_path = df.filepath.iloc[-1]

# Instantiate a lyse.Run object for this shot
run = lyse.Run(h5_path)

# Read the output table of the dummy intermediate device from the shot file. It has one
# row per clock tick and one column per output, named after the output.
with h5py.File(h5_path, 'r') as h:
    outputs = h['devices']['intermediate_device']['OUTPUTS'][:]
analog_data = outputs['analog_out']
digital_data = outputs['digital_out']

# Plot both outputs
plt.plot(analog_data, 'b.', label='analog_out')
plt.plot(digital_data, 'r.', label='digital_out')
plt.xlabel('clock tick')
plt.ylabel('intermediate device output')

# Label the plot with a unique string representing the shot
plt.title(Path(run.h5_path).name)

# Plot adornments
plt.legend(loc='lower left')
plt.grid()

# Show the plot
plt.show()

# Save the outputs as arrays, and the maximum analog output as a scalar result, in the
# 'results' group of the shot file
run.save_result_array('analog_out', analog_data)
run.save_result_array('digital_out', digital_data)
run.save_result('analog_out_max', analog_data.max())
