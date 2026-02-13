from __future__ import annotations

import copy
import getpass
import uuid
import warnings
from pathlib import Path
from typing import Any, Final, Self

from pydantic import ValidationError

from fmu.dataio._export import export_metadata_file
from fmu.dataio._logging import null_logger
from fmu.dataio.version import __version__
from fmu.datamodels.common import Access, Tracklog, User
from fmu.datamodels.fmu_results import enums, fields, global_configuration
from fmu.datamodels.fmu_results.fmu_results import CaseMetadata

from ._config import CaseWorkflowConfig

logger: Final = null_logger(__name__)


class ExportCaseMetadata:
    """Creates and exports metadata for an FMU Case.

    This class is used for exporting the case metadata before the simulation begins.
    If the case metadata file may already exists a warning is emitted.

    The metadata and uuid are used to register the case on Sumo, if Sumo is enabled.

    Args:
        config: An object representing the global configuration.
        rootfolder: Absolute path to the case root, including case name.
        casename: Name of case (experiment)
    """

    def __init__(
        self,
        config: global_configuration.GlobalConfiguration | dict[str, Any],
        rootfolder: str | Path,
        casename: str,
    ) -> None:
        """Initialize the ExportCaseMetadata class."""

        # TODO: Receive only validated config
        if isinstance(config, dict):
            try:
                self.config = global_configuration.GlobalConfiguration.model_validate(
                    config
                )
            except ValidationError as e:
                global_configuration.validation_error_warning(e)
                raise
        else:
            self.config = config

        self.rootfolder = rootfolder
        self.casename = casename
        self._casepath = Path(self.rootfolder)
        self._metafile = self._casepath / "share/metadata/fmu_case.yml"
        self._metadata: dict = {}
        logger.info("Ran __init__ for ExportCaseMetadata")

    def _establish_metadata_files(self) -> bool:
        """Checks if the metadata files and directories are established and creates
        relevant directories and files if not.

        Returns:
            False if fmu_case.yml exists (not established), True if it doesn't.
        """
        if not self._metafile.parent.exists():
            self._metafile.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Created rootpath (case) %s", self._casepath)
        logger.info("The requested metafile is %s", self._metafile)
        return not self._metafile.exists()

    def _case_uuid(self) -> uuid.UUID:
        """
        Generates and persists a unique UUID for a new case.

        Upon creation of a new case, this UUID is stored in case
        metadata and written to disk, ensuring it remains constant for the case across
        runs and exports. It is foundational for tracking cases and embedding
        identifiers into file metadata.
        """
        return uuid.uuid4()

    def generate_metadata(self) -> dict:
        """Generate case metadata.

        Returns:
            A dictionary with case metadata or an empty dictionary if the metadata
            already exists.
        """
        if not self._establish_metadata_files():
            exists_warning = (
                f"Using existing case metadata from casepath: '{self.rootfolder}'. "
                "All data exported to Sumo will be stored to this existing case in "
                "Sumo. If you want to create a new case in Sumo to store your data to, "
                "delete the old case from the scratch disk, or run on a different "
                "casepath by editing your ERT configuration file.\n\n"
                "Ignore this warning if your model is not enabled for Sumo yet, "
                "or if storing to the existing case in Sumo is what you want."
            )
            logger.warning(exists_warning)
            warnings.warn(exists_warning, UserWarning)
            return {}

        self._metadata = CaseMetadata(  # type: ignore[call-arg]
            class_=enums.FMUResultsMetadataClass.case,
            masterdata=self.config.masterdata,
            access=Access.model_validate(self.config.access.model_dump()),
            fmu=fields.FMUBase(
                model=self.config.model,
                case=fields.Case(
                    name=self.casename,
                    uuid=self._case_uuid(),
                    user=User(id=getpass.getuser()),
                    description=None,
                ),
            ),
            tracklog=Tracklog.initialize(__version__),
        ).model_dump(
            mode="json",
            exclude_none=True,
            by_alias=True,
        )

        return copy.deepcopy(self._metadata)

    def export(self) -> str:
        """Export case metadata to file.

        Returns:
            Full path of metadata file.
        """
        if self.generate_metadata():
            export_metadata_file(self._metafile, self._metadata)
            logger.info("METAFILE %s", self._metafile)
        return str(self._metafile)

    @classmethod
    def from_workflow_config(cls, workflow_config: CaseWorkflowConfig) -> Self:
        """Instantiate from a workflow configuration."""
        return cls(
            config=workflow_config.global_config,
            rootfolder=workflow_config.casepath,
            casename=workflow_config.casename,
        )
