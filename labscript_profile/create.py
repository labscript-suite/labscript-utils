import sys
import os
import shutil
import configparser
from pathlib import Path
from subprocess import check_output
from labscript_profile import LABSCRIPT_SUITE_PROFILE, default_labconfig_path

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


def make_labconfig_file():
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

    with open(target_path, 'w') as f:
        config.write(f)


def create_profile():
    src = Path(DEFAULT_PROFILE_CONTENTS)
    dest = Path(LABSCRIPT_SUITE_PROFILE)
    # Profile directory may exist already, but we will error if it contains any of the
    # files or directories we want to copy into it:
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

    make_labconfig_file()
