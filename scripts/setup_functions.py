"""Setup helpers for setup.py in fmu.dataio package."""
import fnmatch
import os
from distutils.command.clean import clean as _clean
from os.path import exists
from shutil import rmtree
from urllib.parse import urlparse

from pip._internal.req import parse_requirements as parse


def _format_requirement(req):
    if req.is_editable:
        # parse out egg=... fragment from VCS URL
        parsed = urlparse(req.requirement)
        egg_name = parsed.fragment.partition("egg=")[-1]
        without_fragment = parsed._replace(fragment="").geturl()
        return f"{egg_name} @ {without_fragment}"
    return req.requirement


def parse_requirements(fname):
    """Turn requirements.txt into a list"""
    reqs = parse(fname, session="test")
    return [_format_requirement(ir) for ir in reqs]


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
                print(f"Removing: {dir_}")
            if not self.dry_run and exists(dir_):
                rmtree(dir_)

        for dir_ in CleanUp.CLEANFOLDERSRECURSIVE:
            for pdir in self.dfind(dir_, "."):
                print(f"Remove folder {pdir}")
                rmtree(pdir)

        for fil_ in CleanUp.CLEANFILESRECURSIVE:
            for pfil in self.ffind(fil_, "."):
                print(f"Remove file {pfil}")
                os.unlink(pfil)
