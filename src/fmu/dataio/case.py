from __future__ import annotations

import copy
import uuid
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from fmu.dataio._models.fmu_results import fields, global_configuration

from . import _utils
from ._logging import null_logger
from ._metadata import CaseMetadataExport

logger: Final = null_logger(__name__)

# ######################################################################################
# CreateCaseMetadata.
#
# The CreateCaseMetadata is used for making the case matadata prior to any other
# actions, e.g. forward jobs. However, case metadata file may already exist,
# and in that case this class should only emit a message or warning.
# ######################################################################################


@dataclass
class CreateCaseMetadata:  # pylint: disable=too-few-public-methods
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
        caseuser: Username provided
        description (Optional): Description text as string or list of strings.
    """

    config: dict
    rootfolder: str | Path
    casename: str
    caseuser: str

    description: str | list | None = None

    _metadata: dict = field(default_factory=dict, init=False)
    _metafile: Path = field(default_factory=Path, init=False)
    _pwd: Path = field(default_factory=Path, init=False)
    _casepath: Path = field(default_factory=Path, init=False)

    def __post_init__(self) -> None:
        self._pwd = Path().absolute()
        self._casepath = Path(self.rootfolder)
        self._metafile = self._casepath / "share/metadata/fmu_case.yml"

        # For this class, the global config must be valid; hence error if not
        try:
            global_configuration.GlobalConfiguration.model_validate(self.config)
        except ValidationError as e:
            global_configuration.validation_error_warning(e)
            raise
        logger.info("Ran __post_init__ for CreateCaseMetadata")

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
                "Using existing case metadata from runpath: "
                "All data exported to Sumo will be stored to this existing case in "
                "Sumo. If you want to create a new case in Sumo to store your data to, "
                "delete the old case through Ert, or run on a different runpath "
                "by editing it in your Ert configuration model.\n\n"
                "Ignore this warning if your model is not enabled for Sumo yet, "
                "or if storing to the existing case in Sumo is what you want."
            )
            logger.warning(exists_warning)
            warnings.warn(exists_warning, UserWarning)
            return {}

        self._metadata = CaseMetadataExport(
            masterdata=fields.Masterdata.model_validate(self.config["masterdata"]),
            access=fields.Access.model_validate(self.config["access"]),
            fmu=fields.FMUBase(
                model=fields.Model.model_validate(
                    self.config["model"],
                ),
                case=fields.Case(
                    name=self.casename,
                    uuid=self._case_uuid(),
                    user=fields.User(id=self.caseuser),
                    description=None,
                ),
            ),
            tracklog=fields.Tracklog.initialize(),
            description=_utils.generate_description(self.description),
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
