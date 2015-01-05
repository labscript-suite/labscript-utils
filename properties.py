import sys
import json
import numpy as np

JSON_IDENTIFIER = 'Content-Type: application/json '

VALID_PROPERTY_LOCATIONS = {
    "connection_table_properties",
    "device_properties",
    "unit_conversion_parameters"
    }

if sys.version < '3':
    STRING_DATATYPES = [str, np.string_, unicode]
else:
    STRING_DATATYPES = [str, np.string_, bytes]


def serialise(value):
    json_string = json.dumps(value)
    return JSON_IDENTIFIER + json_string


def deserialise(value):
    assert value.startswith(JSON_IDENTIFIER)
    return json.loads(value[len(JSON_IDENTIFIER):])
    # return json.loads(value.replace(JSON_IDENTIFIER, '', 1))
    # return json.loads(value.split(JSON_IDENTIFIER, 1)[1])


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
            if 'has no native HDF5 equivalent' in e.message:
                json_string = serialise(val)
                gp.attrs.create(key, json_string)
            else:
                raise


def _get_device_properties(h5_file, device_name):
    gp = h5_file['devices/' + device_name]
    properties = {}
    for key, val in gp.attrs.items():
        # Deserialize values if stored as JSON
        if type(val) in STRING_DATATYPES:
            if val.startswith(JSON_IDENTIFIER):
                properties[key] = deserialise(val)
            else:
                properties[key] = val
        else:
            properties[key] = val
    return properties

def _get_con_table_properties(h5_file, device_name):
    dataset = h5_file['connection table']
    row = dataset[dataset['name'] == device_name][0]
    json_string = row['properties']
    return deserialise(json_string)


def _get_unit_conversion_parameters(h5_file, device_name):
    dataset = h5_file['connection table']
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
