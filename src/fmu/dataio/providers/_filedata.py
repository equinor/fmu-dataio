"""Module for DataIO _FileData

Populate and verify stuff in the 'file' block in fmu (partial excpetion is checksum_md5
as this is convinient to populate later, on demand)
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Final

from fmu.dataio._definitions import ShareFolder
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import compute_md5_and_size_from_objdata
from fmu.datamodels.fmu_results import fields
from fmu.datamodels.fmu_results.enums import FMUContext

from ._base import Provider

logger: Final = null_logger(__name__)

if TYPE_CHECKING:
    from fmu.dataio import ExportData
    from fmu.dataio._runcontext import RunContext

    from .objectdata._provider import ObjectDataProvider


class SharePathConstructor:
    """Class for providing the export share location for an object"""

    def __init__(self, dataio: ExportData, objdata: ObjectDataProvider):
        self.dataio = dataio
        self.objdata = objdata

        self.name = self.dataio.name or self.objdata.name
        self.parent = self._get_parent()

    def get_share_path(self) -> Path:
        """Get the full share location including the filename."""
        return self._get_share_folders() / self._get_filename()

    def _get_share_root(self) -> Path:
        """Get the main share root location as a path e.g. share/results."""
        if self.dataio.preprocessed:
            return Path(ShareFolder.PREPROCESSED.value)
        if self.dataio.is_observation:
            return Path(ShareFolder.OBSERVATIONS.value)
        return Path(ShareFolder.RESULTS.value)

    def _get_share_folders(self) -> Path:
        """Get the full share folders as a path."""
        share_root = self._get_share_root()
        if self.dataio.subfolder:
            return share_root / self.objdata.efolder / self.dataio.subfolder
        return share_root / self.objdata.efolder

    def _get_filename(self) -> Path:
        """Get the filename for the file."""
        stem = self._get_filestem()
        return Path(stem).with_suffix(self.objdata.extension)

    def _get_parent(self) -> str:
        """Action when both parent key and geometry key are given (GridProperty)."""
        geom = self.objdata.get_geometry()

        if geom and self.dataio.parent:
            warnings.warn(
                "Both 'geometry' and 'parent' keys are given, but 'parent' will here "
                "be ignored as they are in conflict. Instead, the geometry.name will "
                "be applied as 'parent' string info as part of the file name.",
                UserWarning,
            )

        return geom.name if geom else self.dataio.parent

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
            self.parent,
            self.name,
            self.dataio.tagname,
            self._get_timepart_for_filename(),
        )
        # join non-empty parts with '--'
        filestem = "--".join(p for p in filestem_order if p)
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


class FileDataProvider(Provider):
    """Class for providing metadata for the 'files' block in fmu-dataio.

    Example::

        file:
            relative_path: ... (relative to case)
            absolute_path: ...
    """

    def __init__(
        self,
        runcontext: RunContext,
        objdata: ObjectDataProvider,
    ):
        self.objdata = objdata
        self.runcontext = runcontext

    def get_metadata(self) -> fields.File:
        casepath = self.runcontext.casepath
        exportroot = self.runcontext.exportroot
        share_path = self.objdata.share_path

        absolute_path = exportroot / share_path
        relative_path = absolute_path.relative_to(casepath or exportroot)

        checksum, size = compute_md5_and_size_from_objdata(self.objdata)

        logger.info("Returning metadata pydantic model fields.File")
        return fields.File(
            absolute_path=absolute_path.resolve(),
            relative_path=relative_path,
            runpath_relative_path=(
                share_path
                if self.runcontext.fmu_context == FMUContext.realization
                else None
            ),
            checksum_md5=checksum,
            size_bytes=size,
        )
