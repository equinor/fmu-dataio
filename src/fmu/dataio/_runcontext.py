from __future__ import annotations

import os
import warnings
from enum import Enum, auto
from pathlib import Path
from typing import Final

from typing_extensions import override  # Remove when Python 3.11 dropped

from fmu.config import utilities as ut
from fmu.dataio._definitions import ERT_RELATIVE_CASE_METADATA_FILE, RMSExecutionMode
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import casepath_has_metadata
from fmu.datamodels.fmu_results.enums import FMUContext
from fmu.datamodels.fmu_results.fmu_results import CaseMetadata

logger: Final = null_logger(__name__)


class RunContext:
    """
    Provides information about the current run context and establishes key paths.

    This class holds information about where the code is running, and establishes
    important paths such as `runpath`, `casepath`, and the `exportroot`.
    It also validates the casepath and loads the case metadata if available.
    """

    def __init__(
        self,
        casepath_proposed: Path | None = None,
        fmu_context: FMUContext | None = None,
    ) -> None:
        logger.debug("Initialize RunContext...")

        # TODO: in the future fmu_context should always be set by the environment
        self._fmu_context = fmu_context or self.fmu_context_from_env
        self._runpath = get_runpath_from_env()
        self._casepath = self._establish_casepath(casepath_proposed)
        self._case_metadata = self._load_case_meta() if self._casepath else None
        self._exportroot = self._establish_exportroot()

        logger.debug("Runpath is %s", self._runpath)
        logger.debug("Casepath is %s", self._casepath)
        logger.debug("Export root is %s", self._exportroot)

    @property
    def inside_fmu(self) -> bool:
        """Check if the run context is inside a ERT run."""
        return self.fmu_context_from_env is not None

    @property
    def inside_rms(self) -> bool:
        """Check if the run context is inside RMS."""
        return self.rms_context is not None

    @property
    def fmu_context(self) -> FMUContext | None:
        """The FMU context"""
        return self._fmu_context

    @property
    def fmu_context_from_env(self) -> FMUContext | None:
        """The FMU context from the environment"""
        return get_fmu_context_from_environment()

    @property
    def rms_context(self) -> RMSExecutionMode | None:
        """The RMS execution mode (interactive/batch)"""
        return get_rms_exec_mode()

    @property
    def exportroot(self) -> Path:
        """The export root path"""
        return self._exportroot

    @property
    def casepath(self) -> Path | None:
        """The path to the case metadata."""
        return self._casepath

    @property
    def case_metadata(self) -> CaseMetadata | None:
        """The case metadata."""
        return self._case_metadata

    @property
    def runpath(self) -> Path | None:
        """The runpath. Will be None if not in a realization context."""
        return self._runpath

    def _establish_exportroot(self) -> Path:
        """
        Establish the exportroot. The exportroot is the folder that together with
        the share location for a file makes up the absolute export path for an object:
        absolute_path = exportroot / objdata.share_path

        The exportroot is dependent on whether this is run in a FMU context via ERT and
        whether it's being run from inside or outside RMS.

        1: Running ERT in realization context -> equal to the runpath
        2: Running ERT in case context -> equal to the casepath
        3: Running RMS interactively -> exportroot/rms/model
        4: When none of the above conditions apply -> equal to present working directory
        """
        logger.info("Establish exportroot")
        logger.debug("RMS execution mode from environment: %s", self.rms_context)

        if self.runpath and self.fmu_context == FMUContext.realization:
            logger.info("Run from ERT realization context")
            return self.runpath

        if self.casepath:
            logger.info("Run from ERT case context")
            return self.casepath.absolute()

        pwd = Path.cwd()

        if self.rms_context == RMSExecutionMode.interactive:
            logger.info("Run from inside RMS interactive")
            return pwd.parent.parent.absolute().resolve()

        logger.info(
            "Running outside FMU context or casepath with valid case metadata "
            "could not be detected, will use pwd as roothpath."
        )
        return pwd

    def _establish_casepath(self, casepath_proposed: Path | None) -> Path | None:
        """If casepath is not given, then try update _casepath (if in realization).

        There is also a validation here that casepath contains case metadata, and if not
        then a second guess is attempted, looking at `parent` insted of `parent.parent`
        is case of missing ensemble folder.
        """
        if not self.inside_fmu:
            return None

        if casepath_proposed:
            if casepath_has_metadata(casepath_proposed):
                return casepath_proposed
            warnings.warn(
                "Could not detect metadata for the proposed casepath "
                f"{casepath_proposed}. Will try to detect from runpath."
            )
        if self.runpath:
            if casepath_has_metadata(self.runpath.parent.parent):
                return self.runpath.parent.parent

            if casepath_has_metadata(self.runpath.parent):
                return self.runpath.parent

        logger.debug("No case metadata, issue a warning!")
        warnings.warn(
            "Could not auto detect the case metadata, please provide the "
            "'casepath' as input. Metadata will be empty!",
            UserWarning,
        )
        return None

    def _load_case_meta(self) -> CaseMetadata:
        """Parse and validate the CASE metadata."""
        logger.debug("Loading case metadata file and return pydantic case model")
        assert self.casepath is not None
        case_metafile = self.casepath / ERT_RELATIVE_CASE_METADATA_FILE
        return CaseMetadata.model_validate(
            ut.yaml_load(case_metafile, loader="standard")
        )


def get_rms_exec_mode() -> RMSExecutionMode | None:
    """
    Get the RMS GUI execution mode from the environment.
    The RUNRMS_EXEC_MODE variable is set when the RMS GUI is started by runrms,
    and holds information about the execution mode (interactive or batch).
    """
    rms_exec_mode = os.environ.get("RUNRMS_EXEC_MODE")
    return RMSExecutionMode(rms_exec_mode) if rms_exec_mode else None


def get_fmu_context_from_environment() -> FMUContext | None:
    """return the ERT run context as an FMUContext"""
    if FmuEnv.RUNPATH.value:
        return FMUContext.realization
    if FmuEnv.EXPERIMENT_ID.value:
        return FMUContext.case
    return None


def get_runpath_from_env() -> Path | None:
    """get runpath as an absolute path if detected from the enviroment"""
    return Path(runpath).resolve() if (runpath := FmuEnv.RUNPATH.value) else None


class FmuEnv(Enum):
    EXPERIMENT_ID = auto()
    ENSEMBLE_ID = auto()
    SIMULATION_MODE = auto()
    REALIZATION_NUMBER = auto()
    ITERATION_NUMBER = auto()
    RUNPATH = auto()

    @property
    @override
    def value(self) -> str | None:  # type: ignore[override]
        # Fetch the environment variable; name of the enum member prefixed with _ERT_
        return os.getenv(f"_ERT_{self.name}")
