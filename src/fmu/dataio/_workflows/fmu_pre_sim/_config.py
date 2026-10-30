"""Workflow configuration for the Ert PRE_SIMULATION workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Self

from fmu.dataio._global_config import (
    RELATIVE_GLOBAL_VARIABLES_PATH,
    load_global_config,
)
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.settings import ProjectFMUDirectory

if TYPE_CHECKING:
    from ert.runpaths import Runpaths as ErtRunpaths


@dataclass(frozen=True)
class PreSimulationConfig:
    """Validated configuration for the PRE_SIMULATION workflow."""

    casepath: Path
    global_config: GlobalConfiguration
    fmu_dir: ProjectFMUDirectory | None

    @property
    def casename(self) -> str:
        return self.casepath.name

    @classmethod
    def build_presim_config(
        cls,
        run_paths: ErtRunpaths,
        casepath: Path,
        fmu_dir: ProjectFMUDirectory | None,
    ) -> Self:
        """Build the PRE_SIMULATION config from the Ert run paths and the case path.

        The pre-simulation workflow takes no arguments, so the configuration is
        resolved entirely from the Ert run paths and the given case path.
        """
        # /../ert/model/
        config_path = (
            Path(run_paths.substitutions["<CONFIG_PATH>"])
            / RELATIVE_GLOBAL_VARIABLES_PATH
        )
        return cls(
            casepath=casepath,
            global_config=load_global_config(config_path),
            fmu_dir=fmu_dir,
        )
