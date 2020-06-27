from ._device_registry import *

# Backwards compatibility for labscript-devices < 3.1. If labscript_devices defines the
# device registry as well, undo the above import and use the contents of
# labscript_devices instead. The above import must be done first so that the names are
# available to labscript_devices during the below import, since as of 3.1 it imports
# this module as well.
try:
    from labscript_devices import ClassRegister
    if ClassRegister.__module__ == 'labscript_devices':
        for name in _device_registry.__all__:
            del globals()[name]
        from labscript_devices import *
except ImportError:
    pass
