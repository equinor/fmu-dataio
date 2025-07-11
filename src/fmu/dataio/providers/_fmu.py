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
from fmu.dataio._runcontext import FmuEnv
from fmu.dataio.exceptions import InvalidMetadataError
from fmu.datamodels.fmu_results import fields
from fmu.datamodels.fmu_results.enums import ErtSimulationMode, FMUContext
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
        object_share_path: The share path location for the object
    """

    def __init__(
        self,
        runcontext: RunContext,
        model: fields.Model | None = None,
        workflow: str | dict[str, str] | None = None,
        object_share_path: Path | None = None,
    ) -> None:
        logger.info("Initialize %s...", self.__class__)
        self.model = model
        self.workflow = workflow
        self.object_share_path = object_share_path

        self._runpath = runcontext.runpath
        self._casepath = runcontext.casepath
        self._casemeta = runcontext.case_metadata
        self._fmu_context = runcontext.fmu_context
        self._real_id = (
            int(real_num) if (real_num := FmuEnv.REALIZATION_NUMBER.value) else 0
        )
        self._ensemble_id = (
            int(iter_num) if (iter_num := FmuEnv.ITERATION_NUMBER.value) else 0
        )
        self._ensemble_name, self._real_name = self._establish_ensemble_and_real_name()

    def get_metadata(self) -> fields.FMU:
        """Construct the metadata FMU block for an ERT forward job."""
        logger.debug("Generate ERT metadata...")

        case_meta = self._casemeta
        if case_meta is None:
            raise InvalidMetadataError("Missing casepath or case metadata.")

        if self._fmu_context != FMUContext.realization:
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

    def _establish_ensemble_and_real_name(self) -> tuple[str, str]:
        """
        Establish the ensemble and real name from the runpath.
        If no ensemble folder is found, the default name `iter-0` is used.
        If the runpath and casepath is not set empty strings are returned.
        """
        if not (self._casepath and self._runpath):
            return ("", "")

        missing_ensemble_folder = self._casepath == self._runpath.parent
        if not missing_ensemble_folder:
            logger.debug("Ensemble folder found")
            ensemble_name = self._runpath.name
            real_name = self._runpath.parent.name
        else:
            logger.debug("No ensemble folder found, using default name iter-0")
            ensemble_name = DEFAULT_ENSMEBLE_NAME
            real_name = self._runpath.name

        logger.debug("Found ensemble name from runpath: %s", ensemble_name)
        logger.debug("Found real name from runpath: %s", real_name)
        return ensemble_name, real_name

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
            f"{case_uuid}{ensemble_uuid}{self._real_id}"
        )
        return ensemble_uuid, real_uuid

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
        assert self._fmu_context is not None
        return fields.Context(stage=self._fmu_context)

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
