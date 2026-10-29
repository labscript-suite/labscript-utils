import sys
import os
import shutil
import configparser
import keyword
import secrets
from pathlib import Path
from zprocess.security import generate_shared_secret
from labscript_profile import LABSCRIPT_SUITE_PROFILE, default_labconfig_path
import argparse

_here = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILE_CONTENTS = os.path.join(_here, 'default_profile')


def write_shared_secret(shared_secret, directory):
    """Write a zprocess shared secret to a new file in the given directory and return
    its filepath"""
    path = Path(directory, f'zpsecret-{secrets.token_hex(4)}.key')
    path.write_text(shared_secret)
    return path


def validate_apparatus_name(apparatus_name):
    """Raise ValueError unless apparatus_name is a valid Python identifier that is not a
    keyword. The apparatus name is the name of a package in labscriptlib."""
    if not apparatus_name.isidentifier() or keyword.iskeyword(apparatus_name):
        raise ValueError(
            f"Apparatus name {apparatus_name!r} is not a valid Python identifier. The "
            "apparatus name is the name of a package in labscriptlib, so it must consist "
            "of letters, digits and underscores, must not start with a digit, and must "
            "not be a Python keyword."
        )


def make_labconfig_file(shared_secret, apparatus_name = None):
    """Create labconfig file from template
    
    Parameters
    ----------
    shared_secret: str
        zprocess shared secret, which is written to a file next to the labconfig file
    apparatus_name: str, optional
        Overrides the default apparatus name with the provided one if not None
    """

    source_path = os.path.join(LABSCRIPT_SUITE_PROFILE, 'labconfig', 'example.ini')
    target_path = default_labconfig_path()
    if os.path.exists(target_path):
        raise FileExistsError(target_path)
    with open(source_path) as infile, open(target_path, 'w') as outfile:
        data = infile.read()
        data = data.replace('\\', os.path.sep)
        outfile.write(data)

    # Now change some things about it:
    config = configparser.ConfigParser(interpolation=None)
    config.read(target_path)
    if sys.platform != 'win32':
        config.set('programs', 'text_editor', '')
        config.set('programs', 'hdf5_viewer', '')
        config.set('DEFAULT', 'shared_drive', '$HOME/labscript_shared')
    shared_secret_path = write_shared_secret(shared_secret, target_path.parent)
    shared_secret_entry = Path(
        '%(labscript_suite)s', shared_secret_path.relative_to(LABSCRIPT_SUITE_PROFILE)
    )
    config.set('security', 'shared_secret', str(shared_secret_entry))
    if apparatus_name is not None:
        print(f'\tSetting apparatus name to \'{apparatus_name}\'')
        config.set('DEFAULT', 'apparatus_name', apparatus_name)

    with open(target_path, 'w') as f:
        config.write(f)

def make_runmanager_config_file():
    """Write the runmanager configuration file that the labconfig file names as
    `autoload_config_file`, with the example experiment as the labscript file, so that
    runmanager opens the example experiment on its first run."""
    from labscript_utils.labconfig import save_appconfig

    config = configparser.ConfigParser(
        defaults={'labscript_suite': str(LABSCRIPT_SUITE_PROFILE)}
    )
    config.read(default_labconfig_path())
    config_path = Path(config['runmanager']['autoload_config_file'])
    labscript_file = Path(config['DEFAULT']['labscriptlib'], 'example_experiment.py')
    save_appconfig(
        config_path,
        {
            'runmanager_state': {
                'current_labscript_file': str(labscript_file),
                'is_using_default_shot_output_folder': True,
            }
        },
    )


def compile_connection_table():
    """Compile the connection table defined in the labconfig file
    
    The output is placed in the location defined by the labconfig file.
    """

    try:
        import runmanager
    except ImportError:
        # if runmanager doesn't import, skip compilation
        return

    config = configparser.ConfigParser(defaults = {'labscript_suite': str(LABSCRIPT_SUITE_PROFILE)})
    config.read(default_labconfig_path())

    # The path to the user's connection_table.py script
    script_path = os.path.expandvars(config['paths']['connection_table_py'])
    # path to the connection_table.h5 destination
    output_h5_path = os.path.expandvars(config['paths']['connection_table_h5'])
    # create output directory, if needed
    Path(output_h5_path).parent.mkdir(parents=True, exist_ok=True)
    # compile the h5 file
    runmanager.new_globals_file(output_h5_path)

    def dummy_callback(success):
        pass

    runmanager.compile_labscript_async(labscript_file = script_path,
                                       run_file = output_h5_path,
                                       stream_port = None,
                                       done_callback = dummy_callback)
    print(f'\tOutput written to {output_h5_path}')

def create_profile_cli():
    """Function that defines the labscript-profile-create command

    Parses CLI arguments and calls :func:`~.create_profile`.
    """

    # capture CMD arguments
    parser = argparse.ArgumentParser(prog='labscript-profile-create',
                                     description='Initialises a default labscript profile'
                                     )

    parser.add_argument('-n', '--apparatus_name',
                        type=str,
                        help='Sets the apparatus_name in the labconfig file and the name '
                             'of the apparatus package in labscriptlib. Must be a valid '
                             'Python identifier: letters, digits and underscores, not '
                             'starting with a digit, and not a Python keyword. Defaults '
                             'to example_apparatus',
                        )
    parser.add_argument('-c', '--compile',
                        action='store_true',
                        help='Enables compilation of the default example connection table',
                        default=False)
    
    args = parser.parse_args()

    if args.apparatus_name is not None:
        try:
            validate_apparatus_name(args.apparatus_name)
        except ValueError as e:
            parser.error(str(e))

    create_profile(args.apparatus_name, args.compile)

def create_profile(apparatus_name = None, compile_table = False):
    """Create the labscript suite profile directory, `~/labscript-suite`.

    Copies the contents of `labscript_profile/default_profile` into the profile
    directory, writes the labconfig file of this computer from `example.ini` with a new
    shared secret in a key file next to it, and writes the runmanager configuration
    file that the labconfig file names as `autoload_config_file`.

    Raises `FileExistsError`, before copying anything, if the profile directory
    already contains `labconfig`, `userlib` or `app_saved_configs`.

    Parameters
    ----------
    apparatus_name: str, optional
        The apparatus name to set in the labconfig file. The `example_apparatus`
        directories of the profile are renamed to it. If None, the apparatus name is
        `example_apparatus`. Raises `ValueError` if it is not a valid Python
        identifier.
    compile_table: bool, optional
        Whether to compile the example connection table to the `connection_table_h5`
        path of the labconfig file. The table is compiled only if runmanager is
        installed. Default is False.
    """

    if apparatus_name is not None:
        validate_apparatus_name(apparatus_name)

    # This raises zprocess.security.CurveNotSupported if libzmq was built without
    # CurveZMQ, so it comes before anything is written:
    shared_secret = generate_shared_secret()

    src = Path(DEFAULT_PROFILE_CONTENTS)
    dest = Path(LABSCRIPT_SUITE_PROFILE)
    print(f'Creating labscript profile at {LABSCRIPT_SUITE_PROFILE}')
    # Profile directory may exist already, but we will error if it contains any of the
    # sub-directories we want to copy into it:
    os.makedirs(dest, exist_ok=True)
    # Preferable to raise errors if anything exists before copying anything, rather than
    # do a partial copy before hitting an error:
    for src_file in src.iterdir():
        dest_file = dest / src_file.name
        if dest_file.exists():
            raise FileExistsError(dest_file)
    for src_file in src.iterdir():
        dest_file = dest / src_file.name
        if src_file.is_dir():
            shutil.copytree(src_file, dest_file)
        else:
            shutil.copy2(src_file, dest_file)

    print('Writing labconfig file')
    make_labconfig_file(shared_secret, apparatus_name)

    # rename apparatus directories
    if apparatus_name is not None:
        print('\tRenaming apparatus directories')
        for path in dest.glob('**/example_apparatus/'):
            new_path = Path(str(path).replace('example_apparatus', apparatus_name))
            path.rename(new_path)

    print('Writing runmanager configuration file')
    make_runmanager_config_file()

    if compile_table:
        print('Compiling the example connection table')
        compile_connection_table()