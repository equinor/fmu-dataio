"""Workflow configuration for the Ert POST_SIMULATION workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Self

from fmu.dataio._global_config import (
    RELATIVE_GLOBAL_VARIABLES_PATH,
    load_global_config,
)
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

if TYPE_CHECKING:
    from ert.runpaths import Runpaths as ErtRunpaths


@dataclass(frozen=True)
class PostSimulationConfig:
    """Validated configuration for the POST_SIMULATION workflow."""

    casepath: Path
    global_config: GlobalConfiguration

    @classmethod
    def build_postsim_config(
        cls,
        run_paths: ErtRunpaths,
        casepath: Path,
    ) -> Self:
        """Build the POST_SIMULATION config from the Ert run paths and the case path.

        The post-simulation workflow takes no arguments, so the configuration is
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
        )
