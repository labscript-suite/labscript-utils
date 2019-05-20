from __future__ import division, unicode_literals, print_function, absolute_import

import os
import sys
import shutil
if sys.version_info.major == 2:
    str = unicode

for path in sys.path:
    if os.path.exists(os.path.join(path, '.is_labscript_suite_install_dir')):
        labscript_installation = os.path.abspath(path)
        break
else:
    labscript_installation = '<not_installed>'

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
    if os.name == 'nt':
        name += '.lnk'
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
    WINLAUNCHER = os.path.join(
            labscript_installation, 'labscript_utils', 'winlauncher.py'
        )
    args = [WINLAUNCHER]

    CONDA_PREFIX = os.getenv('CONDA_PREFIX')
    CONDA_DEFAULT_ENV = os.getenv('CONDA_DEFAULT_ENV')
    if CONDA_PREFIX is not None and CONDA_DEFAULT_ENV is not None:
        # Tell the launcher script to configure the given conda environment:
        args += ['-n', CONDA_DEFAULT_ENV, '-p', CONDA_PREFIX]

    # Add the actual path to the __main__ script of the app:
    args += [os.path.join(labscript_installation, appname, '__main__.py')]

    # Quote for spaces etc in the target and args list:
    target = '"%s"' % target
    arglist = ' '.join(['"%s"' % arg for arg in args])

    return target, arglist


# Including the install directory and python interpreter in the below AppId strings
# ensures they are unique to the install location and any conda env or virtualenv. If
# they were not, then installing to one directory, uninstalling, and reinstalling to
# another would make the Windows AppId API behave unpredictably. Shortcuts don't work,
# and icons are broken. This if of particular importance when developing on the same
# machine as you are deploying to.
_INSTALL = '%s.%s' % (labscript_installation, sys.executable)
appids = {
    app: 'Monashbec.Labscript.%s.%s' % (app.capitalize(), _INSTALL) for app in APPS
}

# The display name of the apps:
app_descriptions = {app: launcher_name(app).replace('.lnk', '') for app in APPS}

if os.name == 'nt':
    from win32com.shell import shellcon
    from win32com.client import Dispatch
    from win32com.propsys import propsys, pscon
    import pythoncom
    WINDOWS = True
else:
    WINDOWS = False

def _check_windows():
    if not WINDOWS:
        msg = "winshell functions are Windows only"
        raise RuntimeError(msg)

def make_shortcut(appname):
    """Create a shortcut file in the labscript suite install dir for the given app"""
    shortcut_path = os.path.join(labscript_installation, launcher_name(appname))
    app_dir = os.path.join(labscript_installation, appname)
    _check_windows()
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortcut(shortcut_path)
    target, args = launch_command(appname)
    shortcut.TargetPath = target
    shortcut.Arguments = args
    shortcut.WorkingDirectory = '"%s"' % app_dir
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
        icon_path = os.path.join(labscript_installation, appname, appname + '.ico')
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
    objShell = Dispatch("WScript.Shell")
    start_menu_programs = objShell.SpecialFolders("Programs")
    shutil.copy(shortcut, start_menu_programs)

def remove_from_start_menu(name):
    """Removes given .lnk file from the start menu.
    If entry not present, does nothing."""
    _check_windows()
    name = os.path.basename(name)
    objShell = Dispatch("WScript.Shell")
    start_menu_programs = objShell.SpecialFolders("Programs")
    if name in os.listdir(start_menu_programs):
        os.unlink(os.path.join(start_menu_programs, name))


def fix_shortcuts():
    """Delete and remake labscript suite application shortcuts and start-menu entries.
    This can help fix issues caused by old shortcuts not interacting well with newer
    anaconda installations."""
    _check_windows()
    print("Remaking labscript suite application shortcuts...")
    for name in sorted(os.listdir(labscript_installation)):
        if name.lower().endswith('.lnk'):
            print("deleting shortcut:", name)
            remove_from_start_menu(name)
            os.unlink(os.path.join(labscript_installation, name))
    for appname in sorted(APPS):
        print("creating shortcut:", launcher_name(appname))
        shortcut_path = make_shortcut(appname)
        add_to_start_menu(shortcut_path)
    print("done")


if __name__ == '__main__':
    if '--fix-shortcuts' in sys.argv:
        fix_shortcuts()
