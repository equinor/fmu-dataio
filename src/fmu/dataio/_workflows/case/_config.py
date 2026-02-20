from __future__ import annotations

import argparse
import logging
import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Self

import yaml
from pydantic import ValidationError

from fmu.datamodels.fmu_results import global_configuration
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

if TYPE_CHECKING:
    import ert

logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


def _load_global_config(global_config_path: Path) -> GlobalConfiguration:
    """Load this simulation's global config."""
    logger.debug(f"Loading global config from {global_config_path}")
    with open(global_config_path, encoding="utf-8") as f:
        global_config_dict = yaml.safe_load(f)
    try:
        return global_configuration.GlobalConfiguration.model_validate(
            global_config_dict
        )
    except ValidationError as e:
        global_configuration.validation_error_warning(e)
        raise


@dataclass(frozen=True)
class CaseWorkflowConfig:
    """Validated workflow configuration."""

    casepath: Path
    ert_config_path: Path
    register_on_sumo: bool
    verbosity: str
    global_config: GlobalConfiguration

    @property
    def casename(self) -> str:
        return self.casepath.name

    @classmethod
    def from_presim_workflow(
        cls,
        ensemble: ert.Ensemble,
        run_paths: ert.Runpaths,
        args: argparse.Namespace,
    ) -> Self:
        """Create an instance from Ert workflow arguments."""
        _warn_deprecations(args)

        realization_path = Path(
            run_paths.get_paths(realizations=[0], iteration=ensemble.iteration)[0]
        )
        # (/../casepath/realization-n/iter-n).parent.parent
        casepath = realization_path.parent.parent

        # /../ert/model/
        ert_config_path = Path(run_paths.substitutions["<CONFIG_PATH>"])

        config_path = (
            ert_config_path.parent.parent / "fmuconfig/output/global_variables.yml"
        )
        global_config = _load_global_config(config_path)

        return cls(
            casepath=casepath,
            ert_config_path=ert_config_path,
            register_on_sumo=args.sumo,
            verbosity="WARNING",
            global_config=global_config,
        )


def _warn_deprecations(args: argparse.Namespace) -> None:
    """Warn on deprecated arguments passed to Ert workflow."""

    if args.casepath:
        warnings.warn(
            "The argument 'casepath' is deprecated. It is no "
            "longer used and can safely be removed from WF_CREATE_CASE_METADATA.",
            FutureWarning,
        )
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
            "The argument 'sumo_env' is ignored and can safely be removed.",
            FutureWarning,
        )
        if args.sumo_env != "prod" and os.getenv("SUMO_ENV") is None:
            raise ValueError(
                "Setting sumo environment through argument input is not allowed. "
                "It must be set as an environment variable SUMO_ENV"
            )
