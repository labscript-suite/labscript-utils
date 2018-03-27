from __future__ import division, unicode_literals, print_function, absolute_import

import os
import sys
import subprocess

this_folder = os.path.realpath(os.path.dirname(__file__))
Win7AppId = os.path.join(this_folder, 'Win7AppId1.1.exe')

for path in sys.path:
    if os.path.exists(os.path.join(path, '.is_labscript_suite_install_dir')):
        labscript_installation = os.path.abspath(path)
        break
else:
    labscript_installation = '<not_installed>'

# Including the install directory in the below AppId strings ensures they are unique
# to the install. If they are not, then installing to one directory, uninstalling,
# and reinstalling to another makes the Windows AppId API behave unpredictably.
# Shortcuts don't work, and icons are broken.
# This if of particular importance when developing on the same machine as you are
# deploying to.
appids = {'runmanager': 'Monashbec.Labscript.Runmanager.%s'%labscript_installation,
         'runviewer': 'Monashbec.Labscript.Runviewer.%s'%labscript_installation,
         'blacs': 'Monashbec.Labscript.Blacs.%s'%labscript_installation,
         'lyse': 'Monashbec.Labscript.Lyse.%s'%labscript_installation}

app_descriptions = {'runmanager': 'runmanager - the labscript suite',
                   'runviewer': 'runviewer - the labscript suite',
                   'blacs': 'blacs - the labscript suite',
                   'lyse': 'lyse - the labscript suite'}

def make_shortcut(path, target, arguments, working_directory, icon_path, description, appid):
    import sys, os
    from win32com.client import Dispatch
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortcut(path)
    shortcut.TargetPath = target
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = working_directory
    shortcut.IconLocation = icon_path
    shortcut.Description = description
    shortcut.save()
    # The normal windows API calls don't seem to be able to set the appid of the shortcut.
    # The required API calls are either absent or not wrapped by pywin32. So we use this
    # command line utility that does it in C++:
    child = subprocess.Popen([Win7AppId, path, appid],
                             stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    stdout, stderr = child.communicate()
    if child.returncode != 0:
        raise OSError('Failed to set UserModelAppId of shortcut.\n' + stdout + stderr)

def set_appusermodel(window_id, appid, icon_path, relaunch_command, relaunch_display_name):
    from win32com.propsys import propsys, pscon
    store = propsys.SHGetPropertyStoreForWindow(window_id, propsys.IID_IPropertyStore)
    id = store.GetValue(pscon.PKEY_AppUserModel_ID)
    store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(appid))
    store.SetValue(pscon.PKEY_AppUserModel_RelaunchCommand, propsys.PROPVARIANTType(relaunch_command))
    store.SetValue(pscon.PKEY_AppUserModel_RelaunchDisplayNameResource, propsys.PROPVARIANTType(relaunch_display_name))
    store.SetValue(pscon.PKEY_AppUserModel_RelaunchIconResource, propsys.PROPVARIANTType(icon_path))

def add_to_start_menu(shortcut):
    from win32com.client import Dispatch
    import shutil
    objShell = Dispatch("WScript.Shell")
    start_menu_programs = objShell.SpecialFolders("Programs")
    shutil.copy(shortcut, start_menu_programs)

def remove_from_start_menu(name):
    """Removes given .lnk file from the start menu.
    If entry not present, does nothing."""
    from win32com.client import Dispatch
    import shutil
    name = os.path.basename(name)
    objShell = Dispatch("WScript.Shell")
    start_menu_programs = objShell.SpecialFolders("Programs")
    if name in os.listdir(start_menu_programs):
        os.unlink(os.path.join(start_menu_programs, name))

