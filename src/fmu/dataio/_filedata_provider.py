"""Module for DataIO _FileData

Populate and verify stuff in the 'file' block in fmu (partial excpetion is checksum_md5
as this is convinient to populate later, on demand)
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from warnings import warn

logger = logging.getLogger(__name__)


@dataclass
class _FileDataProvider:
    """Class for providing metadata for the 'files' block in fmu-dataio.

    Example::

        file:
            relative_path: ... (relative to case)
            absolute_path: ...
            checksum_md5: ...  Will be done in anothr routine!
    """

    # input
    dataio: Any
    objdata: Any
    rootpath: Path = field(default_factory=Path)
    itername: str = ""
    realname: str = ""
    verbosity: str = "CRITICAL"

    # storing results in these variables
    relative_path: Optional[str] = field(default="", init=False)
    absolute_path: Optional[str] = field(default="", init=False)
    checksum_md5: Optional[str] = field(default="", init=False)

    def __post_init__(self):
        logger.setLevel(level=self.verbosity)

        if self.dataio.name:
            self.name = self.dataio.name
        else:
            self.name = self.objdata.name

        self.tagname = self.dataio.tagname
        self.time0 = self.objdata.time0
        self.time1 = self.objdata.time1

        self.parentname = self.dataio.parent
        self.extension = self.objdata.extension
        self.efolder = self.objdata.efolder

        self.create_folder = self.dataio.createfolder
        self.verify_folder = self.dataio.verifyfolder
        self.forcefolder = self.dataio.forcefolder
        self.subfolder = self.dataio.subfolder

        self.fmu_context = self.dataio._usecontext  # may be None!

        logger.info("Initialize %s", __class__)

    def derive_filedata(self):
        stem = self._get_filestem()
        relpath = self._get_path()

        path = Path(relpath) / stem.lower()
        path = path.with_suffix(path.suffix + self.extension)

        # resolve() will fix ".." e.g. change '/some/path/../other' to '/some/other'
        abspath = path.resolve()

        relpath = path.relative_to(self.rootpath)
        self.relative_path = str(relpath)
        self.absolute_path = str(abspath)
        logger.info("Derived filedata")

    def _get_filestem(self):
        """Construct the file"""

        if not self.name:
            raise ValueError("The 'name' entry is missing for constructing a file name")
        if not self.time0 and self.time1:
            raise ValueError("Not legal: 'time0' is missing while 'time1' is present")

        stem = self.name.lower()
        if self.tagname:
            stem += "--" + self.tagname.lower()
        if self.parentname:
            stem = self.parentname.lower() + "--" + stem

        if self.time0 and not self.time1:
            stem += "--" + (str(self.time0)[0:10]).replace("-", "")

        elif self.time0 and self.time1:
            monitor = (str(self.time0)[0:10]).replace("-", "")
            base = (str(self.time1)[0:10]).replace("-", "")
            if monitor == base:
                warn(
                    "The monitor date and base date are equal", UserWarning
                )  # TODO: consider add clocktimes in such cases?
            stem += "--" + monitor + "_" + base

        stem = stem.replace(".", "_").replace(" ", "_")
        return stem

    def _get_path(self):
        """Construct and get the folder path and verify."""

        outroot = self.rootpath

        logger.info("FMU context is %s", self.fmu_context)
        if self.fmu_context == "realization":
            if self.realname:
                outroot = outroot / self.realname

            if self.itername:
                outroot = outroot / self.itername

        if self.fmu_context == "case_symlink_realization":
            raise NotImplementedError("Symlinking not there yet...")

        outroot = outroot / "share"

        if self.dataio.is_observation:
            outroot = outroot / "observation"
        else:
            outroot = outroot / "results"

        dest = outroot / self.efolder  # e.g. "maps"

        if self.forcefolder:
            dest = Path(self.forcefolder)
            dest = dest.absolute()

        if self.subfolder:
            dest = dest / self.subfolder

        if self.create_folder:
            dest.mkdir(parents=True, exist_ok=True)

        # check that destination actually exists if verify_folder is True
        if self.verify_folder and not dest.exists():
            raise IOError(f"Folder {str(dest)} is not present.")

        return dest
