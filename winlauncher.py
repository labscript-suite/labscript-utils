import sys
import os
import importlib.util

def find_conda_env():
    """inspect whether sys.executable is within a conda environment and if it is, return
    the environment name and prefix. Otherwise return None, None"""
    prefix = os.path.dirname(sys.executable)
    if not os.path.isdir(os.path.join(prefix, 'conda-meta')):
        # Not a conda env
        return None, None
    if os.path.isdir(os.path.join(prefix, 'condabin')):
        # It's the base conda env:
        return 'base', prefix
    # Not the base env: its name is the directory basename:
    return os.path.basename(prefix), prefix


def activate_conda_env(name, prefix):
    """Modify environment variables so as to effectively activate the given conda env
    from the perspective of child processes. If the conda env appears to already be
    active, do nothing. Does not set environment variables, instead returns a copy that
    may be passed to subprocess.Popen as the env arg."""
    env = os.environ.copy()
    if env['CONDA_DEFAULT_ENV'] == name and env['CONDA_PREFIX'] == prefix:
        # Env is already active
        return
    env['CONDA_DEFAULT_ENV'] = name
    env['CONDA_PREFIX'] = prefix
    new_paths = os.path.pathsep.join(
        [
            prefix,
            os.path.join(prefix, "Library", "mingw-w64", "bin"),
            os.path.join(prefix, "Library", "usr", "bin"),
            os.path.join(prefix, "Library", "bin"),
            os.path.join(prefix, "Scripts"),
        ]
    )
    existing_paths = env.get('PATH', '')
    # Avoid a leading path separator in the PATH variable:
    if existing_paths:
        env['PATH'] = new_paths + os.path.pathsep + existing_paths
    else:
        env['PATH'] = new_paths

    return env

def run(*args):
    """Runs a child Python subprocess, passing it the given argument list. If
    sys.executable is pythonw.exe, then the child process will be run with the
    corresponding python.exe with a hidden console window. Otherwise it will be run with
    sys.executable. If sys.executable is within a conda environment, then the child
    process's environment will be modified to have the effect of activating the
    environment."""
    import subprocess

    CREATE_NO_WINDOW = 1 << 27 # TODO: can use subprocess.CREATE_NO_WINDOW in py3.7+

    popen_kwargs = {}

    envname, prefix = find_conda_env()
    if envname is not None:
        env = activate_conda_env(envname, prefix)
        popen_kwargs['env'] = env

    python = sys.executable
    if os.path.basename(python).lower() == 'pythonw.exe':
        python = os.path.join(os.path.dirname(python), 'python.exe')
        popen_kwargs['creationflags'] = CREATE_NO_WINDOW

    return subprocess.call([python] + list(args), **popen_kwargs)

def main():
    import argparse

    parser = argparse.ArgumentParser( description="""A launcher for running Python
        scripts/apps on Windows, potentially in conda environments. Run a child Python
        subprocess, passing it the given argument list. If the Python interpreter used
        to invoke this script is Python.exe, then it will be used to invoke the
        subprocess, but if it is Pythonw.exe, the child will instead be run with the
        corresponding Python.exe with a hidden console window. This prevents a number of
        issues with using Pythonw.exe, but without having to show a console window. If
        the Python interpreter is within a conda environment, then the child process's
        environment will be modified to have the effect of activating the environment.
        If this script is invoked as an entry_point of another package, it will inspect
        sys.argv[0] to find the name of the entry_point script. The basename of the
        script, (excluding a '.exe' suffix (or 'w.exe' if a gui_script) will be
        interpreted as a module name, and that module - or its __main__.py if it's a
        package - will be run. Note that a package's __init__.py will not be run first
        as is the case with `python -m package_name`. This is a performance optimisation
        to allow the program to say, display a splash screen as soon as possible during
        startup. If it is necessary for __init__.py to run, the application's
        __main__.py should import it. In this way, an application may define gui_scripts
        and console_scripts entry_points named <modulename> and <modulenamew> that point
        to winlauncher:main to create launcher scripts."""
    )

    parser.add_argument(
        'args',
        metavar='args',
        type=str,
        nargs=argparse.REMAINDER,
        help="""Arguments to pass to the child Python interpreter. In the simplest case
            this simply the path to a script to be run, but may be '-m module_name' or
            any other arguments accepted by the Python' command""",
    )
    args = parser.parse_args().args
    if os.path.abspath(__file__) != os.path.abspath(sys.argv[0]):
        # we're being run as an entry_point for an application. Insert that
        # application's main script at the start of the argument list.
        module_name = os.path.basename(sys.argv[0]).lower()
        if os.path.basename(sys.executable).lower() == 'pythonw.exe':
            module_name = module_name.rsplit('w', 1)[0]
        # Find the import path of the module:
        spec = importlib.util.find_spec(module_name)
        if spec is None or spec.origin is None:
            raise ModuleNotFoundError(module_name)
        if spec.parent:
            # A package:
            script = os.path.join(os.path.dirname(spec.origin), '__main__.py')
        else:
            # A single-file module:
            script = spec.origin
        # Insert at the start of the argument list:
        args = [script] + args

    sys.exit(run(*args))

if __name__ == '__main__':
    main()
