import sys
import os
from os.path import join, pathsep, dirname
import subprocess
import argparse

parser = argparse.ArgumentParser(
    description="""A launcher for running Python scripts/apps on Windows, potentially in
        conda environments. This script can be run with either pythonw.exe or
        python.exe, but in the former case it will launch the app using python.exe with
        a hidden console window. This prevents a number of issues with using
        pythonw.exe, but without having to show a console window. If using a conda
        environment, then any python interpreter may be used to invoke this script, and
        the 'python' command from within the environment will be used to run the target
        python script. If not using a conda environment, the python interpreter used to
        invoke this script (or the corresponding python.exe if pythonw.exe was used)
        will be used to invoke the target script."""
)

parser.add_argument(
    '-n',
    '--name',
    type=str,
    help="""Name of the conda environment to be used, if any.""",
)

parser.add_argument(
    '-p',
    '--prefix',
    type=str,
    help="""Prefix of the conda environment, if any.""",
)

parser.add_argument(
    'script',
    type=str,
    help="""Python script to run. Note: if you wish to do something other than run a
        script by its filepath, you may pass '--' in place of this argument, then all
        subsequent arguments will be passed to the Python interpreter verbatim. This can
        be used for example to run a module as __main__ using the '-m' flag, i.e.
        winshell.py <other arguments> -- -m <module>""",
)

parser.add_argument(
    'args',
    metavar='args',
    type=str,
    nargs=argparse.REMAINDER,
    help='Arguments to pass to target Python script or interpreter',
)

CREATE_NO_WINDOW = 1 << 27
args = parser.parse_args()
prefix = args.prefix
popen_kwargs = {}

if prefix is not None:
    # Environment manipulation copied from cwp.py from the menuinst project. We're not
    # using that script because we do not want to do an os.chdir into the documents
    # folder as it does, and we also need to set the CONDA_DEFAULT_ENV environment
    # variable since our programs need to know the name of the environment they're in,
    # and not just the prefix. Using our own launcher also allows us to swap out
    # pythonw.exe for python.exe without creating a visible console, which otherwise
    # requires yet another layer of subprocesses to achieve.
    new_paths = pathsep.join([prefix,
                         join(prefix, "Library", "mingw-w64", "bin"),
                         join(prefix, "Library", "usr", "bin"),
                         join(prefix, "Library", "bin"),
                         join(prefix, "Scripts")])
    env = os.environ.copy()
    env['PATH'] = new_paths + pathsep + env['PATH']
    env['CONDA_PREFIX'] = prefix
    env['CONDA_DEFAULT_ENV'] = args.name
    python = 'python'
    popen_kwargs['env'] = env
    popen_kwargs['creationflags'] = CREATE_NO_WINDOW
elif 'pythonw.exe' in sys.executable.lower():
    python = join(dirname(sys.executable), 'python.exe')
    popen_kwargs['creationflags'] = CREATE_NO_WINDOW
else:
    python = sys.executable

sys.exit(subprocess.call([python, args.script] + args.args, **popen_kwargs))
