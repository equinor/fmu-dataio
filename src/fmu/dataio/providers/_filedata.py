"""Module for DataIO _FileData

Populate and verify stuff in the 'file' block in fmu (partial excpetion is checksum_md5
as this is convinient to populate later, on demand)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Final, Optional

from fmu.dataio._definitions import FmuContext
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import (
    compute_md5_using_temp_file,
)
from fmu.dataio.datastructure.meta import meta

from ._base import Provider

logger: Final = null_logger(__name__)

if TYPE_CHECKING:
    from fmu.dataio import ExportData, types

    from .objectdata._provider import ObjectDataProvider


class ShareFolder(str, Enum):
    PREPROCESSED = "share/preprocessed/"
    OBSERVATIONS = "share/observations/"
    RESULTS = "share/results/"


@dataclass
class FileDataProvider(Provider):
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
        """
        Construct the filestem string as a combinaton of various
        attributes; parent, name, tagname and time information.
        A '--' is used to separate the non-empty components, and a
        filestem containing all components will look like this:
        filestem = 'parent--name--tagname--time1_time0'
        """

        if not self.name:
            raise ValueError("The 'name' entry is missing for constructing a file name")
        if not self.objdata.time0 and self.objdata.time1:
            raise ValueError("Not legal: 'time0' is missing while 'time1' is present")

        filestem_order = (
            self.dataio.parent,
            self.name,
            self.dataio.tagname,
            self._get_timepart_for_filename(),
        )
        # join non-empty parts with '--'
        filestem = "--".join((p for p in filestem_order if p))
        filestem = self._sanitize_the_filestem(filestem)
        return filestem.lower()

    def _get_timepart_for_filename(self) -> str:
        if self.objdata.time0 is None:
            return ""
        t0 = self.objdata.time0.strftime("%Y%m%d")
        if not self.objdata.time1:
            return t0
        t1 = self.objdata.time1.strftime("%Y%m%d")
        return "_".join(
            (t1, t0) if not self.dataio.filename_timedata_reverse else (t0, t1)
        )

    @staticmethod
    def _sanitize_the_filestem(filestem: str) -> str:
        """
        Clean up the filestem; remove unwanted characters, treat
        norwegian special letters and remove multiple underscores
        """
        filestem = (
            filestem.replace(".", "_")
            .replace(" ", "_")
            .replace("æ", "ae")
            .replace("ø", "oe")
            .replace("å", "aa")
        )
        return re.sub(r"__+", "_", filestem)
