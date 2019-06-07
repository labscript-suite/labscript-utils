#####################################################################
#                                                                   #
# ls_zprocess.py                                                    #
#                                                                   #
# Copyright 2013, Monash University                                 #
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
from socket import gethostbyname
from distutils.version import LooseVersion
import zmq

from labscript_utils import check_version
check_version('zprocess', '2.13.0', '3.0.0')

import zprocess
import zprocess.process_tree
from zprocess.security import SecureContext
from labscript_utils.labconfig import LabConfig
from labscript_utils import dedent
import zprocess.zlog
import zprocess.zlock
import zprocess.remote


"""This module is a number of wrappers around zprocess objects that configures them with
the settings in LabConfig with regard to security, and the host and port of the zlock
server. Multiprocessing done with these wrappers will automatically be configured
according to LabConfig. Manual configuration can be done by instantiating the objects
directly from zprocess instead.

To use zprocess with LabConfig configuration, use the convenience functions defined at
the bottom of this module.
"""

_cached_config = None

def get_config():
    """Get relevant options from LabConfig, substituting defaults where appropriate and
    return as a dict"""
    global _cached_config
    # Cache the config so it is not loaded multiple times per process:
    if _cached_config is not None:
        return _cached_config

    labconfig = LabConfig()
    config = {}
    try:
        config['zlock_host'] = labconfig.get('servers', 'zlock')
    except (labconfig.NoOptionError, labconfig.NoSectionError):
        msg = "No zlock server specified in labconfig"
        raise RuntimeError(msg)
    try:
        config['zlock_port'] = labconfig.get('ports', 'zlock')
    except (labconfig.NoOptionError, labconfig.NoSectionError):
        config['zlock_port'] = zprocess.zlock.DEFAULT_PORT
    # We hard-code the zlog host and port, since zlog always runs on the computer with
    # the top-level process
    config['zlog_host'] = 'localhost'
    config['zlog_port'] = zprocess.zlog.DEFAULT_PORT
    try:
        config['zprocess_remote_port'] = labconfig.get('ports', 'zprocess_remote')
    except (labconfig.NoOptionError, labconfig.NoSectionError):
        config['zprocess_remote_port'] = zprocess.remote.DEFAULT_PORT
    try:
        shared_secret_file = labconfig.get('security', 'shared_secret')
    except (labconfig.NoOptionError, labconfig.NoSectionError):
        config['shared_secret'] = None
        config['shared_secret_file'] = None
    else:
        config['shared_secret'] = open(shared_secret_file).read().strip()
        config['shared_secret_file'] = shared_secret_file
    try:
        config['allow_insecure'] = labconfig.getboolean('security', 'allow_insecure')
    except (labconfig.NoOptionError, labconfig.NoSectionError):
        # Default will be set to False once the security rollout is complete:
        config['allow_insecure'] = True
    try:
        config['logging_maxBytes'] = labconfig.getint('logging', 'maxBytes')
    except (labconfig.NoOptionError, labconfig.NoSectionError):
        config['logging_maxBytes'] = 1024 * 1024 * 50
    try:
        config['logging_backupCount'] = labconfig.getint('logging', 'backupCount')
    except (labconfig.NoOptionError, labconfig.NoSectionError):
        config['logging_backupCount'] = 1
    _cached_config = config
    return config


class ProcessTree(zprocess.ProcessTree):
    """A singleton zprocess.ProcessTree configured with settings from labconfig for
    security, zlock and zlog. Being a singleton is not enforced - the class can still be
    instantiated as normal - but calling the .instance() classmethod will give the
    singleton."""

    _instance = None

    @classmethod
    def instance(cls):
        # If we are already a child process, return the ProcessTree associated with the
        # connection to our parent. This may not even be an instance of this subclass,
        # but it will be if this subclass was used when calling connect_to_parent().
        instance = zprocess.ProcessTree.instance()
        if instance is not None:
            return instance
        # Otherwise, return previously initialised singleton for the top-level process:
        if cls._instance is not None:
            return cls._instance
        # Otherwise, create that singleton and return it:
        config = get_config()
        cls._instance = cls(
            shared_secret=config['shared_secret'],
            allow_insecure=config['allow_insecure'],
            zlock_host=config['zlock_host'],
            zlock_port=config['zlock_port'],
            zlog_host='localhost',
            zlog_port=config['zlog_port'],
        )
        # Assign this to the default zprocess ProcessTree so that code using deprecated
        # zprocess calls use this ProcessTree:
        zprocess.process_tree._default_process_tree = cls._instance
        # Assign the zlock client as the default zlock server so that code using
        # deprecated zlock calls can use it:
        zprocess.zlock._default_zlock_client = cls._instance.zlock_client

        return cls._instance


class ZMQServer(zprocess.ZMQServer):
    """A ZMQServer configured with security settings from labconfig"""

    def __init__(
        self,
        port=None,
        dtype='pyobj',
        pull_only=False,
        bind_address='tcp://0.0.0.0',
        timeout_interval=None,
        **kwargs
    ):
        # There are ways to process args and exclude the keyword arguments we disallow
        # without having to include the whole function signature above, but they are
        # Python 3 only, so we avoid them for now.
        msg = """keyword argument {} not allowed - it will be set according to
            LabConfig. To make a custom ZMQServer, use zprocess.ZMQserver instead of
            labscript_utils.zprocess.ZMQServer"""

        # Error if these args are provided, since we provide them:
        for kwarg in ['shared_secret', 'allow_insecure']:
            if kwarg in kwargs:
                raise ValueError(dedent(msg.format(kwarg)))

        config = get_config()
        shared_secret = config['shared_secret']
        allow_insecure = config['allow_insecure']

        zprocess.ZMQServer.__init__(
            self,
            port=port,
            dtype=dtype,
            pull_only=pull_only,
            bind_address=bind_address,
            shared_secret=shared_secret,
            allow_insecure=allow_insecure,
            timeout_interval=timeout_interval,
            **kwargs
        )


class ZMQClient(zprocess.ZMQClient):
    """A singleton zprocess.ZMQClient configured with settings from labconfig for
    security.  Being a singleton is not enforced - the class can still be
    instantiated as normal - but calling the .instance() classmethod will give the
    singleton."""

    _instance = None

    def __init__(self):
        config = get_config()
        shared_secret = config['shared_secret']
        allow_insecure = config['allow_insecure']
        zprocess.ZMQClient.__init__(
            self, shared_secret=shared_secret, allow_insecure=allow_insecure
        )

    @classmethod
    def instance(cls):
        # Return previously initialised singleton:
        if cls._instance is None:
            # Create singleton:
            cls._instance = cls()
        return cls._instance
        

class Context(SecureContext):
    """Subclass of zprocess.security.SecureContext configured with settings from
    labconfig, substitutable for a zmq.Context. Can be instantiated to get a unique
    context, or call the .instance() classmethod to possibly get an already-existing
    one. Only use the latter if you do not indent to terminate the context."""
    def __init__(self, io_threads=1, shared_secret=None):
        config = get_config()
        # Allow shared_secret only if it matches what we expect. This is because
        # zprocess SecureContext.instance() will call our __init__ method with the
        # shared secret whether we like it or not, so let's cooperate with that.
        if shared_secret is not None and shared_secret != config['shared_secret']:
            msg = "shared_secret must be None or match labconfig"
            raise ValueError(msg)
        SecureContext.__init__( 
            self, io_threads=io_threads, shared_secret=config['shared_secret']
        )

    @classmethod
    def instance(cls):
        config = get_config()
        # Super required to call unbound class method of parent class:
        return super(Context, cls).instance(shared_secret=config['shared_secret'])

    def socket(self, *args, **kwargs):
        config = get_config()
        kwargs['allow_insecure'] = config['allow_insecure']
        return SecureContext.socket(self, *args, **kwargs)


def Lock(*args, **kwargs):
    if 'read_only' in kwargs and not _zlock_server_supports_readwrite:
        # Ignore read_only argument if the server does not support it:
        del kwargs['read_only']
    return ProcessTree.instance().lock(*args, **kwargs)


def Event(*args, **kwargs):
    return ProcessTree.instance().event(*args, **kwargs)


def Handler(*args, **kwargs):
    return ProcessTree.instance().logging_handler(*args, **kwargs)


def zmq_get(*args, **kwargs):
    return ZMQClient.instance().get(*args, **kwargs)


def zmq_get_multipart(*args, **kwargs):
    return ZMQClient.instance().get_multipart(*args, **kwargs)


def zmq_get_string(*args, **kwargs):
    return ZMQClient.instance().get_string(*args, **kwargs)


def zmq_get_raw(*args, **kwargs):
    return ZMQClient.instance().get_raw(*args, **kwargs)


def zmq_push(*args, **kwargs):
    return ZMQClient.instance().push(*args, **kwargs)


def zmq_push_multipart(*args, **kwargs):
    return ZMQClient.instance().push_multipart(*args, **kwargs)


def zmq_push_string(*args, **kwargs):
    return ZMQClient.instance().push_string(*args, **kwargs)


def zmq_push_raw(*args, **kwargs):
    return ZMQClient.instance().push_raw(*args, **kwargs)


def RemoteProcessClient(host, port=None):
    if port is None:
        config = get_config()
        port = config['zprocess_remote_port']
    return ProcessTree.instance().remote_process_client(host, port)


ZLOCK_DEFAULT_TIMEOUT = 45
_zlock_server_supports_readwrite = False

def connect_to_zlock_server():
    # Ensure we are connected to a zlock server, and start one if one is supposed
    # to be running on localhost but is not.
    client = ProcessTree.instance().zlock_client
    if gethostbyname(client.host) == gethostbyname('localhost'):
        try:
            # short connection timeout if localhost, don't want to
            # waste time:
            client.ping(timeout=0.05)
        except zmq.ZMQError:
            # No zlock server running on localhost. Start one. It will run forever, even
            # after this program exits. This is important for other programs which might
            # be using it. I don't really consider this bad practice since the server is
            # typically supposed to be running all the time:
            zprocess.start_daemon(
                [sys.executable, '-m', 'labscript_utils.zlock', '--daemon']
            )
            # Try again. Longer timeout this time, give it time to start up:
            client.ping(timeout=15)
    else:
        client.ping()

    # Check if the zlock server supports read-write locks:
    global _zlock_server_supports_readwrite
    if hasattr(client, 'get_protocol_version'):
        version = client.get_protocol_version()
        if LooseVersion(version) >= LooseVersion('1.1.0'):
            _zlock_server_supports_readwrite = True

    # The user can call these functions to change the timeouts later if they
    # are not to their liking:
    client.set_default_timeout(ZLOCK_DEFAULT_TIMEOUT)


_connected_to_zlog = False


def ensure_connected_to_zlog():
    """Ensure we are connected to a zlog server. If one is not running and we are the
    top-level process, start a zlog server configured according to LabConfig."""
    global _connected_to_zlog
    if _connected_to_zlog:
        return
    # setup connection with the zlog server:
    client = ProcessTree.instance().zlog_client
    if gethostbyname(client.host) == gethostbyname('localhost'):
        try:
            # short connection timeout if localhost, don't want to
            # waste time:
            client.ping(timeout=0.05)
        except zmq.ZMQError:
            # No zlog server running on localhost. Start one. It will run forever, even
            # after this program exits. This is important for other programs which might
            # be using it. I don't really consider this bad practice since the server is
            # typically supposed to be running all the time:
            zprocess.start_daemon(
                [sys.executable, '-m', 'labscript_utils.zlog', '--daemon']
            )
            # Try again. Longer timeout this time, give it time to start up:
            client.ping(timeout=15)
    else:
        client.ping()
    _connected_to_zlog = True

