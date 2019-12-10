## [2.15.0] - 2019-12-04

This release includes one bugfix, one enhancement, one update for compatibility with a
new Python version, and two changes that facilitate the move of labscript suite
components to regular Python packages installable with conda or pip, discussed
[here](https://bitbucket.org/labscript_suite/installer/issues/31/)

- `labscript_utils.versions` Python 3.8 compatibility. Fixes an exception raised on
  Python 3.8 due the the `importlib_metadata` package becoming part of the standard
  library. Contributed by Chris Billington. 
  ([PR #94](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/94))

- `labscript_utils.filewatcher.FileWatcher` can now detect whether files have changed on
  disk by checking a hash of their contents, and not just their modified times. This
  means that a file reverting to its previous state can be detected, such that the
  "connection table needs to be recompiled" message in the next release of BLACS will be
  hidden if the connection table is restored to its previous state. Contributed by
  Russell Anderson.
  ([PR #61](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/61))

- The `labscript_utils.setup_logging` module now creates log files for applications in
  `<labscript_suite_profile>/logs` instead of the installation directory of the
  application itself. Contributed by Chris Billington.
  ([PR #95](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/95))

- `labscript_utils.labscript_suite_install_dir` has been renamed to
  `labscript_suite_profile`, with the former name kept as an alias. This reflects the
  fact that in the future, labscript suite applications may be installed as regular
  Python packages, and not in the directory containing logs, configuration and user
  libraries, which will now be referred to at the "labscript suite profile" directory
  instead of the "installation" directory. Also to help with that change, the
  `labscript_utils.winshell` module now uses the import path of each application instead
  of assuming it is in the profile directory for the purposes of creating windows
  shortcuts. Applications shortcuts now start applications with the `userlib` directory
  as the working directory instead of the application's installation directory.
  Contributed by Chris Billington.
  ([PR #96](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/96))

- Bugfix for using automatic metric prefixes with nonlinear unit conversion functions,
  these previously did the unit conversion incorrectly. Contributed by Peter Elgee and
  Chris Billington.
  ([PR #87](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/87))


## [2.14.1] - 2019-10-22

This release includes one bugfix, two minor improvements and one update for
compatibility with a newer version of a library.

- Bugfix for check_version to produce a sensible error message when `importlib_metadata`
  is not new enough. Contributed by Chris Billington.
  ([PR #88](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/88))

- Improved error message (with traceback of both imports) if `h5py` imported prior to
  `labscript_utils.h5_lock`. Contributed by Chris Billington
  ([PR #90](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/90))

- Improve help text of `labscript_utils.winlauncher` to show how to run modules as well
  as scripts. Contributed by Chris Billington.
  ([PR #91](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/91))

- Compatibility with `importlib_metadata` >= 0.21. Contributed by Chris Billington
  ([PR #92](https://bitbucket.org/labscript_suite/labscript_utils/pull-requests/88))