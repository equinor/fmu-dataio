from __future__ import annotations

import copy
import getpass
import uuid
import warnings
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from fmu.dataio.version import __version__
from fmu.datamodels.fmu_results import enums, fields, global_configuration
from fmu.datamodels.fmu_results.fmu_results import CaseMetadata

from . import _utils
from ._logging import null_logger

logger: Final = null_logger(__name__)

# ######################################################################################
# CreateCaseMetadata.
#
# The CreateCaseMetadata is used for making the case matadata prior to any other
# actions, e.g. forward jobs. However, case metadata file may already exist,
# and in that case this class should only emit a message or warning.
# ######################################################################################


class CreateCaseMetadata:
    """Create metadata for an FMU Case.

    In ERT this is typically ran as an hook workflow in advance.

    Args:
        config: A configuration dictionary. In the standard case this is read
            from FMU global variables (via fmuconfig). The dictionary must contain
            some predefined main level keys. If config is None or the env variable
            FMU_GLOBAL_CONFIG pointing to a file is provided, then it will attempt to
            parse that file instead.
        rootfolder: Absolute path to the case root, including case name.
        casename: Name of case (experiment)
        description (Optional): Description text as string or list of strings.
    """

    def __init__(
        self,
        config: dict,
        rootfolder: str | Path,
        casename: str,
        description: str | list | None = None,  # deprecated
    ) -> None:
        """Initialize the CreateCaseMetadata class."""
        self.config = config
        self.rootfolder = rootfolder
        self.casename = casename

        if description:
            warnings.warn(
                "The 'description' argument is deprecated and no longer used.",
                FutureWarning,
            )

        self._casepath = Path(self.rootfolder)
        self._metafile = self._casepath / "share/metadata/fmu_case.yml"
        self._metadata: dict = {}

        # For this class, the global config must be valid; hence error if not
        try:
            global_configuration.GlobalConfiguration.model_validate(self.config)
        except ValidationError as e:
            global_configuration.validation_error_warning(e)
            raise
        logger.info("Ran __init__ for CreateCaseMetadata")

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

    # ==================================================================================
    # Public methods:
    # ==================================================================================

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
            masterdata=fields.Masterdata.model_validate(self.config["masterdata"]),
            access=fields.Access.model_validate(self.config["access"]),
            fmu=fields.FMUBase(
                model=fields.Model.model_validate(
                    self.config["model"],
                ),
                case=fields.Case(
                    name=self.casename,
                    uuid=self._case_uuid(),
                    user=fields.User(id=getpass.getuser()),
                    description=None,
                ),
            ),
            tracklog=fields.Tracklog.initialize(__version__),
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
            _utils.export_metadata_file(self._metafile, self._metadata)
            logger.info("METAFILE %s", self._metafile)
        return str(self._metafile)
