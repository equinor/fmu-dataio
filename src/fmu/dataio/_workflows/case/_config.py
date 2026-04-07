from __future__ import annotations

import argparse
import logging
import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Self

from fmu.dataio._global_config import RELATIVE_GLOBAL_VARIABLES_PATH, load_global_config
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.settings import ProjectFMUDirectory

if TYPE_CHECKING:
    import ert

logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


@dataclass(frozen=True)
class CaseWorkflowConfig:
    """Validated workflow configuration."""

    casepath: Path
    ert_config_path: Path
    register_on_sumo: bool
    verbosity: str
    global_config: GlobalConfiguration
    global_config_path: Path
    fmu_dir: ProjectFMUDirectory | None

    def __post_init__(self) -> None:
        """Run validation."""
        self.validate()

    @property
    def casename(self) -> str:
        return self.casepath.name

    def validate(self) -> None:
        casepath_str = str(self.casepath)
        if not self.casepath.is_absolute():
            if casepath_str.startswith("<") and casepath_str.endswith(">"):
                raise ValueError(
                    f"Ert variable for case path is not defined: {self.casepath}"
                )
            raise ValueError(
                f"'casepath' must be an absolute path. Got: {self.casepath}"
            )

    @classmethod
    def from_presim_workflow(
        cls,
        run_paths: ert.Runpaths,
        args: argparse.Namespace,
        fmu_dir: ProjectFMUDirectory | None = None,
    ) -> Self:
        """Create an instance from Ert workflow arguments."""
        _warn_deprecations(args)

        # /../ert/model/
        ert_config_path = Path(run_paths.substitutions["<CONFIG_PATH>"])
        config_path = ert_config_path / RELATIVE_GLOBAL_VARIABLES_PATH

        global_config = load_global_config(config_path)

        return cls(
            casepath=args.casepath,
            ert_config_path=ert_config_path,
            register_on_sumo=args.sumo,
            verbosity="WARNING",
            global_config=global_config,
            global_config_path=config_path,
            fmu_dir=fmu_dir,
        )


def _warn_deprecations(args: argparse.Namespace) -> None:
    """Warn on deprecated arguments passed to Ert workflow."""

    if args.ert_config_path:
        warnings.warn(
            "The argument 'ert_config_path' is deprecated. It is no "
            "longer used and can safely be removed from WF_CREATE_CASE_METADATA.",
            FutureWarning,
        )
    if args.ert_casename:
        warnings.warn(
            "The argument 'ert_casename' is deprecated. It is no "
            "longer used and can safely be removed from WF_CREATE_CASE_METADATA.",
            FutureWarning,
        )
    if args.ert_username:
        warnings.warn(
            "The argument 'ert_username' is deprecated. It is no "
            "longer used and can safely be removed from WF_CREATE_CASE_METADATA.",
            FutureWarning,
        )
    if args.global_variables_path:
        warnings.warn(
            "The argument '--global_variables_path' is deprecated. It is no "
            "longer used and can safely be removed from WF_CREATE_CASE_METADATA.",
            FutureWarning,
        )
    if args.verbosity:
        warnings.warn(
            "The argument '--verbosity' is deprecated. It is no "
            "longer used and can safely be removed from WF_CREATE_CASE_METADATA.",
            FutureWarning,
        )
    if args.sumo_env:
        warnings.warn(
            "The argument '--sumo_env' is deprecated. It is no "
            "longer used and can safely be removed from WF_CREATE_CASE_METADATA.",
            FutureWarning,
        )
        if args.sumo_env != "prod" and os.getenv("SUMO_ENV") is None:
            raise ValueError(
                "Setting sumo environment through argument input is not allowed. "
                "It must be set as an environment variable SUMO_ENV"
            )
