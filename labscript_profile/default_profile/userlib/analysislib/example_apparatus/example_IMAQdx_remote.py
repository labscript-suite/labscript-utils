import lyse
from pathlib import Path
import matplotlib.pyplot as plt

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

# Extract the images 'before' and 'after' generated from camera.expose
before, after = run.get_images('camera', 'comparison', 'before', 'after')

# Compute the difference of the two images, after casting them to signed integers
# (otherwise negative differences wrap to 2**16 - 1 - diff)
diff = after.astype('int16') - before.astype('int16')

# Plot the row-wise mean of each image
plt.plot(before.mean(axis=0), label='before')
plt.plot(after.mean(axis=0), label='after')
plt.xlabel('pixel coordinate (column)')
plt.ylabel('counts')

# Label the plot with a unique string representing the shot
plt.title(Path(run.h5_path).name)

# Plot adornments
plt.legend(loc='lower left')
plt.grid()

# Show the plot
plt.show()

# Compute a result based on the image processing and save it to the 'results' group of
# the shot file
result = diff.std()
run.save_result('foobar', result)
