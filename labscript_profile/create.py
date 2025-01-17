import sys
import os
import shutil
import configparser
from pathlib import Path
from subprocess import check_output
from labscript_profile import LABSCRIPT_SUITE_PROFILE, default_labconfig_path
import argparse

_here = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILE_CONTENTS = os.path.join(_here, 'default_profile')


def make_shared_secret(directory):
    """Create a new zprocess shared secret file in the given directory and return its
    filepath"""
    cmd = [sys.executable, '-m', 'zprocess.makesecret']
    output = check_output(cmd, cwd=directory).decode('utf8')
    for line in output.splitlines():
        if 'zpsecret' in line and '.key' in line:
            return Path(line.strip())
    raise RuntimeError("Could not parse output of zprocess.makesecret")


def make_labconfig_file(apparatus_name = None):
    """Create labconfig file from template
    
    Parameters
    ----------
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
    if sys.platform == 'linux':
        config.set('programs', 'text_editor', 'gedit')
    elif sys.platform == 'darwin':
        config.set('programs', 'text_editor', 'open')
        config.set('programs', 'text_editor_arguments', '-a TextEdit {file}')
    if sys.platform != 'win32':
        config.set('programs', 'hdf5_viewer', 'hdfview')
        config.set('DEFAULT', 'shared_drive', '$HOME/labscript_shared')
    shared_secret = make_shared_secret(target_path.parent)
    shared_secret_entry = Path(
        '%(labscript_suite)s', shared_secret.relative_to(LABSCRIPT_SUITE_PROFILE)
    )
    config.set('security', 'shared_secret', str(shared_secret_entry))
    if apparatus_name is not None:
        print(f'\tSetting apparatus name to \'{apparatus_name}\'')
        config.set('DEFAULT', 'apparatus_name', apparatus_name)

    with open(target_path, 'w') as f:
        config.write(f)

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
                        help='Sets the apparatus_name in the labconfig file. Defaults to example_apparatus',
                        )
    parser.add_argument('-c', '--compile',
                        action='store_true',
                        help='Enables compilation of the default example connection table',
                        default=False)
    
    args = parser.parse_args()

    create_profile(args.apparatus_name, args.compile)

def create_profile(apparatus_name = None, compile_table = False):
    """Function that creates a labscript config profile from the default config

    Parameters
    ----------
    appratus_name: str, optional
        apparatus_name to define in the config.
        If None, defaults to example_apparatus (set in default config file)
    compile_table: bool, optional
        Whether to compile to example connection table defined by the default config file
        Default is False.
    """

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
    make_labconfig_file(apparatus_name)

    # rename apparatus directories
    if apparatus_name is not None:
        print('\tRenaming apparatus directories')
        for path in dest.glob('**/example_apparatus/'):
            new_path = Path(str(path).replace('example_apparatus', apparatus_name))
            path.rename(new_path)

    if compile_table:
        print('Compiling the example connection table')
        compile_connection_table()