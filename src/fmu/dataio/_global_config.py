"""Module to produce a GlobalConfiguration object or dictionary."""

from pathlib import Path
from typing import Any, Final

import pydantic
import yaml

from fmu.dataio._logging import null_logger
from fmu.dataio.exceptions import ValidationError
from fmu.datamodels.fmu_results.global_configuration import (
    Access,
    GlobalConfiguration,
    validation_error_warning,
)
from fmu.settings import find_nearest_fmu_directory

RUNPATH_GLOBAL_VARIABLES_PATH: Final[Path] = Path(
    "fmuconfig/output/global_variables.yml"
)
RELATIVE_GLOBAL_VARIABLES_PATH: Final[Path] = (
    Path("../..") / RUNPATH_GLOBAL_VARIABLES_PATH
)

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

    if not config_path.is_file():
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


def _resolve_global_config_path(config_path: Path | None) -> Path:
    """Resolves a global variables configuration path.

    Will fall back to other possible locations if None or passed/known paths cannot be
    found.

    Order:
        1. Provided path
        2. Relative to runpath
        3. Relative to application (RMS, Ert, ...)
    """
    # If it exists, no need to fall back
    if config_path is not None and config_path.is_file():
        return config_path.resolve()

    if RUNPATH_GLOBAL_VARIABLES_PATH.is_file():
        return RUNPATH_GLOBAL_VARIABLES_PATH.resolve()

    if RELATIVE_GLOBAL_VARIABLES_PATH.is_file():
        return RELATIVE_GLOBAL_VARIABLES_PATH.resolve()

    raise FileNotFoundError(
        f"Could not find the global variables file at {config_path}, "
        f"{RUNPATH_GLOBAL_VARIABLES_PATH}, or {RELATIVE_GLOBAL_VARIABLES_PATH}."
    )


def load_global_config_from_fmu_settings() -> GlobalConfiguration | None:
    """Loads and validates a global configuration from .fmu if one can be found.

    It is possible (though unlikely) a valid configuration cannot be constructed from
    the data stored in .fmu.

    Returns:
        Valid GlobalConfiguration object, or None if:
            - .fmu/ cannot be found
            - data in .fmu/ is invalid or cannot be loaded
            - data in .fmu/ does not validate against current GlobalConfiguration model
    """
    try:
        fmu_dir = find_nearest_fmu_directory()
    except FileNotFoundError:
        logger.info("No .fmu/ directory found to load global configuration from.")
        return None

    config = fmu_dir.config.load()
    if config.masterdata is None or config.access is None or config.model is None:
        return None

    try:
        cfg_access = Access.model_validate(config.access.model_dump(mode="json"))
    except pydantic.ValidationError as err:
        logger.warning(
            "Could not build valid global configuration access from .fmu/. "
            f".fmu directory: {fmu_dir.path}, error: {err}"
        )
        return None

    try:
        stratigraphy = fmu_dir._mappings.build_global_config_stratigraphy()
    except pydantic.ValidationError as err:
        logger.warning(
            "Could not build valid global configuration stratigraphy from .fmu/. "
            f".fmu directory: {fmu_dir.path}, error: {err}"
        )
        return None

    try:
        # TODO: Use _build_global_configuration if/when .fmu/ is required.
        return GlobalConfiguration(
            masterdata=config.masterdata,
            access=cfg_access,
            model=config.model,
            stratigraphy=stratigraphy,
        )
    except pydantic.ValidationError as err:
        logger.warning(
            "Could not build valid global configuration from .fmu/. "
            f".fmu directory: {fmu_dir.path}, error: {err}"
        )
    return None


def load_global_config(
    config_path: Path | None = None, standard_result: bool = False
) -> GlobalConfiguration:
    """Load the global config from standard path and return validated config.

    Args:
        config_path: The path to global_variables.yml
        standard_result: If True, modifies validation error message

    Raises:
        FileNotFoundError: If .fmu/ doesn't exist _and_ global_variables.yml doesn't
            exist

    Returns:
        Validated GlobalConfiguration object
    """
    if fmu_settings_global_config := load_global_config_from_fmu_settings():
        return fmu_settings_global_config

    resolved_config_path = _resolve_global_config_path(config_path)
    return load_global_config_from_global_variables(
        resolved_config_path, standard_result
    )
