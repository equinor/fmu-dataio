from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import xtgeo
from packaging.version import parse as versionparse

from fmu.dataio._logging import null_logger
from fmu.dataio._utils import load_config_from_path

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


def load_global_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Could not detect the global config file at standard "
            f"location: {CONFIG_PATH}."
        )
    return load_config_from_path(CONFIG_PATH)


def horizon_folder_exist(project: Any, horizon_folder: str) -> bool:
    """Check if a horizon folder exist inside the project"""
    return horizon_folder in project.horizons.representations


def get_horizons_in_folder(
    project: Any, horizon_folder: str
) -> list[xtgeo.RegularSurface]:
    """Get all non-empty horizons from a horizon folder stratigraphically ordered."""

    logger.debug("Reading horizons from folder %s", horizon_folder)

    if not horizon_folder_exist(project, horizon_folder):
        raise ValueError(
            f"The provided horizon folder name {horizon_folder} "
            "does not exist inside RMS."
        )

    surfaces = []
    for horizon in project.horizons:
        if not horizon[horizon_folder].is_empty():
            surfaces.append(
                xtgeo.surface_from_roxar(project, horizon.name, horizon_folder)
            )
    return surfaces
