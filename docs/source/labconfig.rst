The *labconfig.ini* file
========================

The `labconfig.ini` file is a global configuration file for your **labscript-suite** installation.
It contains configurable settings that govern how the individual components of the suite operate.
The name of this file must be the host computer's system name.
So if my system's name was `heisenberg`, the labconfig file name would be `heisenberg.ini`.
This file should be located in the `labscript-suite` directory in the user space, in the `labconfig` subdirectory.

When :doc:`installing the **labscript-suite** for the first time <labscript-suite:installation/index>`, running the `labscript-profile-create` command will automatically generate the `labscript-suite` user space directory in the correct place and generate a `labconfig.ini` file for use on your system.
By editing the `ini` file named after your system, you can update the configuration settings of your **labscript-suite** installation.

The Default *labconfig.ini*
---------------------------

Below is a copy of the default lab configuration if you were to install the **labscript-suite** today.

.. note::

	When updates are made to the suite that add or change keys available in the labconfig, your local file will **NOT** be automatically updated to include them.
	Instead, if keys are missing from your local profile, default behavior will be assumed.
	To implement the added functionality, you will need to manually add/change the keys in your local labconfig.

.. include:: ../../labscript_profile/default_profile/labconfig/example.ini
	:code:
