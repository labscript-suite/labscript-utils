# USAGE NOTES
#
# Make a PyPI release tarball with:
#
#     python setup.py sdist
#
# Upload to test PyPI with:
#
#     twine upload --repository-url https://test.pypi.org/legacy/ dist/*
#
# Install from test PyPI with:
#
#     pip install --index-url https://test.pypi.org/simple/ labscript_utils
#
# Upload to real PyPI with:
#
#     twine upload dist/*
#
# Build conda packages for all platforms (in a conda environment with setuptools_conda
# installed) with:
#
#     python setup.py dist_conda
#
# Upoad to your own account (for testing) on anaconda cloud (in a conda environment with
# anaconda-client installed) with:
#
#     anaconda upload --skip-existing conda_packages/*/*
#
# (Trickier on Windows, as it won't expand the wildcards)
#
# Upoad to the labscript-suite organisation's channel on anaconda cloud (in a
# conda environment with anaconda-client installed) with:
#
#     anaconda  upload -u labscript-suite --skip-existing conda_packages/*/*
#
# If you need to rebuild the same version of the package for conda due to a packaging
# issue, you must increment CONDA_BUILD_NUMBER in order to create a unique version on
# anaconda cloud. When subsequently releasing a new version of the package,
# CONDA_BUILD_NUMBER should be reset to zero.

import os
from setuptools import setup
from distutils import sysconfig
from runpy import run_path

try:
    from setuptools_conda import dist_conda
except ImportError:
    dist_conda = None

SETUP_REQUIRES = ['setuptools', 'setuptools_scm']

INSTALL_REQUIRES = [
    "importlib_metadata >=1.0;      python_version < '3.8'",
    "pywin32;                       sys_platform == 'win32'",
    "pyqtgraph",
    "numpy >=1.15",
    "scipy",
    "h5py >=2.9",
    "qtutils >=2.2.3",
    "zprocess >=2.18.0",
    "pyqtgraph",
]

if 'CONDA_BUILD' in os.environ:
    # Various packaging schemes are variously unhappy with how to include the .pth file
    # in site-packages. Conda is happy if we specify it with data_files and an absolute
    # path, whereas basically everything else (pip, setup.py install, bdist,
    # bdist_wheel) is happy if we specify it as package_data one level up.
    data_files = [(sysconfig.get_python_lib(), ['labscript-suite.pth'])]
    package_data = {}
else:
    data_files = []
    package_data = {'labscript_suite': [os.path.join('..', 'labscript-suite.pth')]}

setup(
    name='labscript_utils',
    version=run_path(os.path.join('labscript_utils', '__version__.py'))['__version__'],
    description="Shared utilities for the labscript suite",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='The labscript suite community',
    author_email='labscriptsuite@googlegroups.com ',
    url='http://labscriptsuite.org',
    license="BSD",
    packages=["labscript_utils", "labscript_profile"],
    zip_safe=False,
    setup_requires=SETUP_REQUIRES,
    include_package_data=True,
    package_data=package_data,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5",
    install_requires=INSTALL_REQUIRES if 'CONDA_BUILD' not in os.environ else [],
    cmdclass={'dist_conda': dist_conda} if dist_conda is not None else {},
    data_files=data_files,
    entry_points={
        'console_scripts': [
            'labscript-profile-create = labscript_profile.create:create_profile',
        ],
    },
    command_options={
        'dist_conda': {
            'pythons': (__file__, ['3.6', '3.7', '3.8']),
            'platforms': (__file__, ['linux-64', 'win-32', 'win-64', 'osx-64']),
            'force_conversion': (__file__, True),
        },
    },
)
