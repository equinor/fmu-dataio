from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Self

from fmu.config import utilities as ut
from fmu.dataio._definitions import ERT_RELATIVE_CASE_METADATA_FILE, RMSExecutionMode
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import casepath_has_metadata
from fmu.datamodels.fmu_results.enums import FMUContext
from fmu.datamodels.fmu_results.fmu_results import CaseMetadata

logger: Final = null_logger(__name__)


@dataclass(frozen=True)
class FMUPaths:
    """Immutable container for export paths.

    Path hierarchy:
        casepath/
        ├── share/
        │   ├── metadata/fmu_case.yml
        │   └── ensemble/                   # ensemble level exports
        │       ├── iter-0/
        │       │   └── share/results/...
        │       ├── iter-1/
        │       └── pred-dg3/
        ├── realization-0/
        │   ├── iter-0/                     # runpath (realization exports)
        │   │   └── share/results/...
        │   ├── iter-1/
        │   └── pred-dg3/                   # prediction ensemble
        └── realization-1/

    The paths stored here are export roots, meaning the share/results/... part is
    appended elsewhere.
    """

    casepath: Path | None = None  # casepath/
    ensemble_path: Path | None = None  # casepath/share/ensemble/iter-N
    runpath: Path | None = None  # casepath/realization-N/iter-N
    ensemble_name: str | None = None  # iter-N or pred-dg3
    realization_name: str | None = None  # realization-N

    def export_root_for_context(self, context: FMUContext) -> Path | None:
        """Get the export root that corresponds to the provided FMU context."""
        mapping = {
            FMUContext.realization: self.runpath,
            FMUContext.ensemble: self.ensemble_path,
            FMUContext.case: self.casepath,
        }
        return mapping.get(context)


@dataclass(frozen=True)
class FMUEnvironment:
    """Immutable snapshot of FMU/Ert provided environment variables."""

    experiment_id: str | None
    ensemble_id: str | None
    simulation_mode: str | None
    realization_number: int | None
    iteration_number: int | None
    runpath: Path | None
    rms_exec_mode: RMSExecutionMode | None

    @property
    def fmu_context(self) -> FMUContext | None:
        """Determine the FMU context from environment, if possible.

        Note that we cannot reliably determine an 'ensemble' context unless running in a
        PRE_EXPERIMENT mode, which we do not currently do. Hence this is only useful to
        determine case or object exports rather than ensemble level experts."""
        if self.runpath:
            return FMUContext.realization
        if self.experiment_id:
            return FMUContext.case
        return None

    @staticmethod
    def get_ert_env(name: str) -> str | None:
        return os.getenv(f"_ERT_{name}")

    @classmethod
    def from_env(cls) -> Self:
        """Create from the current enviroement."""

        runpath_str = cls.get_ert_env("RUNPATH")
        real_num = cls.get_ert_env("REALIZATION_NUMBER")
        iter_num = cls.get_ert_env("ITERATION_NUMBER")

        rms_exec_mode = os.getenv("RUNRMS_EXEC_MODE")

        return cls(
            experiment_id=cls.get_ert_env("EXPERIMENT_ID"),
            ensemble_id=cls.get_ert_env("ENSEMBLE_ID"),
            simulation_mode=cls.get_ert_env("SIMULATION_MODE"),
            realization_number=int(real_num) if real_num else None,
            iteration_number=int(iter_num) if iter_num else None,
            runpath=Path(runpath_str).resolve() if runpath_str else None,
            rms_exec_mode=RMSExecutionMode(rms_exec_mode) if rms_exec_mode else None,
        )


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
        ensemble_name: str | None = None,
    ) -> None:
        self._env = FMUEnvironment.from_env()
        self._fmu_context = fmu_context or self._env.fmu_context
        self._ensemble_name_override = ensemble_name
        self._paths = self._resolve_paths(casepath_proposed)
        self._case_metadata = self._load_case_metadata()

    @property
    def env(self) -> FMUEnvironment:
        """Access the raw environment variables."""
        return self._env

    @property
    def inside_fmu(self) -> bool:
        """Check if the run context is inside a ERT run."""
        return self._env.fmu_context is not None

    @property
    def fmu_context(self) -> FMUContext | None:
        """The FMU context"""
        return self._fmu_context

    @property
    def paths(self) -> FMUPaths:
        """All resolved paths."""
        return self._paths

    @property
    def casepath(self) -> Path | None:
        """The path to the case."""
        return self._paths.casepath

    @property
    def runpath(self) -> Path | None:
        """The runpath. Will be None if not in a realization context."""
        return self._paths.runpath

    @property
    def ensemble_path(self) -> Path | None:
        """The export path for ensemble-level data.

        This is casepath/share/ensemble/iter-N, where ensemble-level data are exported.
        """
        return self._paths.ensemble_path

    @property
    def inside_rms(self) -> bool:
        """Check if the run context is inside RMS."""
        return self._env.rms_exec_mode is not None

    @property
    def rms_context(self) -> RMSExecutionMode | None:
        """The RMS execution mode (interactive/batch)"""
        return self._env.rms_exec_mode

    @property
    def exportroot(self) -> Path:
        """The root path for exports based on current context.

        The exportroot is the folder that together with the share location for a file
        makes up the absolute export path for an object: absolute_path = exportroot /
        objdata.share_path

        The exportroot is dependent on whether this is run in a FMU context via ERT and
        whether it's being run from inside or outside RMS.

        1: Running ERT in realization context -> equal to the runpath
        2: Running ERT in case context -> equal to the casepath
        3: Running RMS interactively -> exportroot/rms/model
        4: When none of the above conditions apply -> equal to present working directory
        """
        if self._fmu_context:
            root = self._paths.export_root_for_context(self._fmu_context)
            if root:
                return root

        if self._env.rms_exec_mode == RMSExecutionMode.interactive:
            return Path.cwd().parent.parent.resolve()
        return Path.cwd()

    @property
    def case_metadata(self) -> CaseMetadata | None:
        """The case metadata."""
        return self._case_metadata

    def _resolve_paths(self, casepath_input: Path | None) -> FMUPaths:
        """Resolve all FMU paths from environment and/or proposed casepath."""
        if not self.inside_fmu:
            return FMUPaths()

        runpath = self._env.runpath
        casepath = self._find_valid_casepath(casepath_input, runpath)

        ensemble_path = None
        ensemble_name = None
        realization_name = None

        if casepath and runpath:
            ensemble_name, realization_name = (
                self._extract_ensemble_and_realization_name(casepath, runpath)
            )

        if self._ensemble_name_override:
            ensemble_name = self._ensemble_name_override

        if casepath and ensemble_name:
            ensemble_path = casepath / "share" / "ensemble" / ensemble_name

        return FMUPaths(
            casepath=casepath,
            ensemble_path=ensemble_path,
            runpath=runpath,
            ensemble_name=ensemble_name,
            realization_name=realization_name,
        )

    def _extract_ensemble_and_realization_name(
        self, casepath: Path, runpath: Path
    ) -> tuple[str | None, str | None]:
        """Extract ensemble and realization name from the runpath.

        Handles two scenarios:
            casepath/realization-N/iter-N    -> ("iter-N", "realization-N")
            casepath/realization-N/          -> ("iter-0", "realization-N")
        """
        try:
            rel_path = runpath.relative_to(casepath)
        except ValueError:
            return (None, None)

        parts = rel_path.parts
        if len(parts) >= 2:
            realization_name = parts[0]
            ensemble_name = parts[1]
            return (ensemble_name, realization_name)

        if len(parts) == 1:
            realization_name = parts[0]
            ensemble_name = "iter-0"
            return (ensemble_name, realization_name)

        return (None, None)

    def _find_valid_casepath(
        self,
        proposed: Path | None,
        runpath: Path | None,
    ) -> Path | None:
        """Find a valid casepath with metadata."""
        candidates = [
            proposed,
            runpath.parent.parent if runpath else None,  # Standard: case/real/iter
            runpath.parent if runpath else None,  # No ensemble folder (case/real)
        ]
        for candidate in candidates:
            if candidate and casepath_has_metadata(candidate):
                return candidate

        warnings.warn(
            "Could not detect the case metadata. Provide 'casepath' as input. "
            "No metadata will be produced without it.",
            UserWarning,
        )
        return None

    def _load_case_metadata(self) -> CaseMetadata | None:
        """Parse and validate the CASE metadata."""
        logger.debug("Loading case metadata file and return pydantic case model")

        if not self.casepath:
            return None

        case_metafile = self.casepath / ERT_RELATIVE_CASE_METADATA_FILE
        return CaseMetadata.model_validate(
            ut.yaml_load(case_metafile, loader="standard")
        )
