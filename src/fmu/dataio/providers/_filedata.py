"""Module for DataIO _FileData

Populate and verify stuff in the 'file' block in fmu (partial excpetion is checksum_md5
as this is convinient to populate later, on demand)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Final, Optional
from warnings import warn

from fmu.dataio._definitions import FmuContext
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import (
    compute_md5_using_temp_file,
)
from fmu.dataio.datastructure.meta import meta

logger: Final = null_logger(__name__)

if TYPE_CHECKING:
    from fmu.dataio import ExportData, types

    from .objectdata._provider import ObjectDataProvider


class ShareFolder(str, Enum):
    PREPROCESSED = "share/preprocessed"
    OBSERVATIONS = "share/observations"
    RESULTS = "share/results"


@dataclass
class FileDataProvider:
    """Class for providing metadata for the 'files' block in fmu-dataio.

    Example::

        file:
            relative_path: ... (relative to case)
            absolute_path: ...
    """

    # input
    dataio: ExportData
    objdata: ObjectDataProvider
    runpath: Path | None = None
    obj: Optional[types.Inferrable] = None
    compute_md5: bool = False

    @property
    def name(self) -> str:
        return self.dataio.name or self.objdata.name

    def get_metadata(self) -> meta.File:
        if self.dataio.forcefolder and (
            forcefolder := self._get_forcefolder_if_absolute()
        ):
            absolute_path = self._add_filename_to_path(forcefolder)
            relative_path = self._try_to_resolve_forcefolder(absolute_path)

        else:
            rootpath = (
                self.runpath
                if self.runpath and self.dataio.fmu_context == FmuContext.REALIZATION
                else self.dataio._rootpath
            )
            share_folders = self._get_share_folders()
            export_folder = rootpath / share_folders

            absolute_path = self._add_filename_to_path(export_folder)
            relative_path = absolute_path.relative_to(self.dataio._rootpath)

        logger.info("Returning metadata pydantic model meta.File")
        return meta.File(
            absolute_path=absolute_path.resolve(),
            relative_path=relative_path,
            checksum_md5=self._compute_md5() if self.compute_md5 else None,
        )

    def _get_share_folders(self) -> Path:
        """Get the export share folders."""
        if self.dataio.fmu_context == FmuContext.PREPROCESSED:
            sharefolder = Path(ShareFolder.PREPROCESSED.value)
        elif self.dataio.is_observation:
            sharefolder = Path(ShareFolder.OBSERVATIONS.value)
        else:
            sharefolder = Path(ShareFolder.RESULTS.value)

        sharefolder = sharefolder / self.objdata.efolder
        if self.dataio.subfolder:
            sharefolder = sharefolder / self.dataio.subfolder

        logger.info("Export share folders are %s", sharefolder)
        return sharefolder

    def _compute_md5(self) -> str:
        """Compute an MD5 sum using a temporary file."""
        if self.obj is None:
            raise ValueError("Can't compute MD5 sum without an object.")
        return compute_md5_using_temp_file(
            self.obj, self.objdata.extension, self.dataio._usefmtflag
        )

    def _add_filename_to_path(self, path: Path) -> Path:
        stem = self._get_filestem()
        return (path / stem).with_suffix(path.suffix + self.objdata.extension)

    def _get_filestem(self) -> str:
        """Construct the file"""

        if not self.name:
            raise ValueError("The 'name' entry is missing for constructing a file name")
        if not self.objdata.time0 and self.objdata.time1:
            raise ValueError("Not legal: 'time0' is missing while 'time1' is present")

        stem = self.name.lower()
        if self.dataio.tagname:
            stem += "--" + self.dataio.tagname.lower()
        if self.dataio.parent:
            stem = self.dataio.parent.lower() + "--" + stem

        if self.objdata.time0 and not self.objdata.time1:
            stem += "--" + (str(self.objdata.time0)[0:10]).replace("-", "")

        elif self.objdata.time0 and self.objdata.time1:
            monitor = (str(self.objdata.time1)[0:10]).replace("-", "")
            base = (str(self.objdata.time0)[0:10]).replace("-", "")
            if monitor == base:
                warn(
                    "The monitor date and base date are equal", UserWarning
                )  # TODO: consider add clocktimes in such cases?
            if self.dataio.filename_timedata_reverse:  # class variable
                stem += "--" + base + "_" + monitor
            else:
                stem += "--" + monitor + "_" + base

        # remove unwanted characters
        stem = stem.replace(".", "_").replace(" ", "_")

        # avoid multiple double underscores
        while "__" in stem:
            stem = stem.replace("__", "_")

        # treat norwegian special letters
        # BUG(?): What about germen letter like "Ü"?
        stem = stem.replace("æ", "ae")
        stem = stem.replace("ø", "oe")
        stem = stem.replace("å", "aa")
        return stem.lower()

    def _get_forcefolder_if_absolute(self) -> Path | None:
        if self.dataio.forcefolder.startswith("/"):
            if not self.dataio.allow_forcefolder_absolute:
                raise ValueError(
                    "Cannot use absolute path to 'forcefolder', i.e. "
                    "starting with '/'. This is strongly discouraged and is only "
                    "allowed if classvariable allow_forcefolder_absolute is set to True"
                )
            warn("Using absolute paths in forcefolder is not recommended!")
            return Path(self.dataio.forcefolder).absolute()
        return None

    def _try_to_resolve_forcefolder(self, forcefolder: Path) -> Path:
        try:
            return forcefolder.relative_to(self.dataio._rootpath)
        except ValueError as verr:
            if ("does not start with" in str(verr)) or (
                "not in the subpath of" in str(verr)
            ):
                logger.info(
                    "Relative path equal to absolute path due to forcefolder "
                    "with absolute path deviating for rootpath %s",
                    self.dataio._rootpath,
                )
                return forcefolder.resolve()
            raise
