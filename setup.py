import os
from setuptools import setup
from setuptools.command.develop import develop
import logging

# Setupstools >=64
try:
    from setuptools.command.editable_wheel import editable_wheel
except ImportError:
    editable_wheel_command = None
else:
    from wheel.wheelfile import WheelFile

    class editable_wheel_command(editable_wheel):
        """Custom editable_wheel command which installs the .pth file to the
        wheel file for editable installs."""
        def _create_wheel_file(self, bdist_wheel):
            wheel_path = super()._create_wheel_file(bdist_wheel)
            with WheelFile(wheel_path, 'a') as wheel:
                wheel.write("labscript-suite.pth")
            return wheel_path


# Setuptools <= 63:
class develop_command(develop):
    """Custom develop command which installs the .pth file to site-packages for editable
    installs."""
    def run(self):
        path = os.path.join(self.install_dir, 'labscript-suite.pth')
        super().run()
        if not self.uninstall:
            logging.info(f'Copying labscript-suite.pth to {path}')
            if not self.dry_run:
                self.copy_file('labscript-suite.pth', path)

setup(
    cmdclass={
        'develop': develop_command,
        'editable_wheel': editable_wheel_command,
    },
)