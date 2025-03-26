from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pydantic
import xtgeo
from packaging.version import parse as versionparse

from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.global_configuration import GlobalConfiguration
from fmu.dataio._utils import load_config_from_path
from fmu.dataio.exceptions import ValidationError

from ._conditional_rms_imports import import_rms_package

if TYPE_CHECKING:
    from packaging.version import Version


logger: Final = null_logger(__name__)


rmsapi, _ = import_rms_package()


CONFIG_PATH = Path("../../fmuconfig/output/global_variables.yml")

RMS_API_PROJECT_MAPPING = {
    "1.10": "14.2",
    "1.9": "14.1",
    "1.7": "13.1",
}


def _get_rmsapi_version() -> Version:
    """Get the rmsapi version"""
    return versionparse(rmsapi.__version__)


def check_rmsapi_version(minimum_version: str) -> None:
    """Check if we are working in a RMS API, and also check RMS versions"""
    logger.debug("Check API version...")
    if minimum_version not in RMS_API_PROJECT_MAPPING:
        raise ValueError(
            "The minimum version has not been mapped to a RMS project "
            "version, it should be added to the 'RMS_API_PROJECT_MAPPING'"
        )
    if _get_rmsapi_version() < versionparse(minimum_version):
        raise RuntimeError(
            f"You need at least API version {minimum_version} "
            f"(RMS {RMS_API_PROJECT_MAPPING[minimum_version]}) to use this function."
        )
    logger.debug("Check API version... DONE")


def get_rms_project_units(project: Any) -> str:
    """See if the RMS project is defined in metric or feet."""

    units = project.project_units
    logger.debug("Units are %s", units)
    return str(units)


def load_global_config() -> GlobalConfiguration:
    """Load the global config from standard path and return validated config."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Could not detect the global config file at standard "
            f"location: {CONFIG_PATH}."
        )
    config = load_config_from_path(CONFIG_PATH)
    return validate_global_config(config)


def validate_global_config(config: dict[str, Any]) -> GlobalConfiguration:
    """Validate the input config using pydantic, raise error if invalid."""
    try:
        return GlobalConfiguration.model_validate(config)
    except pydantic.ValidationError as err:
        error_message = (
            "When exporting standard_results it is required to have a valid config.\n"
        )
        if "masterdata" not in config:
            error_message += (
                "Follow the 'Getting started' steps to do necessary preparations: "
                "https://fmu-dataio.readthedocs.io/en/latest/preparations.html "
            )

        raise ValidationError(
            f"{error_message}\nDetailed information: \n{err}"
        ) from err


def validate_horizon_folder(project: Any, horizon_folder: str) -> None:
    """
    Check if a horizon folder exist inside the project and that data exists for some
    horizons within the folder. Otherwise raise errors.
    """
    if horizon_folder not in project.horizons.representations:
        raise ValueError(
            f"The provided horizon folder name {horizon_folder} "
            "does not exist inside RMS."
        )

    if all(horizon[horizon_folder].is_empty() for horizon in project.horizons):
        raise RuntimeError(
            f"The provided horizon folder name {horizon_folder} "
            "contains only empty items."
        )


def validate_zones_folder(project: Any, zone_folder: str) -> None:
    """
    Check if a zone folder exist inside the project and that data exists for some
    zones within the folder. Otherwise raise errors.
    """
    if zone_folder not in project.zones.representations:
        raise ValueError(
            f"The provided zone folder name {zone_folder} does not exist inside RMS."
        )

    if all(horizon[zone_folder].is_empty() for horizon in project.zones):
        raise RuntimeError(
            f"The provided zone folder name {zone_folder} contains only empty items."
        )


def get_horizons_in_folder(
    project: Any, horizon_folder: str
) -> list[xtgeo.RegularSurface]:
    """Get all non-empty horizons from a horizon folder stratigraphically ordered."""

    logger.debug("Reading horizons from folder %s", horizon_folder)
    validate_horizon_folder(project, horizon_folder)

    surfaces = []
    for horizon in project.horizons:
        if not horizon[horizon_folder].is_empty():
            surfaces.append(
                xtgeo.surface_from_roxar(project, horizon.name, horizon_folder)
            )
    return surfaces


def get_zones_in_folder(project: Any, zone_folder: str) -> list[xtgeo.RegularSurface]:
    """Get all non-empty surfaces from a zones folder stratigraphically ordered."""

    logger.debug("Reading surfaces from zone folder %s", zone_folder)
    validate_zones_folder(project, zone_folder)

    surfaces = []
    for zone in project.zones:
        if not zone[zone_folder].is_empty():
            surfaces.append(xtgeo.surface_from_roxar(project, zone.name, zone_folder))
    return surfaces


def get_polygons_in_folder(project: Any, horizon_folder: str) -> list[xtgeo.Polygons]:
    """Get all non-empty polygons from a horizon folder stratigraphically ordered."""

    logger.debug("Reading polygons from folder %s", horizon_folder)
    validate_horizon_folder(project, horizon_folder)

    polygons = []
    for horizon in project.horizons:
        if not horizon[horizon_folder].is_empty():
            polygon = xtgeo.polygons_from_roxar(project, horizon.name, horizon_folder)
            polygon.name = horizon.name  # not automatically set for polygons
            polygons.append(polygon)
    return polygons
