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
from pathlib import Path
from typing import TYPE_CHECKING, Final
from warnings import warn

import pydantic

from fmu.config import utilities as ut
from fmu.dataio import _utils
from fmu.dataio._definitions import ERT_RELATIVE_CASE_METADATA_FILE
from fmu.dataio._logging import null_logger
from fmu.dataio._runcontext import FMUEnvironment
from fmu.dataio.exceptions import InvalidMetadataError
from fmu.datamodels.fmu_results import fields
from fmu.datamodels.fmu_results.enums import ErtSimulationMode, FMUContext
from fmu.datamodels.fmu_results.fields import Workflow
from fmu.datamodels.fmu_results.fmu_results import CaseMetadata

from ._base import Provider

if TYPE_CHECKING:
    from uuid import UUID

    from fmu.dataio._runcontext import RunContext

# case metadata relative to casepath
RESTART_PATH_ENVNAME: Final = "RESTART_FROM_PATH"
DEFAULT_ENSMEBLE_NAME: Final = "iter-0"

logger: Final = null_logger(__name__)


class FmuProvider(Provider):
    """Class for providing metadata regarding the ERT run.

    Args:
        model: Name of the model (usually from global config)
        runcontext: The context this is ran in, with paths and case metadata
        workflow: Descriptive work flow info
        share_path: The share path location for the object
    """

    def __init__(
        self,
        runcontext: RunContext,
        model: fields.Model | None = None,
        workflow: Workflow | None = None,
        share_path: Path | None = None,
    ) -> None:
        logger.info("Initialize %s...", self.__class__)
        self.model = model
        self.workflow = workflow
        self.share_path = share_path

        self._runpath = runcontext.runpath
        self._casepath = runcontext.casepath
        self._casemeta = runcontext.case_metadata
        self._fmu_context = runcontext.fmu_context
        self._env = FMUEnvironment.from_env()
        self._realization_number = self._env.realization_number or 0
        self._iteration_number = self._env.iteration_number or 0
        self._ensemble_name = runcontext.paths.ensemble_name or ""
        self._realization_name = runcontext.paths.realization_name or ""

    def get_metadata(self) -> fields.FMU:
        """Construct the metadata FMU block for an ERT forward job."""
        logger.debug("Generate ERT metadata...")

        case_meta = self._casemeta
        if case_meta is None:
            raise InvalidMetadataError("Missing casepath or case metadata.")

        case_uuid = case_meta.fmu.case.uuid

        if self._fmu_context == FMUContext.case:
            return fields.FMU(
                case=case_meta.fmu.case,
                context=self._get_fmucontext_meta(),
                model=self.model or case_meta.fmu.model,
                workflow=self.workflow,
                ert=self._get_ert_meta(),
            )

        ensemble_uuid, real_uuid = self._get_ensemble_and_real_uuid(case_uuid)

        if self._fmu_context == FMUContext.ensemble:
            return fields.FMU(
                case=case_meta.fmu.case,
                context=self._get_fmucontext_meta(),
                model=self.model or case_meta.fmu.model,
                workflow=self.workflow,
                ensemble=self._get_ensemble_meta(ensemble_uuid),
                ert=self._get_ert_meta(),
            )

        return fields.FMU(
            case=case_meta.fmu.case,
            context=self._get_fmucontext_meta(),
            model=self.model or case_meta.fmu.model,
            workflow=self.workflow,
            ensemble=self._get_ensemble_meta(ensemble_uuid),
            realization=self._get_realization_meta(real_uuid),
            ert=self._get_ert_meta(),
            entity=self._get_entity_meta(case_uuid),
        )

    def _get_ert_meta(self) -> fields.Ert | None:
        """Constructs the `Ert` Pydantic object for the `ert` metadata field."""
        if not self._env.experiment_id or not self._env.simulation_mode:
            return None

        ensemble: fields.Ensemble | None = None
        if self._env.ensemble_id:
            ensemble = fields.Ensemble(
                name=self._ensemble_name,
                uuid=uuid.UUID(self._env.ensemble_id),
                id=self._iteration_number,
            )

        return fields.Ert(
            experiment=fields.Experiment(id=uuid.UUID(self._env.experiment_id)),
            simulation_mode=ErtSimulationMode(self._env.simulation_mode),
            ensemble=ensemble,
        )

    def _get_restart_data_uuid(self) -> UUID | None:
        """Load restart_from information"""
        assert self._runpath is not None
        logger.debug("Detected a restart run from environment variable")
        restart_path = (self._runpath / os.environ[RESTART_PATH_ENVNAME]).resolve()

        if _utils.casepath_has_metadata(restart_path.parent.parent):
            restart_case_metafile = (
                restart_path.parent.parent / ERT_RELATIVE_CASE_METADATA_FILE
            )
            restart_ensemble_name = restart_path.name
        elif _utils.casepath_has_metadata(restart_path.parent):
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
            restart_metadata = CaseMetadata.model_validate(
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
            f"{case_uuid}{ensemble_uuid}{self._realization_number}"
        )
        return ensemble_uuid, real_uuid

    def _get_realization_meta(self, real_uuid: UUID) -> fields.Realization:
        return fields.Realization(
            id=self._realization_number,
            name=self._realization_name,
            uuid=real_uuid,
        )

    def _get_ensemble_meta(self, ensemble_uuid: UUID) -> fields.Ensemble:
        return fields.Ensemble(
            name=self._ensemble_name,
            uuid=ensemble_uuid,
            restart_from=(
                self._get_restart_data_uuid()
                if os.getenv(RESTART_PATH_ENVNAME)
                else None
            ),
            id=self._iteration_number,
        )

    def _get_fmucontext_meta(self) -> fields.Context:
        assert self._fmu_context is not None
        return fields.Context(stage=self._fmu_context)

    def _get_entity_uuid(self, case_uuid: UUID) -> UUID:
        """
        Get the entity UUID generated from the case uuid and the
        share path for the object. This is an identifer used for linking
        objects across a case that represents the same.
        """
        return _utils.uuid_from_string(f"{case_uuid}{self.share_path}")

    def _get_entity_meta(self, case_uuid: UUID) -> fields.Entity:
        """Get the fmu.entity model"""
        return fields.Entity(uuid=self._get_entity_uuid(case_uuid))
