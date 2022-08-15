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

        self.forcefolder = self.dataio.forcefolder
        self.forcefolder_is_absolute = False
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

        try:
            str(abspath).encode("ascii")
        except UnicodeEncodeError:
            print(f"!! Path has non-ascii elements which is not supported: {abspath}")
            raise

        if self.forcefolder_is_absolute:
            # may become meaningsless as forcefolder can be something else, but will try
            try:
                relpath = path.relative_to(self.rootpath)
            except ValueError as verr:
                if "does not start with" in str(verr):
                    relpath = abspath
                    logger.info(
                        "Relative path equal to absolute path due to forcefolder "
                        "with absolute path deviating for rootpath %s",
                        self.rootpath,
                    )
                else:
                    raise
        else:
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

        # treat norwegian special letters
        stem = stem.replace("æ", "ae")
        stem = stem.replace("ø", "oe")
        stem = stem.replace("å", "aa")

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
            outroot = outroot / "observations"
        else:
            outroot = outroot / "results"

        dest = outroot / self.efolder  # e.g. "maps"

        if self.dataio.forcefolder and self.dataio.forcefolder.startswith("/"):
            if not self.dataio.allow_forcefolder_absolute:
                raise ValueError(
                    "The forcefolder includes an absolute path, i.e. "
                    "starting with '/'. This is strongly discouraged and is only "
                    "allowed if classvariable allow_forcefolder_absolute is set to True"
                )
            else:
                warn("Using absolute paths in forcefolder is not recommended!")

            # absolute if starts with "/", otherwise relative to outroot
            dest = Path(self.dataio.forcefolder)
            dest = dest.absolute()
            self.forcefolder_is_absolute = True

        if self.dataio.subfolder:
            dest = dest / self.dataio.subfolder

        if self.dataio.createfolder:
            dest.mkdir(parents=True, exist_ok=True)

        # check that destination actually exists if verify_folder is True
        if self.dataio.verifyfolder and not dest.exists():
            raise IOError(f"Folder {str(dest)} is not present.")

        return dest
