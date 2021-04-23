"""Setup helpers for setup.py in fmu.dataio package."""
import os
from os.path import exists
from shutil import rmtree
import fnmatch

from distutils.command.clean import clean as _clean


def parse_requirements(filename):
    """Load requirements from a pip requirements file."""
    try:
        lineiter = (line.strip() for line in open(filename))
        return [line for line in lineiter if line and not line.startswith("#")]
    except OSError:
        return []


# ======================================================================================
# Overriding and extending setup commands; here "clean"
# ======================================================================================


class CleanUp(_clean):
    """Custom implementation of ``clean`` command.

    Overriding clean in order to get rid if "dist" folder and etc, see setup.py.
    """

    CLEANFOLDERS = (
        "__pycache__",
        "pip-wheel-metadata",
        ".eggs",
        "dist",
        "build",
        "sdist",
        "wheel",
        ".pytest_cache",
        "docs/apiref",
        "docs/_build",
    )

    CLEANFOLDERSRECURSIVE = ["__pycache__", "_tmp_*", "*.egg-info"]
    CLEANFILESRECURSIVE = ["*.pyc", "*.pyo"]

    @staticmethod
    def ffind(pattern, path):
        """Find files."""
        result = []
        for root, _, files in os.walk(path):
            for name in files:
                if fnmatch.fnmatch(name, pattern):
                    result.append(os.path.join(root, name))
        return result

    @staticmethod
    def dfind(pattern, path):
        """Find folders."""
        result = []
        for root, dirs, _ in os.walk(path):
            for name in dirs:
                if fnmatch.fnmatch(name, pattern):
                    result.append(os.path.join(root, name))
        return result

    def run(self):
        """Execute run.

        After calling the super class implementation, this function removes
        the directories specific to scikit-build ++.
        """
        super(CleanUp, self).run()

        for dir_ in CleanUp.CLEANFOLDERS:
            if exists(dir_):
                print("Removing: {}".format(dir_))
            if not self.dry_run and exists(dir_):
                rmtree(dir_)

        for dir_ in CleanUp.CLEANFOLDERSRECURSIVE:
            for pdir in self.dfind(dir_, "."):
                print("Remove folder {}".format(pdir))
                rmtree(pdir)

        for fil_ in CleanUp.CLEANFILESRECURSIVE:
            for pfil in self.ffind(fil_, "."):
                print("Remove file {}".format(pfil))
                os.unlink(pfil)
