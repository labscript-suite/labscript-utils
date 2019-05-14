from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode
import sys
import json
from base64 import b64encode, b64decode
if PY2:    
    from collections import Iterable, Mapping
else:
    from collections.abc import Iterable, Mapping
import numpy as np
import h5py

vlenstring = h5py.special_dtype(vlen=str)

JSON_IDENTIFIER = 'Content-Type: application/json '
BASE64_IDENTIFIER = 'Content-Transfer-Encoding: base64 '

VALID_PROPERTY_LOCATIONS = {
    "connection_table_properties",
    "device_properties",
    "unit_conversion_parameters"
    }

if PY2:
    str = unicode


def _check_dicts(o):
    if isinstance(o, Mapping):
        if not all(isinstance(k, (str, bytes)) for k in o.keys()):
            raise TypeError("Cannot JSON encode dictionary with non-string keys")
        for item in o.values():
            _check_dicts(item)
    elif isinstance(o, Iterable) and not isinstance(o, (str, bytes)):
        for item in o:
            _check_dicts(item)


def _encode_bytestrings(o):
    """Encode all bytestring values (not keys) to base64 with a prefix"""
    if isinstance(o, Mapping):
        return {key: _encode_bytestrings(value) for key, value in o.items()}
    elif isinstance(o, Iterable) and not isinstance(o, (str, bytes)):
        return list([_encode_bytestrings(value) for value in o])
    elif isinstance(o, bytes):
        return BASE64_IDENTIFIER + str(b64encode(o).decode())
    else:
        return o


def _decode_bytestrings(o):
    """Decode all base64-encoded values (not keys) to bytestrings"""
    if isinstance(o, Mapping):
        return {key: _decode_bytestrings(value) for key, value in o.items()}
    elif isinstance(o, Iterable) and not isinstance(o, (str, bytes)):
        return list([_decode_bytestrings(value) for value in o])
    elif isinstance(o, str) and o.startswith(BASE64_IDENTIFIER):
        return b64decode(o[len(BASE64_IDENTIFIER):])
    else:
        return o


def is_json(value):
    if isinstance(value, bytes):
        return value[:len(JSON_IDENTIFIER)] == JSON_IDENTIFIER.encode('utf8')
    elif isinstance(value, str):
        return value.startswith(JSON_IDENTIFIER)
    return False


def _default(o):
    # Workaround for https://bugs.python.org/issue24313
    if isinstance(o, np.integer):
        return int(o)
    raise TypeError


def serialise(value):
    _check_dicts(value)
    if not PY2:
        value = _encode_bytestrings(value)
    json_string = json.dumps(value, default=_default)
    return JSON_IDENTIFIER + json_string


def deserialise(value):
    assert is_json(value)
    return _decode_bytestrings(json.loads(value[len(JSON_IDENTIFIER):]))


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
