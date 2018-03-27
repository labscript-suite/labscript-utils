from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode
import sys
import json
import numpy as np
import h5py

vlenstring = h5py.special_dtype(vlen=str)

JSON_IDENTIFIER = 'Content-Type: application/json '

VALID_PROPERTY_LOCATIONS = {
    "connection_table_properties",
    "device_properties",
    "unit_conversion_parameters"
    }

if PY2:
    str = unicode


def is_json(value):
    if isinstance(value, bytes):
        return value[:len(JSON_IDENTIFIER)] == JSON_IDENTIFIER.encode('utf8')
    elif isinstance(value, str):
        return value.startswith(JSON_IDENTIFIER)
    return False


def serialise(value):
    json_string = json.dumps(value)
    return JSON_IDENTIFIER + json_string


def deserialise(value):
    assert is_json(value)
    return json.loads(value[len(JSON_IDENTIFIER):])


def set_device_properties(h5_file, device_name, properties):
    gp = h5_file['devices/' + device_name]
    for key, val in properties.items():
        try:
            # Workaround for h5py not supporting None but not raising a TypeError:
            if val is None:
                raise TypeError('has no native HDF5 equivalent')
            gp.attrs[key] = val
        except TypeError as e:
            # If type not supported by HDF5, store as JSON
            if 'has no native HDF5 equivalent' in str(e):
                json_string = serialise(val)
                gp.attrs[key] = json_string
            else:
                raise


def _get_device_properties(h5_file, device_name):
    gp = h5_file['devices/' + device_name]
    properties = {}
    for key, val in gp.attrs.items():
        # Deserialize values if stored as JSON
        if is_json(val):
            properties[key] = deserialise(val)
        else:
            properties[key] = val
    return properties


def _get_con_table_properties(h5_file, device_name):
    dataset = h5_file['connection table']

    # Compare with the name in the connection table
    # whether it is np.bytes_ or vlenstr:
    namecol_dtype = dataset['name'].dtype
    if namecol_dtype.type is np.bytes_:
        device_name = device_name.encode('utf8')
    elif namecol_dtype is vlenstring:
        pass
    else:
        raise TypeError(namecol_dtype)

    row = dataset[dataset['name'] == device_name][0]
    json_string = row['properties']
    return deserialise(json_string)


def _get_unit_conversion_parameters(h5_file, device_name):
    dataset = h5_file['connection table']

    # Compare with the name in the connection table
    # whether it is np.bytes_ or vlenstr:
    namecol_dtype = dataset['name'].dtype
    if namecol_dtype.type is np.bytes_:
        device_name = device_name.encode('utf8')
    elif namecol_dtype is vlenstring:
        pass
    else:
        raise TypeError(namecol_dtype)

    row = dataset[dataset['name'] == device_name][0]
    json_string = row['unit conversion params']
    return deserialise(json_string)


def get(h5_file, device_name, location):
    if location == 'device_properties':
        return _get_device_properties(h5_file, device_name)
    elif location == 'connection_table_properties':
        return _get_con_table_properties(h5_file, device_name)
    elif location == 'unit_conversion_parameters':
        return _get_unit_conversion_parameters(h5_file, device_name)
    else:
        raise ValueError('location must be one of %s'%str(VALID_PROPERTY_LOCATIONS))
