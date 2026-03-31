"""Module to produce a GlobalConfiguration object or dictionary."""

import os
from pathlib import Path
from typing import Any, Final

import pydantic
import yaml

from fmu.dataio._logging import null_logger
from fmu.dataio.exceptions import ValidationError
from fmu.datamodels.fmu_results.global_configuration import (
    GlobalConfiguration,
    validation_error_warning,
)

GLOBAL_CONFIG_ENV_VAR: Final[str] = "FMU_GLOBAL_CONFIG"
GLOBAL_VARIABLES_PATH: Final[Path] = Path("../../fmuconfig/output/global_variables.yml")

logger: Final = null_logger(__name__)


def _build_global_configuration(
    config_dict: dict[str, Any], standard_result: bool = False
) -> GlobalConfiguration:
    try:
        return GlobalConfiguration.model_validate(config_dict)
    except pydantic.ValidationError as err:
        error_message = "Global variables does not contain valid masterdata.\n"

        if standard_result:
            error_message += (
                "When exporting standard results it is required to have a valid "
                "config.\n"
            )
        else:
            validation_error_warning(err)

        if "masterdata" not in config_dict:
            error_message += (
                "Follow the 'Getting started' steps to do necessary preparations: "
                "https://fmu-dataio.readthedocs.io/en/latest/getting_started.html "
            )

        raise ValidationError(
            f"{error_message}\nDetailed information: \n{err}"
        ) from err


def load_global_config_from_global_variables(
    config_path: Path, standard_result: bool = False
) -> GlobalConfiguration:
    """Load the global config from standard path and return validated config."""
    logger.info(f"Loading global config from file via {config_path}")

    if not config_path.exists():
        raise FileNotFoundError(
            f"Could not find the global variables file at {config_path}."
        )

    with config_path.open(encoding="utf-8") as f:
        try:
            config_dict = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(
                f"Unable to load config from {config_path}. Error: {e}"
            ) from e

    return _build_global_configuration(config_dict, standard_result)


def load_global_config_from_env(
    env_var: str = GLOBAL_CONFIG_ENV_VAR,
) -> dict[str, Any] | None:
    """Get the config from environment variable.

    This function should only be used when fetching from an environment variable is
    explicitly desired. This is not meant as a general way to provide global config.
    """
    logger.info(f"Loading global config from file via environment {env_var}")

    try:
        maybe_cfg_path = os.getenv(env_var, None)
        if not maybe_cfg_path:
            return None

        with Path(maybe_cfg_path).open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    except Exception as e:
        raise ValueError(
            "Unable to load config from path in environment variable "
            f"{env_var}={maybe_cfg_path}. The environment variable {env_var} must "
            f"point to a valid YAML file. Error: {e}"
        ) from e


def load_global_config(
    config_path: Path = GLOBAL_VARIABLES_PATH,
    standard_result: bool = False,
) -> GlobalConfiguration:
    """Load the global config from standard path and return validated config.

    Args:
        config_path: The path to global_varibles.yml
        standard_result: If True, modifies validation error message

    Raises:
        FileNotFoundError: If .fmu/ doesn't exist _and_ global_variables.yml doesn't
            exist

    Returns:
        Validated GlobalConfiguration object
    """
    # TODO: Check .fmu
    return load_global_config_from_global_variables(config_path, standard_result)
