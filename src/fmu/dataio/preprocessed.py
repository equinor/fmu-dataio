"""Module containing ExportPreprocessedData.

The ExportPreprocessedData is used for exporting preprocessed data that already
contains metadata, into a FMU run.
"""

import shutil
import warnings
from pathlib import Path
from typing import Any, Final

import yaml
from pydantic import ValidationError

from fmu.datamodels.common.enums import TrackLogEventType
from fmu.datamodels.fmu_results.enums import FMUContext
from fmu.datamodels.fmu_results.fields import File

from ._definitions import ERT_RELATIVE_CASE_METADATA_FILE
from ._export import ObjectMetadataExport, export_metadata_file
from ._logging import null_logger
from ._metadata import FmuMetadata, ShareFolder
from ._runcontext import RunContext
from ._utils import md5sum
from .exceptions import InvalidMetadataError
from .manifest._manifest import update_export_manifest
from .version import __version__

logger: Final = null_logger(__name__)


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
        casepath: Required casepath for the active ERT experiment. The case needs to
            contain valid case metadata i.e. the ERT workflow 'WF_CREATE_CASE_METADATA'
            has been run prior to using this class.

        is_observation: Default is True. If True, then disk storage will be on the
            "casepath/share/observations" folder, otherwise on casepath/share/result.
    """

    def __init__(
        self,
        casepath: str | Path,
        is_observation: bool = True,
    ) -> None:
        self._is_observation = is_observation
        self._runcontext = RunContext(
            casepath_proposed=Path(casepath),
            fmu_context=FMUContext.case,
        )

        if self._runcontext.env.fmu_context != FMUContext.case:
            raise RuntimeError(
                "Only possible to run re-export of preprocessed data inside FMU "
                "using a pre-simulation workflow in ERT."
            )

        if not self._runcontext.casepath:
            raise ValueError(
                "Could not detect valid case metadata at file location:"
                f"{Path(casepath) / ERT_RELATIVE_CASE_METADATA_FILE}. Provide an "
                "updated casepath. Note, it is required to have run the ERT workflow "
                "'WF_CREATE_CASE_METADATA' prior to this export job. See how-to here: "
                "https://fmu-dataio.readthedocs.io/en/latest/"
                "getting_started.html#workflow-for-creating-case-metadata"
            )

        self.casepath = self._runcontext.casepath.absolute()

    @staticmethod
    def _validate_object(obj: str | Path) -> Path:
        """
        Check that the input object is an existing file and convert it
        to an absolute path.
        """
        if not isinstance(obj, str | Path):
            raise ValueError("Only file paths are supported as input object")

        objfile = Path(obj).resolve()
        if not objfile.exists():
            raise FileNotFoundError(f"The file {obj} does not exist.")

        if ShareFolder.PREPROCESSED not in str(objfile):
            raise RuntimeError(
                f"Exporting files located outside the '{ShareFolder.PREPROCESSED}' "
                "folder is not supported. Please re-export your objects to disk "
                "using ExportData(preprocessed=True)"
            )
        return objfile

    @staticmethod
    def _sidecar_metafile_path(objfile: Path) -> Path:
        """Return the path to the metadata sidecar for an object file."""
        return objfile.parent / f".{objfile.name}.yml"

    @staticmethod
    def _read_metadata_file(objmetafile: Path) -> dict[str, Any] | None:
        """
        Return a metadata file as a dictionary. If the metadata file
        is not present, None will be returned.
        """
        if not objmetafile.is_file():
            return None
        return yaml.safe_load(objmetafile.read_text())

    def _get_relative_export_path(self, existing_path: Path) -> Path:
        """
        Get an updated relative_path from an existing path to a preprocessed
        file stored somewhere inside the 'share/preprocessed/' folder.
        The existing subfolders and filename will be kept.
        """
        share_folder = (
            Path(ShareFolder.OBSERVATIONS.value)
            if self._is_observation
            else Path(ShareFolder.RESULTS.value)
        )
        for parent in existing_path.parents:
            if parent.name == "preprocessed" and parent.parent.name == "share":
                return share_folder / existing_path.relative_to(parent)

        raise RuntimeError(
            f"Path {existing_path} is not inside a '{ShareFolder.PREPROCESSED}' folder."
        )

    def _check_md5sum_consistency(
        self, checksum_md5_file: str, checksum_md5_meta: str
    ) -> None:
        """Check if the md5sum for the file is equal to the one in the metadata."""
        if checksum_md5_file != checksum_md5_meta:
            warnings.warn(
                "The preprocessed file seems to have been modified since it was "
                "initially exported. You are advised to re-create the preprocessed "
                "data to prevent mismatch between the file and its metadata."
            )

    def _require_preprocessed_flag(self, existing_metadata: dict[str, Any]) -> None:
        """Remove '_preprocessed' from the metadata and reject non-preprocessed data."""
        if not existing_metadata.pop("_preprocessed", False):
            raise ValueError(
                "Missing entry '_preprocessed' in the metadata. Only files exported "
                "with ExportData(fmu_context='preprocessed') is supported. "
                "Please re-export your objects to disk."
            )

    def _build_file_metadata(self, objfile: Path, checksum_md5: str) -> File:
        """Return a File model with updated paths and checksum_md5"""
        relative_path = self._get_relative_export_path(existing_path=objfile)
        return File(
            absolute_path=self.casepath / relative_path,
            relative_path=relative_path,
            checksum_md5=checksum_md5,
        )

    def _get_updated_metadata(
        self, existing_metadata: dict[str, Any], objfile: Path
    ) -> dict[str, Any]:
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

        checksum_md5_file = md5sum(objfile)
        if checksum_md5_meta := existing_metadata["file"].get("checksum_md5"):
            self._check_md5sum_consistency(checksum_md5_file, checksum_md5_meta)

        self._require_preprocessed_flag(existing_metadata)

        existing_metadata["fmu"] = FmuMetadata(
            runcontext=self._runcontext
        ).get_metadata()
        existing_metadata["file"] = self._build_file_metadata(
            objfile, checksum_md5_file
        )

        try:
            # TODO: Would like to use meta.Root.model_validate() here
            # but then the '$schema' field is dropped from the existing_metadata
            validated_metadata = ObjectMetadataExport.model_validate(existing_metadata)
            validated_metadata.tracklog.append(TrackLogEventType.merged, __version__)
            return validated_metadata.model_dump(
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
        objmetafile = self._sidecar_metafile_path(objfile)

        if existing_metadata := self._read_metadata_file(objmetafile):
            return self._get_updated_metadata(existing_metadata, objfile)

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
        objmetafile = self._sidecar_metafile_path(objfile)

        outfile = self.casepath / self._get_relative_export_path(existing_path=objfile)
        outfile.parent.mkdir(parents=True, exist_ok=True)

        # copy existing file to updated path
        shutil.copy2(objfile, outfile)
        logger.info("Copied input file to: %s", outfile)

        if existing_metadata := self._read_metadata_file(objmetafile):
            try:
                updated_metadata = self._get_updated_metadata(
                    existing_metadata, objfile
                )
            except InvalidMetadataError as err:
                warnings.warn(str(err))
            else:
                metafile = self._sidecar_metafile_path(outfile)
                export_metadata_file(file=metafile, metadata=updated_metadata)
                logger.info("Updated metadata file is: %s", metafile)
                update_export_manifest(outfile, casepath=self._runcontext.casepath)
        else:
            warnings.warn(
                f"Could not detect existing metadata with name {objmetafile}. "
                f"Input file will be copied to {outfile}, but without metadata."
            )

        return str(outfile)
