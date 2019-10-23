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