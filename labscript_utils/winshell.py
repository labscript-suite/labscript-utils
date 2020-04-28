from __future__ import division, unicode_literals, print_function, absolute_import

import os
import sys
import shutil
if sys.version_info.major == 2:
    str = unicode

from labscript_utils import labscript_suite_profile, labscript_utils_dir
from labscript_utils.versions import get_import_path

APPS = ['runmanager', 'runviewer', 'blacs', 'lyse']

def launcher_name(appname):
    """Return the name of the launcher file for a given program. 
    This will be used for the launchers and start menu shortcuts"""
    name = 'labscript suite'
    # Add conda env name, if any and if not the base env:
    env = os.getenv('CONDA_DEFAULT_ENV')
    if env is not None and env != 'base':
        name += ' (%s)' % env
    name += ' - %s' % appname
    if sys.platform == 'win32':
        name += '.lnk'
    elif sys.platform == 'linux':
        name += '.desktop'
    elif sys.platform == 'darwin':
        raise NotImplementedError
    return name

def launch_command(appname):
    """Return target and arguments for launching the given app. Result is wrapped in a
    launcher script, winluncher.py, which runs the app in the current conda environment,
    if any.
    """
    target = sys.executable.lower()
    if not target.endswith('w.exe'):
        target = target.lower().replace('.exe', 'w.exe')

    # Wrap the command in call to our launcher script:
    WINLAUNCHER = os.path.join(labscript_utils_dir, 'winlauncher.py')
    args = [WINLAUNCHER]

    CONDA_PREFIX = os.getenv('CONDA_PREFIX')
    CONDA_DEFAULT_ENV = os.getenv('CONDA_DEFAULT_ENV')
    if CONDA_PREFIX is not None and CONDA_DEFAULT_ENV is not None:
        # Tell the launcher script to configure the given conda environment:
        args += ['-n', CONDA_DEFAULT_ENV, '-p', CONDA_PREFIX]

    # Add the actual path to the __main__ script of the app:
    args += [os.path.join(get_import_path(appname), appname, '__main__.py')]

    # Quote for spaces etc in the target and args list:
    target = '"%s"' % target
    arglist = ' '.join(['"%s"' % arg for arg in args])

    return target, arglist


# Including the profile directory and python interpreter in the below AppId strings
# ensures they are unique to the profile location and any conda env or virtualenv. If
# they were not, then switching or creating new labscript suite profile directories
# could make the Windows AppId API behave unpredictably. Shortcuts don't work, and icons
# are broken. This if of particular importance when developing on the same machine as
# you are deploying to.
_INSTALL = '%s.%s' % (labscript_suite_profile, sys.executable)
appids = {
    app: 'Monashbec.Labscript.%s.%s' % (app.capitalize(), _INSTALL) for app in APPS
}

# The display name of the apps:
app_descriptions = {app: launcher_name(app).replace('.lnk', '') for app in APPS}

if os.name == 'nt':
    from win32com.shell import shell, shellcon
    from win32com.client import Dispatch
    from win32com.propsys import propsys, pscon
    import pythoncom
    objShell = Dispatch('WScript.Shell')
    WINDOWS = True
else:
    WINDOWS = False

def _check_windows():
    if not WINDOWS:
        msg = "winshell functions are Windows only"
        raise RuntimeError(msg)

def make_shortcut(appname, directory=labscript_suite_profile):
    """Create a shortcut file in the labscript suite install dir for the given app"""
    _check_windows()
    shortcut_path = os.path.join(directory, launcher_name(appname))
    if os.path.exists(shortcut_path):
        os.unlink(shortcut_path)
    app_dir = os.path.join(get_import_path(appname), appname)
    shortcut = objShell.CreateShortcut(shortcut_path)
    target, args = launch_command(appname)
    shortcut.TargetPath = target
    shortcut.Arguments = args
    # TODO: read this from labconfig
    shortcut.WorkingDirectory = os.path.join(labscript_suite_profile, 'userlib')
    shortcut.IconLocation = os.path.join(app_dir, appname + '.ico')
    shortcut.Description = app_descriptions[appname]
    shortcut.save()

    store = propsys.SHGetPropertyStoreFromParsingName(
        shortcut_path, None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
    )
    store.SetValue(
        pscon.PKEY_AppUserModel_ID,
        propsys.PROPVARIANTType(str(appids[appname]), pythoncom.VT_LPWSTR),
    )
    store.Commit()

    return shortcut_path


def set_appusermodel(
    window_id,
    appid=None,
    icon_path=None,
    relaunch_command=None,
    relaunch_display_name=None,
    appname=None,
):
    """Set the appID details for the window, configuring how it appears in the taskbar
    and its pinning/relaunching behaviour. If appid, icon_path, relaunch_command or
    relaunch_display_name are None, they will be inferred from the appname, which must
    not be None if the other arguments are not provided. If the appid matches one of our
    known apps, then the other arguments will be ignored, as if appname was passed in
    and all other arguments were None. This is so that we can fix faulty relaunch
    commands being produced by older versions of the apps whilst accepting how they call
    us, without crashing, for backwards compatibility."""
    _check_windows()

    if appid is not None:
        for known_appname, known_appid in appids.items():
            if appid == known_appid:
                appname = known_appname
                appid = icon_path = relaunch_command = relaunch_display_name = None

    if appid is None:
        appid = appids[appname]
    if icon_path is None:
        icon_path = os.path.join(get_import_path(appname), appname + '.ico')
    if relaunch_command is None:
        target, args = launch_command(appname)
        relaunch_command = ' '.join([target, args])
    if relaunch_display_name is None:
        relaunch_display_name = app_descriptions[appname]

    store = propsys.SHGetPropertyStoreForWindow(window_id, propsys.IID_IPropertyStore)
    id = store.GetValue(pscon.PKEY_AppUserModel_ID)
    store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(appid))
    store.SetValue(
        pscon.PKEY_AppUserModel_RelaunchCommand,
        propsys.PROPVARIANTType(relaunch_command),
    )
    store.SetValue(
        pscon.PKEY_AppUserModel_RelaunchDisplayNameResource,
        propsys.PROPVARIANTType(relaunch_display_name),
    )
    store.SetValue(
        pscon.PKEY_AppUserModel_RelaunchIconResource, propsys.PROPVARIANTType(icon_path)
    )

def add_to_start_menu(shortcut):
    _check_windows()
    start_menu_programs = objShell.SpecialFolders("Programs")
    shutil.copy(shortcut, start_menu_programs)

def is_in_start_menu(name):
    """Whether an item with the same basename as the given name is in the start menu"""
    _check_windows()
    start_menu_programs = objShell.SpecialFolders("Programs")
    return os.path.basename(name) in os.listdir(start_menu_programs)

def remove_from_start_menu(name):
    """Removes given .lnk file from the start menu. If entry not present, does
    nothing."""
    _check_windows()
    name = os.path.basename(name)
    start_menu_programs = objShell.SpecialFolders("Programs")
    try:
        os.unlink(os.path.join(start_menu_programs, name))
    except OSError:
        pass

def clean_start_menu():
    """Delete from the start menu any shortcut with 'labscript suite' in the name, whose
    target does not exist"""
    _check_windows()
    start_menu = objShell.SpecialFolders("Programs")
    for name in os.listdir(start_menu):
        if 'labscript suite' in name:
            shortcut_path = os.path.join(start_menu, name)
            shortcut = objShell.CreateShortcut(shortcut_path)
            if not os.path.exists(shortcut.Targetpath):
                os.unlink(shortcut_path)

def update_if_pinned(shortcut):
    """If a shortcut with the same name is pinned to the taskbar, delete it and replace
    it with the given shortcut"""
    basename = os.path.basename(shortcut)
    appdata = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, None, 0)
    taskbar_pinned_dir = os.path.join(
        appdata,
        'Microsoft',
        'Internet Explorer',
        'Quick Launch',
        'User Pinned',
        'TaskBar',
    )
    if basename in os.listdir(taskbar_pinned_dir):
        print("Updating pinned shortcut %s" % basename)
        os.unlink(os.path.join(taskbar_pinned_dir, basename))
        shutil.copy(shortcut, taskbar_pinned_dir)

def fix_shortcuts():
    """Delete and remake labscript suite application shortcuts and start-menu entries.
    This can help fix issues caused by old shortcuts not interacting well with newer
    anaconda installations."""
    _check_windows()
    print("Remaking labscript suite application shortcuts...")
    for name in sorted(os.listdir(labscript_suite_profile)):
        name = name.lower()
        if (
            name.endswith('.lnk')
            and is_in_start_menu(name)
            and any(appname in name for appname in APPS)
        ):
            print("deleting shortcut:", name)
            remove_from_start_menu(name)
            os.unlink(os.path.join(labscript_suite_profile, name))
    for appname in sorted(APPS):
        print("creating shortcut:", launcher_name(appname))
        shortcut_path = make_shortcut(appname)
        add_to_start_menu(shortcut_path)
        update_if_pinned(shortcut_path)
    print("done")


if __name__ == '__main__':
    if '--fix-shortcuts' in sys.argv:
        fix_shortcuts()
