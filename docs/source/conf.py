# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

from pkg_resources import get_distribution


# -- Project information -----------------------------------------------------

project = 'labscript-utils'
copyright = '2020, labscript suite'
author = 'labscript suite'

current_labscript_suite_repo = 'labscript-utils'


# The full version, including alpha/beta/rc tags
version = get_distribution(current_labscript_suite_repo).version
release = version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    # "sphinx.ext.linkcode",
    "sphinx.ext.viewcode",
    "sphinx_rtd_theme",
    "recommonmark",
]


#
# This code is for sphinx.ext.linkcode to link to GitHub source directly. 
# It doesn't link directly to specific lines though so is not as nice as 
# I would like right now. You also can't customise the "[source]" text
# in the sphinx docs (if you could, we could have both viewcode and linkcode extensions at the same time)
#
# # get github version/tag
# if '+' in version:
#     gh_source_version = version.split('+')[-1][1:]
# else:
#     gh_source_version = version

# # define function for resolving source link
# def linkcode_resolve(domain, info):
#     if domain != 'py':
#         return None
#     if not info['module']:
#         return None
#     filename = info['module'].replace('.', '/')
#     return "https://github.com/labscript-suite/{}/blob/{}/{}.py".format(current_labscript_suite_repo, gh_source_version, filename)

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# The suffix(es) of source filenames.
source_suffix = ['.rst', '.md']

# intersphinx allows us to link directly to other repos sphinxdocs.
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/reference/', None),
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable/', None),
    'qtutils': ('https://qtutils.readthedocs.io/en/stable/', None),
    'pyqtgraph': ('https://pyqtgraph.readthedocs.io/en/latest/', None), # change to stable once v0.11 is published
    'matplotlib': ('https://matplotlib.org/', None),
    'h5py': ('http://docs.h5py.org/en/stable/', None),
    'pydaqmx': ('https://pythonhosted.org/PyDAQmx/', None),
    'qt': ('', 'pyqt5-modified-objects.inv') # from https://github.com/MSLNZ/msl-qt/blob/master/docs/create_pyqt_objects.py under MIT License
    # TODO
    # desktop-app
    # spinapi/pynivision/etc
}

# list of all labscript suite components that have docs
labscript_suite_programs = [
    'labscript',
    'runmanager',
    'runviewer',
    'blacs',
    'lyse',
    'labscript-utils',
    'labscript-devices',
]
# remove this current repo from the list
if current_labscript_suite_repo in labscript_suite_programs:
    labscript_suite_programs.remove(current_labscript_suite_repo)

# whether to use stable or latest version
labscript_suite_doc_version = 'stable' # 'stable' or 'latest'

# add intersphinx references for each component
for ls_prog in labscript_suite_programs:
    intersphinx_mapping[ls_prog] = ('https://docs.labscript_suite.org/projects/{}/en/{}/'.format(ls_prog, labscript_suite_doc_version), None)

# add intersphinx reference for the metapackage
intersphinx_mapping['labscript-suite'] = ('https://docs.labscript_suite.org/en/{}/'.format(labscript_suite_doc_version), None)

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']