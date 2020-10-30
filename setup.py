import os
from setuptools import setup
from setuptools.command.develop import develop
from distutils import log


class develop_command(develop):
    """Custom develop command which installs the .pth file to site-packages for editable
    installs."""
    def run(self):
        path = os.path.join(self.install_dir, 'labscript-suite.pth')
        super().run()
        if not self.uninstall:
            log.info(f'Copying labscript-suite.pth to {path}')
            if not self.dry_run:
                self.copy_file('labscript-suite.pth', path)


VERSION_SCHEME = {
    "version_scheme": os.getenv("SCM_VERSION_SCHEME", "release-branch-semver"),
    "local_scheme": os.getenv("SCM_LOCAL_SCHEME", "node-and-date"),
}

setup(use_scm_version=VERSION_SCHEME, cmdclass={'develop': develop_command})
