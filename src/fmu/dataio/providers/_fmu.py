"""Module for DataIO FmuProvider

The FmuProvider will from the environment and eventually API's detect valid
fields to the FMU data block.

Note that FMU may potentially have different providers, e.g. ERT versions
or it can detect that no FMU providers are present (e.g. just ran from RMS interactive)

Note that establishing the FMU case metadata for a run, is currently *not* done
here; this is done by code in the InitializeCase class.

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
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Final, Optional, Union
from warnings import warn

from fmu.config import utilities as ut
from fmu.dataio import _utils
from fmu.dataio._definitions import FmuContext
from fmu.dataio._logging import null_logger
from fmu.dataio.datastructure._internal import internal
from fmu.dataio.datastructure.meta import meta
from fmu.dataio.exceptions import InvalidMetadataError

from ._base import Provider

if TYPE_CHECKING:
    from uuid import UUID

# case metadata relative to casepath
ERT_RELATIVE_CASE_METADATA_FILE: Final = "share/metadata/fmu_case.yml"
RESTART_PATH_ENVNAME: Final = "RESTART_FROM_PATH"

logger: Final = null_logger(__name__)


def get_fmu_context_from_environment() -> FmuContext:
    """return the ERT run context as an FmuContext"""
    if FmuEnv.RUNPATH.value:
        return FmuContext.REALIZATION
    if FmuEnv.EXPERIMENT_ID.value:
        return FmuContext.CASE
    return FmuContext.NON_FMU


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
        fmu_context: The FMU context this is ran in; see FmuContext enum class
        casepath_proposed: Proposed casepath. Needed if FmuContext is CASE
        workflow: Descriptive work flow info
    """

    model: dict | None = None
    fmu_context: FmuContext = FmuContext.REALIZATION
    casepath_proposed: Optional[Path] = None
    workflow: Optional[Union[str, dict[str, str]]] = None

    # private properties for this class
    _runpath: Optional[Path] = field(default_factory=Path, init=False)
    _casepath: Optional[Path] = field(default_factory=Path, init=False)
    _iter_name: str = field(default="", init=False)
    _iter_id: int = field(default=0, init=False)
    _real_name: str = field(default="", init=False)
    _real_id: int = field(default=0, init=False)
    _case_name: str = field(default="", init=False)

    def __post_init__(self) -> None:
        logger.info("Initialize %s...", self.__class__)
        logger.debug("Case path is initially <%s>...", self.casepath_proposed)

        self._runpath = self._get_runpath_from_env()
        logger.debug("Runpath is %s", self._runpath)

        self._real_id = (
            int(iter_num) if (iter_num := FmuEnv.REALIZATION_NUMBER.value) else 0
        )
        self._iter_id = (
            int(real_num) if (real_num := FmuEnv.ITERATION_NUMBER.value) else 0
        )

        self._casepath = self._validate_and_establish_casepath()
        if self._casepath:
            self._case_name = self._casepath.name

            if self._runpath and self.fmu_context != FmuContext.CASE:
                missing_iter_folder = self._casepath == self._runpath.parent
                if not missing_iter_folder:
                    logger.debug("Iteration folder found")
                    self._iter_name = self._runpath.name
                    self._real_name = self._runpath.parent.name
                else:
                    logger.debug("No iteration folder found, using default name iter-0")
                    self._iter_name = "iter-0"
                    self._real_name = self._runpath.name

                logger.debug("Found iter name from runpath: %s", self._iter_name)
                logger.debug("Found real name from runpath: %s", self._real_name)

    def get_iter_name(self) -> str:
        """Return the iter_name, e.g. 'iter-3' or 'pred'."""
        return self._iter_name

    def get_real_name(self) -> str:
        """Return the real_name, e.g. 'realization-23'."""
        return self._real_name

    def get_casepath(self) -> Path | None:
        """Return updated casepath in a FMU run, will be updated if initially blank."""
        return self._casepath

    def get_runpath(self) -> Path | None:
        """Return runpath for a FMU run."""
        return self._runpath

    def get_metadata(self) -> internal.FMUClassMetaData:
        """Construct the metadata FMU block for an ERT forward job."""
        logger.debug("Generate ERT metadata...")

        if self._casepath is None or self.model is None:
            raise InvalidMetadataError("Missing casepath or model description")

        case_meta = self._get_fmucase_meta()

        if self.fmu_context != FmuContext.REALIZATION:
            return internal.FMUClassMetaData(
                case=case_meta,
                context=self._get_fmucontext_meta(),
                model=self._get_fmumodel_meta(),
                workflow=self._get_workflow_meta() if self.workflow else None,
            )

        iter_uuid, real_uuid = self._get_iteration_and_real_uuid(case_meta.uuid)
        return internal.FMUClassMetaData(
            case=case_meta,
            context=self._get_fmucontext_meta(),
            model=self._get_fmumodel_meta(),
            workflow=self._get_workflow_meta() if self.workflow else None,
            iteration=self._get_iteration_meta(iter_uuid),
            realization=self._get_realization_meta(real_uuid),
        )

    @staticmethod
    def _get_runpath_from_env() -> Path | None:
        """get runpath as an absolute path if detected from the enviroment"""
        return Path(runpath).resolve() if (runpath := FmuEnv.RUNPATH.value) else None

    def _validate_and_establish_casepath(self) -> Path | None:
        """If casepath is not given, then try update _casepath (if in realization).

        There is also a validation here that casepath contains case metadata, and if not
        then a second guess is attempted, looking at `parent` insted of `parent.parent`
        is case of missing iteration folder.
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

        if self.fmu_context == FmuContext.CASE:
            # TODO: Change to ValueError when no longer kwargs are accepted in export()
            warn("Could not auto detect the casepath, please provide it as input.")

        logger.debug("No case metadata, issue a warning!")
        warn("Case metadata does not exist, metadata will be empty!", UserWarning)
        return None

    def _get_restart_data_uuid(self) -> UUID | None:
        """Load restart_from information"""
        assert self._runpath is not None
        logger.debug("Detected a restart run from environment variable")
        restart_path = self._runpath / os.environ[RESTART_PATH_ENVNAME]
        restart_case_metafile = (
            restart_path.parent.parent / ERT_RELATIVE_CASE_METADATA_FILE
        ).resolve()

        if not restart_case_metafile.exists():
            warn(
                f"{RESTART_PATH_ENVNAME} environment variable is set to "
                f"{os.environ[RESTART_PATH_ENVNAME]} which is invalid. Metadata "
                "restart_from will remain empty.",
                UserWarning,
            )
            return None

        restart_metadata = internal.CaseSchema.model_validate(
            ut.yaml_load(restart_case_metafile, loader="standard")
        )
        return _utils.uuid_from_string(
            f"{restart_metadata.fmu.case.uuid}{restart_path.name}"
        )

    def _get_ert_parameters(self) -> meta.Parameters | None:
        logger.debug("Read ERT parameters")
        assert self._runpath is not None
        parameters_file = self._runpath / "parameters.txt"
        if not parameters_file.exists():
            warn("The parameters.txt file was not found", UserWarning)
            return None

        params = _utils.read_parameters_txt(parameters_file)
        logger.debug("parameters.txt parsed.")
        # BUG(?): value can contain Nones, loop in fn. below
        # does contains check, will fail.
        return meta.Parameters(root=_utils.nested_parameters_dict(params))  # type: ignore

    def _get_iteration_and_real_uuid(self, case_uuid: UUID) -> tuple[UUID, UUID]:
        iter_uuid = _utils.uuid_from_string(f"{case_uuid}{self._iter_name}")
        real_uuid = _utils.uuid_from_string(f"{case_uuid}{iter_uuid}{self._real_id}")
        return iter_uuid, real_uuid

    def _get_fmucase_meta(self) -> meta.FMUCase:
        """Parse and validate the CASE metadata."""
        logger.debug("Loading case metadata file and return pydantic case model")
        assert self._casepath is not None
        case_metafile = self._casepath / ERT_RELATIVE_CASE_METADATA_FILE
        case_meta = internal.CaseSchema.model_validate(
            ut.yaml_load(case_metafile, loader="standard")
        )
        return case_meta.fmu.case

    def _get_realization_meta(self, real_uuid: UUID) -> meta.Realization:
        return meta.Realization(
            id=self._real_id,
            name=self._real_name,
            parameters=self._get_ert_parameters(),
            uuid=real_uuid,
        )

    def _get_iteration_meta(self, iter_uuid: UUID) -> meta.Iteration:
        return meta.Iteration(
            id=self._iter_id,
            name=self._iter_name,
            uuid=iter_uuid,
            restart_from=self._get_restart_data_uuid()
            if os.getenv(RESTART_PATH_ENVNAME)
            else None,
        )

    def _get_fmucontext_meta(self) -> internal.Context:
        return internal.Context(stage=self.fmu_context)

    def _get_fmumodel_meta(self) -> meta.FMUModel:
        return meta.FMUModel.model_validate(self.model)

    def _get_workflow_meta(self) -> meta.Workflow:
        assert self.workflow is not None
        if isinstance(self.workflow, dict):
            return meta.Workflow.model_validate(self.workflow)
        return meta.Workflow(reference=self.workflow)
