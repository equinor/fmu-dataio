"""Module for DataIO FmuProvider

The FmuProvider will from the environment and eventually API's detect valid
fields to the FMU data block.

Note that FMU may potentially have different providers, e.g. ERT versions
or it can detect that no FMU providers are present (e.g. just ran from RMS interactive)

Note that establishing the FMU case metadata for a run, is currently *not* done
here; this is done by code in the CreateCaseMetadata class.

From ERT v. 5 (?), the following env variables are provided in startup (example):

_ERT_EXPERIMENT_ID:   6a8e1e0f-9315-46bb-9648-8de87151f4c7
_ERT_ENSEMBLE_ID:   b027f225-c45d-477d-8f33-73695217ba14
_ERT_SIMULATION_MODE:   test_run

and during a Forward model:

_ERT_EXPERIMENT_ID:   6a8e1e0f-9315-46bb-9648-8de87151f4c7
_ERT_ENSEMBLE_ID:   b027f225-c45d-477d-8f33-73695217ba14
_ERT_SIMULATION_MODE:   test_run
_ERT_ITERATION_NUMBER:   0
_ERT_REALIZATION_NUMBER:   0
_ERT_RUNPATH:   /scratch/fmu/jriv/01_drogon_ahm/realization-0/iter-0/

"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Final
from warnings import warn

import pydantic

from fmu.config import utilities as ut
from fmu.dataio import _utils
from fmu.dataio._logging import null_logger
from fmu.dataio._metadata import CaseMetadataExport
from fmu.dataio._models.fmu_results import fields
from fmu.dataio._models.fmu_results.enums import ErtSimulationMode, FMUContext
from fmu.dataio.exceptions import InvalidMetadataError

from ._base import Provider

if TYPE_CHECKING:
    from uuid import UUID

# case metadata relative to casepath
ERT_RELATIVE_CASE_METADATA_FILE: Final = "share/metadata/fmu_case.yml"
RESTART_PATH_ENVNAME: Final = "RESTART_FROM_PATH"
DEFAULT_ENSMEBLE_NAME: Final = "iter-0"

logger: Final = null_logger(__name__)


def get_fmu_context_from_environment() -> FMUContext | None:
    """return the ERT run context as an FMUContext"""
    if FmuEnv.RUNPATH.value:
        return FMUContext.realization
    if FmuEnv.EXPERIMENT_ID.value:
        return FMUContext.case
    return None


def _casepath_has_metadata(casepath: Path) -> bool:
    """Check if a proposed casepath has a metadata file"""
    if (casepath / ERT_RELATIVE_CASE_METADATA_FILE).exists():
        logger.debug("Found metadata for proposed casepath <%s>", casepath)
        return True
    logger.debug("Did not find metadata for proposed casepath <%s>", casepath)
    return False


class FmuEnv(Enum):
    EXPERIMENT_ID = auto()
    ENSEMBLE_ID = auto()
    SIMULATION_MODE = auto()
    REALIZATION_NUMBER = auto()
    ITERATION_NUMBER = auto()
    RUNPATH = auto()

    @property
    def value(self) -> str | None:
        # Fetch the environment variable; name of the enum member prefixed with _ERT_
        return os.getenv(f"_ERT_{self.name}")

    @property
    def keyname(self) -> str:
        # Fetch the environment variable; name of the enum member prefixed with _ERT_
        return f"_ERT_{self.name}"


@dataclass
class FmuProvider(Provider):
    """Class for getting the run environment (e.g. an ERT) and provide metadata.

    Args:
        model: Name of the model (usually from global config)
        fmu_context: The FMU context this is ran in; see FMUContext enum class
        casepath_proposed: Proposed casepath. Needed if FMUContext is CASE
        workflow: Descriptive work flow info
    """

    model: fields.Model | None = None
    fmu_context: FMUContext = FMUContext.realization
    casepath_proposed: Path | None = None
    workflow: str | dict[str, str] | None = None
    object_share_path: Path | None = None

    # private properties for this class
    _runpath: Path | None = field(default_factory=Path, init=False)
    _casepath: Path | None = field(default_factory=Path, init=False)
    _ensemble_name: str = field(default="", init=False)
    _ensemble_id: int = field(default=0, init=False)
    _real_name: str = field(default="", init=False)
    _real_id: int = field(default=0, init=False)
    _case_name: str = field(default="", init=False)

    def __post_init__(self) -> None:
        logger.info("Initialize %s...", self.__class__)
        logger.debug("Case path is initially <%s>...", self.casepath_proposed)

        self._runpath = self._get_runpath_from_env()
        logger.debug("Runpath is %s", self._runpath)

        self._real_id = (
            int(real_num) if (real_num := FmuEnv.REALIZATION_NUMBER.value) else 0
        )
        self._ensemble_id = (
            int(iter_num) if (iter_num := FmuEnv.ITERATION_NUMBER.value) else 0
        )

        self._casepath = self._validate_and_establish_casepath()
        if self._casepath:
            self._case_name = self._casepath.name

            if self._runpath and self.fmu_context != FMUContext.case:
                missing_ensemble_folder = self._casepath == self._runpath.parent
                if not missing_ensemble_folder:
                    logger.debug("Ensemble folder found")
                    self._ensemble_name = self._runpath.name
                    self._real_name = self._runpath.parent.name
                else:
                    logger.debug("No ensemble folder found, using default name iter-0")
                    self._ensemble_name = DEFAULT_ENSMEBLE_NAME
                    self._real_name = self._runpath.name

                logger.debug(
                    "Found ensemble name from runpath: %s", self._ensemble_name
                )
                logger.debug("Found real name from runpath: %s", self._real_name)

    def get_ensemble_name(self) -> str:
        """Return the ensemble name, e.g. 'iter-3' or 'pred'."""
        return self._ensemble_name

    def get_real_name(self) -> str:
        """Return the real_name, e.g. 'realization-23'."""
        return self._real_name

    def get_casepath(self) -> Path | None:
        """Return updated casepath in a FMU run, will be updated if initially blank."""
        return self._casepath

    def get_runpath(self) -> Path | None:
        """Return runpath for a FMU run."""
        return self._runpath

    def get_metadata(self) -> fields.FMU:
        """Construct the metadata FMU block for an ERT forward job."""
        logger.debug("Generate ERT metadata...")

        if self._casepath is None:
            raise InvalidMetadataError("Missing casepath")

        case_meta = self._get_case_meta()

        if self.fmu_context != FMUContext.realization:
            return fields.FMU(
                case=case_meta.fmu.case,
                context=self._get_fmucontext_meta(),
                model=self.model or case_meta.fmu.model,
                workflow=self._get_workflow_meta() if self.workflow else None,
                ert=self._get_ert_meta(),
            )

        case_uuid = case_meta.fmu.case.uuid
        ensemble_uuid, real_uuid = self._get_ensemble_and_real_uuid(case_uuid)

        return fields.FMU(
            case=case_meta.fmu.case,
            context=self._get_fmucontext_meta(),
            model=self.model or case_meta.fmu.model,
            workflow=self._get_workflow_meta() if self.workflow else None,
            ensemble=self._get_ensemble_meta(ensemble_uuid),
            realization=self._get_realization_meta(real_uuid),
            ert=self._get_ert_meta(),
            entity=self._get_entity_meta(case_uuid),
        )

    @staticmethod
    def _get_runpath_from_env() -> Path | None:
        """get runpath as an absolute path if detected from the enviroment"""
        return Path(runpath).resolve() if (runpath := FmuEnv.RUNPATH.value) else None

    @staticmethod
    def _get_ert_meta() -> fields.Ert | None:
        """Constructs the `Ert` Pydantic object for the `ert` metadata field."""
        return (
            fields.Ert(
                experiment=(
                    fields.Experiment(
                        id=uuid.UUID(FmuEnv.EXPERIMENT_ID.value),
                    )
                ),
                simulation_mode=ErtSimulationMode(FmuEnv.SIMULATION_MODE.value),
            )
            if FmuEnv.EXPERIMENT_ID.value
            else None
        )

    def _validate_and_establish_casepath(self) -> Path | None:
        """If casepath is not given, then try update _casepath (if in realization).

        There is also a validation here that casepath contains case metadata, and if not
        then a second guess is attempted, looking at `parent` insted of `parent.parent`
        is case of missing ensemble folder.
        """
        if self.casepath_proposed:
            if _casepath_has_metadata(self.casepath_proposed):
                return self.casepath_proposed
            warn(
                "Could not detect metadata for the proposed casepath "
                f"{self.casepath_proposed}. Will try to detect from runpath."
            )
        if self._runpath:
            if _casepath_has_metadata(self._runpath.parent.parent):
                return self._runpath.parent.parent

            if _casepath_has_metadata(self._runpath.parent):
                return self._runpath.parent

        if self.fmu_context == FMUContext.case:
            # TODO: add ValueError when no longer kwargs are accepted in export()
            ...

        logger.debug("No case metadata, issue a warning!")
        warn(
            "Could not auto detect the case metadata, please provide the "
            "'casepath' as input. Metadata will be empty!",
            UserWarning,
        )
        return None

    def _get_restart_data_uuid(self) -> UUID | None:
        """Load restart_from information"""
        assert self._runpath is not None
        logger.debug("Detected a restart run from environment variable")
        restart_path = (self._runpath / os.environ[RESTART_PATH_ENVNAME]).resolve()

        if _casepath_has_metadata(restart_path.parent.parent):
            restart_case_metafile = (
                restart_path.parent.parent / ERT_RELATIVE_CASE_METADATA_FILE
            )
            restart_ensemble_name = restart_path.name
        elif _casepath_has_metadata(restart_path.parent):
            restart_case_metafile = (
                restart_path.parent / ERT_RELATIVE_CASE_METADATA_FILE
            )
            restart_ensemble_name = DEFAULT_ENSMEBLE_NAME
        else:
            warn(
                f"Environment variable {RESTART_PATH_ENVNAME} resolves to the path "
                f"{restart_path} which is non existing or points to an ERT run "
                "without case metdata. Metadata 'restart_from' will remain empty.",
                UserWarning,
            )
            return None

        try:
            restart_metadata = CaseMetadataExport.model_validate(
                ut.yaml_load(restart_case_metafile)
            )
            return _utils.uuid_from_string(
                f"{restart_metadata.fmu.case.uuid}{restart_ensemble_name}"
            )
        except pydantic.ValidationError as err:
            warn(
                "The case metadata for the restart ensemble is invalid "
                f"{restart_case_metafile}. Metadata 'restart_from' will remain empty. "
                f"Detailed information: \n {str(err)}",
                UserWarning,
            )
            return None

    def _get_ensemble_and_real_uuid(self, case_uuid: UUID) -> tuple[UUID, UUID]:
        ensemble_uuid = _utils.uuid_from_string(f"{case_uuid}{self._ensemble_name}")
        real_uuid = _utils.uuid_from_string(
            f"{case_uuid}{ensemble_uuid}{self._real_id}"
        )
        return ensemble_uuid, real_uuid

    def _get_case_meta(self) -> CaseMetadataExport:
        """Parse and validate the CASE metadata."""
        logger.debug("Loading case metadata file and return pydantic case model")
        assert self._casepath is not None
        case_metafile = self._casepath / ERT_RELATIVE_CASE_METADATA_FILE
        return CaseMetadataExport.model_validate(
            ut.yaml_load(case_metafile, loader="standard")
        )

    def _get_realization_meta(self, real_uuid: UUID) -> fields.Realization:
        return fields.Realization(
            id=self._real_id,
            name=self._real_name,
            uuid=real_uuid,
        )

    def _get_ensemble_meta(self, ensemble_uuid: UUID) -> fields.Ensemble:
        return fields.Ensemble(
            id=self._ensemble_id,
            name=self._ensemble_name,
            uuid=ensemble_uuid,
            restart_from=self._get_restart_data_uuid()
            if os.getenv(RESTART_PATH_ENVNAME)
            else None,
        )

    def _get_fmucontext_meta(self) -> fields.Context:
        return fields.Context(stage=self.fmu_context)

    def _get_entity_uuid(self, case_uuid: UUID) -> UUID:
        """
        Get the entity UUID generated from the case uuid and the
        share path for the object. This is an identifer used for linking
        objects across a case that represents the same.
        """
        return _utils.uuid_from_string(f"{case_uuid}{self.object_share_path}")

    def _get_entity_meta(self, case_uuid: UUID) -> fields.Entity:
        """Get the fmu.entity model"""
        return fields.Entity(uuid=self._get_entity_uuid(case_uuid))

    def _get_workflow_meta(self) -> fields.Workflow:
        assert self.workflow is not None
        if isinstance(self.workflow, dict):
            return fields.Workflow.model_validate(self.workflow)
        return fields.Workflow(reference=self.workflow)
