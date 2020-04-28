#####################################################################
#                                                                   #
# camera_server.py                                                  #
#                                                                   #
# Copyright 2016, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

import sys
import time
import zprocess
from labscript_utils import check_version
import labscript_utils.shared_drive
# importing this wraps zlock calls around HDF file openings and closings:
import labscript_utils.h5_lock
import h5py
import numpy as np
check_version('zprocess', '1.3.3', '3.0')

# This file implements the protocol for a camera server, that is, a program
# that BLACS can interface with to control cameras. It contains a class that
# acts as a camera server and communicates with BLACS over zeromq. The
# protocol is as below. A user need not implement this protocol themselves,
# they instead should subclass CameraServer and override the
# transition_to_buffered(), transition_to_static(), and abort() methods. An
# example is show at the bottom of this file. Note that the filepath send from
# BLACS to the camera server has a 'network agnostic' prefix - it is assumed
# that BLACS and the camera server may not have the same path to the location
# of the HDF5 file, it may be on a shared drive with different drive
# letters/mount points on the two computers. So BLACS calls
# labscript_utils.shared_drive.path_to_agnostic() on the filepath before
# sending it, and the camera server should call
# labscript_utils.shared_drive.path_to_local() once receiving it. If you
# subclass CameraServer, you don't have to worry about this step, so long as
# the shared drive path is correctly declared in your labconfig file.
#
# All communications are as utf-8 encoded strings.
#
# Ping, can occur at any time:
#   BLACS sends: 'hello'
#   CameraServer responds: 'hello'
#
# transition_to_buffered, occurs when BLACS is preparing to start a shot:
#   BLACS sends: '<utf8-encoded-path-of-h5-file->.h5'
#   CameraServer responds: 'ok'
#   BLACS sends: '' (empty string)
#   (Camera server calls self.transition_to_buffered(), to do any processing
#       it needs to to set up the shot)
#   CameraServer responds: 'done'
#   OR, if exception encountered calling self.transition_to_buffered(), camera
#       server calls self.abort() and then responds with the exception text.
#
# transition_to_static, occurs when BLACS has completed a shot:
#   BLACS sends: 'done'
#   CameraServer responds: 'ok'
#   BLACS sends: '' (empty string)
#   (Camera server calls self.transition_to_static(), to do any processing it
#       needs to do at the end of the shot)
#   CameraServer responds: 'done'
#   OR, if exception encountered calling self.transition_to_static(), camera
#       server calls self.abort() and then responds with the exception text.
#
# abort, can occur at any time:
#   BLACS sends 'abort'
#   (Camera server calls self.abort(), to return things to a sensible state
#       where transition_to_buffered can be called again )
#   CameraServer responds: 'done'
#   OR, if exception encountered calling self.abort(), camera server responds
#       with the exception text.
#

class CameraServer(zprocess.ZMQServer):
    def __init__(self, port):
           zprocess.ZMQServer.__init__(self, port, type='string')
           self._h5_filepath = None

    def handler(self, request_data):
        try:
            print(request_data)
            if request_data == 'hello':
                return 'hello'
            elif request_data.endswith('.h5'):
                self._h5_filepath = labscript_utils.shared_drive.path_to_local(request_data)
                self.send('ok')
                self.recv()
                self.transition_to_buffered(self._h5_filepath)
                return 'done'
            elif request_data == 'done':
                self.send('ok')
                self.recv()
                self.transition_to_static(self._h5_filepath)
                self._h5_filepath = None
                return 'done'
            elif request_data == 'abort':
                self.abort()
                self._h5_filepath = None
                return 'done'
            else:
                raise ValueError('invalid request: %s'%request_data)
        except Exception:
            if self._h5_filepath is not None and request_data != 'abort':
                try:
                    self.abort()
                except Exception as e:
                    sys.stderr.write('Exception in self.abort() while handling another exception:\n{}\n'.format(str(e)))
            self._h5_filepath = None
            raise

    def transition_to_buffered(self, h5_filepath):
        """To be overridden by subclasses. Do any preparatory processing
        before a shot, eg setting exposure times, readying cameras to receive
        triggers etc."""
        print('transition to buffered')

    def transition_to_static(self, h5_filepath):
        """To be overridden by subclasses. Do any post processing after a
        shot, eg computing optical depth, fits, displaying images, saving
        images and results to the h5 file, returning cameras to an idle
        state."""
        print('transition to static')

    def abort(self):
        """To be overridden by subclasses. Return cameras and any other state
        to one in which transition_to_buffered() can be called again. abort()
        will be called if there was an exception in either
        transition_to_buffered() or transtition_to_static(), and so should
        ideally be written to return things to a sensible state even if those
        methods did not complete. Like any cleanup function, abort() should
        proceed to further cleanups even if earlier cleanups fail. As such it
        should make liberal use of try: except: blocks, so that an exception
        in performing one cleanup operation does not stop it from proceeding
        to subsequent cleanup operations"""
        print('abort')


# A minimalistic example of how to subclass a CameraServer:

class TubingenCameraServer(CameraServer):
    """Minimalistic camera server. Transition to buffered and abort are not
    implemented, because we don't need to do anything in those cases. This
    camera server simply writes to the h5 file the images, which have been
    saved to disk during each shot by an external program."""

    def transition_to_buffered(self, h5_filepath):
        # Our minimalistic example doesn't need to implement this method,
        # since the camera we used simply saved images to disk every time
        # it received a trigger, and didn't need any per-shot
        # configuration. But here is where you would put code to get the
        # camera ready for a shot, with its configuration possibly
        # depending on the contents of the h5 file, such as the globals in
        # h5_file['globals'].attrs.
        pass

    def transition_to_static(self, h5_filepath):
        """Read FITS images from file saved by an external program, and save
        them to the h5 file"""
        import pyfits
        start_time = time.time()
        with h5py.File(h5_filepath) as f:
            group = f['devices']['camera']
            if not 'EXPOSURES' in group:
                print('no images taken this shot')
                return
            group = f.create_group('images').create_group('side').create_group('absorption')
            with pyfits.open(r'C:\CameraControl\images\1_0_0.fits') as fits_images:
                image_array = np.array(fits_images[0].data, dtype=float)
                group.create_dataset('atoms',data=image_array)
            with pyfits.open(r'C:\CameraControl\images\1_0_1.fits') as fits_images:
                image_array = np.array(fits_images[0].data, dtype=float)
                group.create_dataset('flat',data=image_array)
            with pyfits.open(r'C:\CameraControl\images\1_0_2.fits') as fits_images:
                image_array = np.array(fits_images[0].data, dtype=float)
                group.create_dataset('dark',data=image_array)
            # Copy over the effective pixel size to a spot that lyse
            # automatically grabs params from:
            effective_pixel_size = f['/devices/camera'].attrs['effective_pixel_size']
            f['images/side'].attrs['effective_pixel_size'] = effective_pixel_size
        print('image saving time: %s s' %str(time.time() - start_time))

    def abort(self):
        # Our minimalistic example doesn't need to implement this method,
        # since the camera we used was always ready and didn't need to be
        # 'reset' to be ready for a new shot. But here is where you would
        # put cleanup code to do so. Likely this would be very similar to
        # transition_to_static, except without saving any data to a h5 file.
        pass

if __name__ == '__main__':

    # How to run a camera server:

    port = 8765
    print('starting camera server on port %d...' % port)
    server = CameraServer(port)
    server.shutdown_on_interrupt()
