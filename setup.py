import os
from setuptools import setup
from distutils import sysconfig

try:
    from setuptools_conda import dist_conda

    CMDCLASS = {"dist_conda": dist_conda}
except ImportError:
    CMDCLASS = {}

if "CONDA_BUILD" in os.environ:
    # Various packaging schemes are variously unhappy with how to include the .pth file
    # in site-packages. Conda is happy if we specify it with data_files and an absolute
    # path, whereas basically everything else (pip, setup.py install, bdist,
    # bdist_wheel) is happy if we specify it as package_data one level up.
    DATA_FILES = [(sysconfig.get_python_lib(), ["labscript-suite.pth"])]
    PACKAGE_DATA = {}
else:
    DATA_FILES = []
    PACKAGE_DATA = {"labscript_suite": [os.path.join("..", "labscript-suite.pth")]}

VERSION_SCHEME = {}
VERSION_SCHEME["version_scheme"] = os.environ.get(
    "SCM_VERSION_SCHEME", "guess-next-dev"
)
VERSION_SCHEME["local_scheme"] = os.environ.get("SCM_LOCAL_SCHEME", "node-and-date")

VERSION_SCHEME = {}
VERSION_SCHEME["version_scheme"] = os.environ.get(
    "SCM_VERSION_SCHEME", "release-branch-semver"
)
VERSION_SCHEME["local_scheme"] = os.environ.get("SCM_LOCAL_SCHEME", "node-and-date")

setup(
    use_scm_version=VERSION_SCHEME,
    cmdclass=CMDCLASS,
    data_files=DATA_FILES,
    package_data=PACKAGE_DATA,
)
