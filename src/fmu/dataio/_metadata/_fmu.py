"""Contains the FMU provider class.

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
from typing import TYPE_CHECKING, Any, Final
from warnings import warn

import pydantic
import yaml

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

RESTART_PATH_ENVNAME: Final = "RESTART_FROM_PATH"
DEFAULT_ENSEMBLE_NAME: Final = "iter-0"

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
        self._model = model
        self._workflow = workflow
        self._share_path = share_path
        self._runcontext = runcontext
        self._env = FMUEnvironment.from_env()

    def get_metadata(self) -> fields.FMU:
        """Construct the metadata FMU block for an ERT forward job."""
        logger.debug("Generating FMU provider metadata")

        case_meta = self._require_case_metadata()
        case = case_meta.fmu.case
        model = self._model or case_meta.fmu.model
        context = self._fmu_context

        kwargs: dict[str, Any] = {
            "case": case,
            "context": fields.Context(stage=context),
            "model": model,
            "workflow": self._workflow,
            "ert": self._build_ert(),
        }

        if context == FMUContext.case:
            return fields.FMU.model_validate(kwargs)

        ensemble_uuid, real_uuid = self._derive_uuids(case.uuid)
        kwargs["ensemble"] = self._build_ensemble(ensemble_uuid)

        if context == FMUContext.ensemble:
            return fields.FMU.model_validate(kwargs)

        kwargs["realization"] = self._build_realization(real_uuid)
        kwargs["entity"] = self._build_entity(case.uuid)

        return fields.FMU.model_validate(kwargs)

    def _build_ert(self) -> fields.Ert | None:
        """Construct the `Ert` metadata, or None if env vars are missing."""
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

    def _build_ensemble(self, ensemble_uuid: UUID) -> fields.Ensemble:
        return fields.Ensemble(
            name=self._ensemble_name,
            uuid=ensemble_uuid,
            restart_from=self._resolve_restart_uuid(),
            id=self._iteration_number,
        )

    def _build_realization(self, real_uuid: UUID) -> fields.Realization:
        return fields.Realization(
            id=self._realization_number,
            name=self._realization_name,
            uuid=real_uuid,
        )

    def _build_entity(self, case_uuid: UUID) -> fields.Entity:
        entity_uuid = _utils.uuid_from_string(f"{case_uuid}{self._share_path}")
        return fields.Entity(uuid=entity_uuid)

    def _derive_uuids(self, case_uuid: UUID) -> tuple[UUID, UUID]:
        ensemble_uuid = _utils.uuid_from_string(f"{case_uuid}{self._ensemble_name}")
        real_uuid = _utils.uuid_from_string(
            f"{case_uuid}{ensemble_uuid}{self._realization_number}"
        )
        return ensemble_uuid, real_uuid

    def _resolve_restart_uuid(self) -> UUID | None:
        """Returns the restart-from ensemble UUID, or None."""
        restart_relpath = os.getenv(RESTART_PATH_ENVNAME)
        if not restart_relpath:
            return None

        logger.debug("Detected a restart run from environment variable")
        restart_path = self._require_runpath() / restart_relpath
        restart_path = restart_path.resolve()

        metadata_file, ensemble_name = self._find_restart_case_meta(restart_path)
        if metadata_file is None:
            return None

        return self._load_restart_ensemble_uuid(metadata_file, ensemble_name)

    def _find_restart_case_meta(self, restart_path: Path) -> tuple[Path | None, str]:
        """Locate the case metadata file relative to a restart path.

        Returns (metadata_file_path, ensemble_name) or (None, "") if not found.
        """
        # restart_path is the ensemble dir
        if _utils.casepath_has_metadata(restart_path.parent.parent):
            return (
                restart_path.parent.parent / ERT_RELATIVE_CASE_METADATA_FILE,
                restart_path.name,
            )

        # restart_path is directly under the case dir
        if _utils.casepath_has_metadata(restart_path.parent):
            return (
                restart_path.parent / ERT_RELATIVE_CASE_METADATA_FILE,
                DEFAULT_ENSEMBLE_NAME,
            )

        warn(
            f"Environment variable {RESTART_PATH_ENVNAME} resolves to the path "
            f"{restart_path} which is non existing or points to an ERT run "
            "without case metdata. Metadata 'restart_from' will remain empty.",
            UserWarning,
        )
        return None, ""

    @staticmethod
    def _load_restart_ensemble_uuid(
        metadata_file: Path,
        ensemble_name: str,
    ) -> UUID | None:
        """Parse case metadata and derive the restart ensemble UUID."""
        try:
            with open(metadata_file) as f:
                case_metadata_dict = yaml.safe_load(f.read())
            restart_metadata = CaseMetadata.model_validate(case_metadata_dict)

            return _utils.uuid_from_string(
                f"{restart_metadata.fmu.case.uuid}{ensemble_name}"
            )
        except pydantic.ValidationError as err:
            warn(
                "The case metadata for the restart ensemble is invalid "
                f"{metadata_file}. Metadata 'restart_from' will remain empty. "
                f"Detailed information: \n {str(err)}",
                UserWarning,
            )
            return None

    @property
    def _fmu_context(self) -> FMUContext:
        ctx = self._runcontext.fmu_context
        if ctx is None:
            raise InvalidMetadataError("FMU Context is not set on runcontext.")
        return ctx

    @property
    def _ensemble_name(self) -> str:
        return self._runcontext.paths.ensemble_name or ""

    @property
    def _realization_name(self) -> str:
        return self._runcontext.paths.realization_name or ""

    @property
    def _realization_number(self) -> int:
        return self._env.realization_number or 0

    @property
    def _iteration_number(self) -> int:
        return self._env.iteration_number or 0

    def _require_case_metadata(self) -> CaseMetadata:
        meta = self._runcontext.case_metadata
        if meta is None:
            raise InvalidMetadataError("Missing casepath or case metadata")
        return meta

    def _require_runpath(self) -> Path:
        runpath = self._runcontext.runpath
        if runpath is None:
            raise InvalidMetadataError(
                "Runpath is required for restart resolution but is not set."
            )
        return runpath
