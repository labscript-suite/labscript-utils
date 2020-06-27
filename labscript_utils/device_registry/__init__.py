try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata
import packaging.version

use_local_machinery = True
try:
    labscript_device_version_str = importlib_metadata.version('labscript_devices')
    labscript_devices_version = packaging.version.parse(labscript_device_version_str)
    use_local_machinery = labscript_devices_version >= packaging.version.parse('3.1.0.dev16')
except importlib_metadata.PackageNotFoundError:
    pass

# import and use the labscript_devices code if an old version of the package is used.
# This ensures that new labscript_utils with old labscript_devices doesn't attempt to
# register labscript_devices classes twice
if not use_local_machinery:
    from labscript_devices import * 
else:
    from ._import_machinery import *
