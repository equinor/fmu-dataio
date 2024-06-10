from __future__ import annotations

import shutil
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import yaml
from pydantic import ValidationError

from ._definitions import FmuContext
from ._logging import null_logger
from ._metadata import generate_meta_tracklog
from ._utils import export_metadata_file, md5sum
from .datastructure._internal import internal
from .datastructure.meta import meta
from .exceptions import InvalidMetadataError
from .providers._filedata import ShareFolder
from .providers._fmu import (
    ERT_RELATIVE_CASE_METADATA_FILE,
    FmuProvider,
    get_fmu_context_from_environment,
)

logger: Final = null_logger(__name__)

# ######################################################################################
# ExportPreprocessedData.
#
# The ExportPreprocessedData is used for exporting preprocessed data that already
# contains metadata, into a FMU run.
# ######################################################################################


@dataclass
class ExportPreprocessedData:
    """Export a preprocessed file and its metadata into a FMU run at case level.

    The existing metadata will be validated and three fields will be updated
    - The 'fmu' block will be added with information about the existing FMU/ERT run
    - The 'file' block will be updated with new file paths.
    - The 'tracklog' block will be extended with a new event tagged "merged".

    Note it is important that the preprocessed data have been created upfront with the,
    ExportData class using the argument fmu_context='preprocessed'. This ensures
    that the file and metadata are stored in the 'share/preprocessed/' folder.

    Args:
        config: Required dictionary with 'model' information; 'name' and 'revision'.
            Example is {'model': {'name': 'mymodelname', 'revision': '1.0.0'}}
            Normally read from FMU global variables (via fmuconfig).

        casepath: Required casepath for the active ERT experiment. The case needs to
            contain valid case metadata i.e. the ERT workflow 'WF_CREATE_CASE_METADATA'
            has been run prior to using this class.

        is_observation: Default is True. If True, then disk storage will be on the
            "casepath/share/observations" folder, otherwise on casepath/share/result.
    """

    config: dict
    casepath: str | Path
    is_observation: bool = True

    _fmudata: FmuProvider | None = field(default=None)

    def __post_init__(self) -> None:
        if get_fmu_context_from_environment() != FmuContext.CASE:
            raise RuntimeError(
                "Only possible to run re-export of preprocessed data inside FMU "
                "using a pre-simulation workflow in ERT."
            )

        self._fmudata = FmuProvider(
            model=self.config.get("model"),
            fmu_context=FmuContext.CASE,
            casepath_proposed=Path(self.casepath),
            workflow=None,
        )

        if not (casepath := self._fmudata.get_casepath()):
            raise ValueError(
                "Could not detect valid case metadata at file location:"
                f"{Path(self.casepath) / ERT_RELATIVE_CASE_METADATA_FILE}. Provide an "
                "updated casepath. Note, it is required to have run the ERT workflow "
                "'WF_CREATE_CASE_METADATA' prior to this export job. See how-to here: "
                "https://fmu-dataio.readthedocs.io/en/latest/"
                "preparations.html#workflow-for-creating-case-metadata"
            )

        self.casepath = casepath.absolute()

    @staticmethod
    def _validate_object(obj: str | Path) -> Path:
        """
        Check that the input object is an existing file and convert it
        to an absolute path.
        """
        if not isinstance(obj, (str, Path)):
            raise ValueError("Only file paths are supported as input object")

        objfile = Path(obj).resolve()
        if not objfile.exists():
            raise FileNotFoundError(f"The file {obj} does not exist.")

        if ShareFolder.PREPROCESSED not in str(objfile):
            raise RuntimeError(
                f"Exporting files located outside the '{ShareFolder.PREPROCESSED}' "
                "folder is not supported. Please re-export your objects to disk "
                "using ExportData(fmu_context='preprocessed')"
            )
        return objfile

    @staticmethod
    def _read_metadata_file(objmetafile: Path) -> dict | None:
        """
        Return a metadata file as a dictionary. If the metadata file
        is not present, None will be returned.
        """
        if objmetafile.exists():
            with open(objmetafile, encoding="utf-8") as stream:
                return yaml.safe_load(stream)
        return None

    def _get_relative_export_path(self, existing_path: Path) -> Path:
        """
        Get an updated relative_path from an existing path to a preprocessed
        file stored somewhere inside the 'share/preprocessed/' folder.
        The existing subfolders and filename will be kept.
        """
        existing_subfolders_and_filename = str(existing_path).rsplit(
            ShareFolder.PREPROCESSED, maxsplit=1
        )[-1]

        if self.is_observation:
            return (
                Path(ShareFolder.OBSERVATIONS.value) / existing_subfolders_and_filename
            )
        return Path(ShareFolder.RESULTS.value) / existing_subfolders_and_filename

    @staticmethod
    def _check_md5sum_consistency(
        checksum_md5_file: str, checksum_md5_meta: str
    ) -> None:
        """Check if the md5sum for the file is equal to the one in the metadata"""
        if checksum_md5_file != checksum_md5_meta:
            warnings.warn(
                "The preprocessed file seem to have been modified since it was "
                "initially exported. You are adviced to re-create the preprocessed "
                "data to prevent mismatch between the file and its metadata."
            )

    def _get_meta_file(self, objfile: Path, checksum_md5: str) -> meta.File:
        """Return a meta.File model with updated paths and checksum_md5"""
        relative_path = self._get_relative_export_path(existing_path=objfile)
        return meta.File(
            absolute_path=self.casepath / relative_path,
            relative_path=relative_path,
            checksum_md5=checksum_md5,
        )

    def _get_updated_metadata(self, meta_existing: dict, objfile: Path) -> dict:
        """
        Update the existing metadata with updated fmu/file/tracklog info:
        - The 'fmu' block will be added
        - The 'file' block will be updated with new paths.
        - The 'tracklog' block will be extended with a new event tagged "merged".

        A simple consistency check will be run to detect if the file has been
        modified since it was initially exported.

        Subsequently the final metadata is validated against the schema to ensure
        it is ready for sumo upload, before it is returned.
        """
        assert self._fmudata is not None

        checksum_md5_file = md5sum(objfile)
        if checksum_md5_meta := meta_existing["file"].get("checksum_md5"):
            self._check_md5sum_consistency(checksum_md5_file, checksum_md5_meta)

        # remove '_preprocessed' key if present and check truthy state of it
        if not meta_existing.pop("_preprocessed", False):
            raise ValueError(
                "Missing entry '_preprocessed' in the metadata. Only files exported "
                "with ExportData(fmu_context='preprocessed') is supported. "
                "Please re-export your objects to disk."
            )

        meta_existing["fmu"] = self._fmudata.get_metadata()
        meta_existing["file"] = self._get_meta_file(objfile, checksum_md5_file)

        # update the tracklog block
        tracklog_entry = generate_meta_tracklog(event="merged")
        meta_existing["tracklog"].extend(tracklog_entry)

        try:
            # TODO: Would like to use meta.Root.model_validate() here
            # but then the '$schema' field is dropped from the meta_existing
            return internal.DataClassMeta.model_validate(meta_existing).model_dump(
                mode="json", exclude_none=True, by_alias=True
            )
        except ValidationError as err:
            raise InvalidMetadataError(
                f"The existing metadata for the preprocessed file {objfile} is "
                "outdated. The files will still be copied to the fmu case but no "
                "metadata will be made. Please re-export the preprocessed object to "
                "disk to ensure the metadata are following the latest data standards. "
                f"Detailed information: \n{str(err)}"
            ) from err

    # ==================================================================================
    # Public methods:
    # ==================================================================================

    def generate_metadata(self, obj: str | Path) -> dict:
        """Generate updated metadata for the preprocessed data.

        Returns:
            A dictionary with all metadata.
        """

        objfile = self._validate_object(obj)
        objmetafile = objfile.parent / f".{objfile.name}.yml"

        if meta_existing := self._read_metadata_file(objmetafile):
            return self._get_updated_metadata(meta_existing, objfile)

        raise RuntimeError(
            f"Could not detect existing metadata with name {objmetafile}"
        )

    def export(self, obj: str | Path) -> str:
        """Re-export preprocessed file with updated metadata.
        If existing metadata can't be found or it is outdated,
        the file will still be copied but metadata will not be created.

        Returns:
            Full path of exported object file.
        """
        objfile = self._validate_object(obj)
        objmetafile = objfile.parent / f".{objfile.name}.yml"

        outfile = self.casepath / self._get_relative_export_path(existing_path=objfile)
        outfile.parent.mkdir(parents=True, exist_ok=True)

        # copy existing file to updated path
        shutil.copy(objfile, outfile)
        logger.info("Copied input file to: %s", outfile)

        if meta_existing := self._read_metadata_file(objmetafile):
            try:
                meta_updated = self._get_updated_metadata(meta_existing, objfile)
            except InvalidMetadataError as err:
                warnings.warn(str(err))
            else:
                # store metafile to updated path
                metafile = outfile.parent / f".{outfile.name}.yml"
                export_metadata_file(
                    file=metafile, metadata=meta_updated, savefmt="yaml"
                )
                logger.info("Updated metadata file is: %s", metafile)
        else:
            warnings.warn(
                f"Could not detect existing metadata with name {objmetafile}. "
                f"Input file will be copied to {outfile}, but without metadata."
            )

        return str(outfile)
