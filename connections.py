#####################################################################
#                                                                   #
# /connections.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from __future__ import division, unicode_literals, print_function, absolute_import
import labscript_utils.h5_lock, h5py
import labscript_utils.properties
import logging
import labscript_utils.excepthook
import numpy as np
import copy
import ast
from labscript_utils.dict_diff import dict_diff
import sys
from zprocess import raise_exception_in_thread
from labscript_utils import PY2
if PY2:
    str = unicode

def _ensure_str(s):
    """convert bytestrings and numpy strings to python strings"""
    return s.decode() if isinstance(s, bytes) else str(s)


class ConnectionTable(object):    
    def __init__(self, h5file, logging_prefix=None):
        """Object to represent a connection table. Set logging prefix if you
        desire logging. Log used will be <prefix>.ConnectionTable"""
        self.filepath = h5file
        self.logger = None
        if logging_prefix is not None:
            self.logger = logging.getLogger('{}.ConnectionTable'.format(logging_prefix))
            self.logger.debug('Parsing connection table from %s'%h5file)
            
        self.toplevel_children = {}
        self.table = {}
        self.master_pseudoclock = None
        self.raw_table = np.empty(0)

        try:
            with h5py.File(h5file,'r') as hdf5_file:
                try:
                    dataset = hdf5_file['connection table']
                except Exception:
                    msg = 'could not open connection table dataset in %s' % h5file
                    if self.logger: self.logger.error(msg)
                    raise_exception_in_thread(sys.exc_info())
                    return

                self.raw_table = dataset[:]
                try:
                    self.master_pseudoclock = _ensure_str(dataset.attrs['master_pseudoclock'])
                except KeyError:
                    pass

                try:
                    all_connections = [Connection(raw_row) for raw_row in self.raw_table]
                    self.table = {connection.name: connection for connection in all_connections}
                    for name, connection in self.table.items():
                        connection._populate_relatives(self.table)
                        if connection.parent_port is None:
                            self.toplevel_children[name] = connection
                except Exception:
                    msg = 'Could not parse connection table in %s' % h5file
                    if self.logger: self.logger.error(msg)
                    raise_exception_in_thread(sys.exc_info())

        except Exception:
            msg = 'Could not open connection table file %s' % h5file
            if self.logger: self.logger.exception(msg)
            raise_exception_in_thread(sys.exc_info())

    def assert_superset(self, other):
        # let's check that we're a superset of the connection table in "other"
        if not isinstance(other, ConnectionTable):
            msg = "Loaded file is not a valid connection table"
            raise TypeError(msg)
        
        missing = []    # things I don't know exist
        incompat = []   # things that are different from what I expect
        
        for name, other_connection in other.table.items():
            # does it exist?
            try:
                connection = self.table[name]
            except KeyError:
                missing.append('  ' + name)
            else:
                # is it the same?   
                if connection != other_connection:
                    diff = connection.diff(other_connection)
                    msg = '  ' + name + ':\n'
                    for key, (ours, theirs) in diff.items():
                        if isinstance(ours, dict) and isinstance(theirs, dict):
                            msg += '    {}:\n'.format(key)
                            subdiff = dict_diff(ours, theirs)
                            for key, (ours, theirs) in subdiff.items():
                                msg += '      {}: {} != {}'.format(key, ours, theirs)
                        else:
                            msg += '    {}: {} != {}'.format(key, ours, theirs)
                    incompat.append(msg)
        
        # construct a human-readable explanation
        errmsg = ""
        if len(missing) > 0:
            errmsg += '\nDevices that do not exist in the connection table:\n  '+'\n'.join(missing)
        if len(incompat) > 0:
            errmsg += '\nDevices with incompatible settings:\n'+'\n'.join(incompat)
        
        # if there is no error message, then everything must be good!
        if errmsg:
            msg = "Cannot execute script as connection tables do not match." + errmsg
            raise Exception(msg)
        
    def compare_to(self, other):
        if not isinstance(other, ConnectionTable):
            return False, {"error": "The connection table passed in is not a valid connection table"}
        error = {}
        # Check if top level children in other table are a subset of self.        
        for name, connection in other.toplevel_children.items():
            if not name in self.toplevel_children:
                if self.logger: self.logger.error('missing: %s '% str(name))
                if "children_missing" not in error:
                    error["children_missing"] = {}
                error["children_missing"][name] = True
            else:
                # for each top level child in other, check if children of that object are also children of the child in self.
                result, child_error = self.toplevel_children[name].compare_to(connection)
                if not result:
                    #TODO more info on what doesn't match? Print a diff and return it as part of the message?
                    if self.logger: self.logger.error('Connection table mismatch')
                    if "children" not in error:
                        error["children"] = {}
                    error["children"][name] = child_error
                
        if error != {}:
            return False,error
        else:
            return True,error

    def print_details(self):
        for key, value in self.toplevel_children.items():
            print(key)
            value.print_details('  ')
    
    def get_attached_devices(self):
        """Finds out which devices in the connection table are
        connected to BLACS, based on whether their 'BLACS_connection'
        attribute is non-empty. Returns a dictionary of them in the form
        {device_instance_name: labscript_class_name}"""
        attached_devices = {}
        for name, device in self.table.items():
            if device.BLACS_connection:
                # The device is connected to BLACS. Save its name and class:
                attached_devices[name] = device.device_class
        return attached_devices
        
    # Returns the "Connection" object which is a child of "parent_name",
    # connected via "parent_port" Eg, Returns the child of "pulseblaster_0"
    # connected via "dds 0"
    def find_child(self, parent_name, parent_port):
        for name, connection in self.table.items():
            if (connection.parent_name == parent_name 
                    and connection.parent_port == parent_port):
                return connection
        return None
    
    def find_by_name(self,name):
        name = _ensure_str(name)
        for device_name, connection in self.toplevel_children.items():
            if device_name == name:
                return connection
            else:
                result = connection.find_by_name(name)
                if result is not None:
                    return result
        return None

    def remove_device(self, device_name):
        """Removes a device from the ConnectionTable, but keeps it in the
        raw_table. This can help make comparissons of connection tables fail
        for tables with broken devices."""
        if device_name in self.toplevel_children:
            del self.toplevel_children[device_name]
        if device_name == self.master_pseudoclock:
            self.master_pseudoclock = None
        del self.table[device_name]


class Connection(object):
    """A class to represent a row in the connection table, present the
    contents as instance attributes after deserialising their contents, and
    providing default values for backward compatibility with older HDF5 files.
    Contains links to Connection objects for child devices of each device"""
    _defaults = {'unit conversion class': None,
                'unit conversion params': {},
                'BLACS_connection': "",
                'properties': {}}

    def __init__(self, raw_row):

        # Populate a dict with the defaults:
        self._rowdict = self._defaults.copy()

        # Put the given values in, overwriting the defaults if applicable:
        deserialised_items = {_ensure_str(name): self._deserialise(name, value)
                              for name, value in zip(raw_row.dtype.names, raw_row)}

        self._rowdict.update(deserialised_items)
            
        # Populate attributes:
        self.name = self._rowdict['name']
        self.device_class = self._rowdict['class']
        self.parent_name = self._rowdict['parent']
        self.parent_port = self._rowdict['parent port']
        self.unit_conversion_class = self._rowdict['unit conversion class']
        self._unit_conversion_params = self._rowdict['unit conversion params']
        self.BLACS_connection = self._rowdict['BLACS_connection']
        self._properties = self._rowdict['properties']
        
        # To be populated by self._populate_relatives:
        self.child_list = {}
        self.parent = None
        
    def _deserialise(self, name, value):
        """deserialise one item of the row depending on what it is"""
        name == _ensure_str(name)
        if name in ['parent port', 'unit conversion class']:
            # If no unit conversion class, or parent port, set to the object
            # None, otherwise leave as the parent port string or unit
            # conversion class name as a (unicode) string
            if _ensure_str(value) == 'None':
                return None
        elif name in ['unit conversion params', 'properties']:
            # deserialise a dict that is stored as a string. In older
            # labscript these were repr() of the dict, in newer they are
            # stored as JSON."""
            if labscript_utils.properties.is_json(value):
                return labscript_utils.properties.deserialise(value)
            else:
                # Backward compatibility with older hdf5 files:
                return ast.literal_eval(value)
        return _ensure_str(value)

    def _populate_relatives(self, table):
        """Populate child devices based on a list of other connection objects,
        and set self.parent to our parent device."""
        for name, connection in table.items():
            if connection.parent_name == self.name:
                self.child_list[connection.name] = connection
            if name == self.parent_name:
                self.parent = connection

    def __eq__(self, other):
        return self._rowdict == other._rowdict

    def __ne__(self, other):
        return self._rowdict != other._rowdict

    @property
    def unit_conversion_params(self):
        # Return a copy so calling code can't modify our instance attribute
        return copy.deepcopy(self._unit_conversion_params)
        
    @property
    def properties(self):
        # Return a copy so calling code can't modify our instance attribute
        return copy.deepcopy(self._properties)
        
    def diff(self, other):
        return dict_diff(self._rowdict, other._rowdict)

    def compare_to(self, other_connection):
        if not isinstance(other_connection,Connection):
            return False,{"error":"Internal Error. Connection Table object is corrupted."}
            
        error = {}
        # Compare all parameters between this connection, and other connection
        if self.name != other_connection.name:
            error["name"] = True
        if self.device_class != other_connection.device_class:
            error["device_class"] = True
        if self.parent_port != other_connection.parent_port:
            error["parent_port"] = True
        if self.unit_conversion_class != other_connection.unit_conversion_class:
            error["unit_conversion_class"] = True
        if self.unit_conversion_params != other_connection.unit_conversion_params:
            error["unit_conversion_params"] = True
        if self.BLACS_connection != other_connection.BLACS_connection:
            error["BLACS_connection"] = True
        if self.properties != other_connection.properties:
            error["properties"] = True
        
        # for each child in other_connection, check that the child also exists here
        for name, connection in other_connection.child_list.items():
            if not name in self.child_list:
                error.setdefault("children_missing",{})
                error["children_missing"][name] = True
                
            else:    
                # call compare_to on child so that we can check it's children!
                result, child_error = self.child_list[name].compare_to(connection)
                if not result:
                    error.setdefault("children",{})
                    error["children"][name] = child_error
                
        # We made it!
        if error != {}:
            return False, error
        else:
            return True, error
        
    def print_details(self,indent):
        for name, child in self.child_list.items():
            print(indent + name)
            child.print_details(indent + '  ')
    
    def find_child(self, parent_name, parent_port):
        for name, connection in self.child_list.items():
            if connection.parent_name == parent_name and connection.parent_port == parent_port:
                return connection
        
        # This is done separately to the above iteration for speed. 
        # We search for all children first, before going down another layer.
        for name, connection in self.child_list.items():
            result = connection.find_child(parent_name, parent_port)
            if result is not None:
                return result
        
        return None

    def find_by_name(self, name):
        name = _ensure_str(name)
        for device_name, connection in self.child_list.items():
            if device_name == name:
                return connection
            else:
                result = connection.find_by_name(name)
                if result is not None:
                    return result
        return None    


# if __name__ == '__main__':
#     a = ConnectionTable('/home/bilbo/labscript_suite/labconfig/bilbo-Precision-5520_BLACS.h5')
#     c = ConnectionTable('/home/bilbo/labscript_shared/Experiments/cjb7_dev/connectiontable.h5')
#     c.print_details()
#     d = ConnectionTable('/home/bilbo/labscript_shared/Experiments/cjb7_dev/connectiontable.h5')
#     list(d.toplevel_children.values())[0]._rowdict['properties']['test'] = 'fake_property'
#     del c.table['bragg_beam_0']
#     c.assert_superset(d)