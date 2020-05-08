import sys
import os
import shutil
import configparser
from pathlib import Path
from labscript_profile import LABSCRIPT_SUITE_PROFILE, default_labconfig_path

_here = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILE_CONTENTS = os.path.join(_here, 'default_profile')


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
    config = configparser.ConfigParser()
    config.read(target_path)
    config.set('DEFAULT', 'labscript_suite', str(LABSCRIPT_SUITE_PROFILE))
    if sys.platform in ['linux', 'linux2']:
        config.set('programs', 'text_editor', 'gedit')
    elif sys.platform == 'darwin':
        config.set('programs', 'text_editor', 'open')
        config.set('programs', 'text_editor_arguments', '-a TextEdit {file}')
    if sys.platform != 'win32':
        config.set('programs', 'hdf5_viewer', 'hdfview')
        config.set('DEFAULT', 'shared_drive', str(Path.home() / ' labscript_shared'))

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
