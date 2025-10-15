from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

import xtgeo
from packaging.version import parse as versionparse

from fmu.dataio._logging import null_logger
from fmu.dataio.exceptions import ValidationError
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.datamodels.standard_results import enums

try:
    import rmsapi
except ImportError as e:
    raise ImportError(
        "Module 'rmsapi' is not available. You have to be inside "
        "RMS to use this function."
    ) from e

if TYPE_CHECKING:
    from packaging.version import Version


logger: Final = null_logger(__name__)


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


def get_open_polygons_id(pol: xtgeo.Polygons) -> list[int]:
    """
    Return list of id's for open polygons within an xtgeo.Polygon.
    In an open polygon the first and last row of the dataframe are not equal
    i.e. different coordinates.
    """
    open_polygons = []
    for polid, poldf in pol.get_dataframe(copy=False).groupby("POLY_ID"):
        if not poldf.iloc[0].equals(poldf.iloc[-1]):
            open_polygons.append(polid)
    return open_polygons


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
        rms_object = horizon[horizon_folder]
        if isinstance(rms_object, rmsapi.Surface) and not rms_object.is_empty():
            surfaces.append(
                xtgeo.surface_from_roxar(
                    project, horizon.name, horizon_folder, stype="horizons"
                )
            )
    if not surfaces:
        raise RuntimeError(
            f"No surfaces detected in the provided folder '{horizon_folder}'"
        )
    return surfaces


def get_zones_in_folder(project: Any, zone_folder: str) -> list[xtgeo.RegularSurface]:
    """Get all non-empty surfaces from a zones folder stratigraphically ordered."""

    logger.debug("Reading surfaces from zone folder %s", zone_folder)
    validate_zones_folder(project, zone_folder)

    surfaces = []
    for zone in project.zones:
        rms_object = zone[zone_folder]
        if isinstance(rms_object, rmsapi.Surface) and not rms_object.is_empty():
            surfaces.append(
                xtgeo.surface_from_roxar(project, zone.name, zone_folder, stype="zones")
            )
    if not surfaces:
        raise RuntimeError(
            f"No surfaces detected in the provided folder '{zone_folder}'"
        )
    return surfaces


def get_polygons_in_folder(
    project: Any, horizon_folder: str, attributes: bool = False
) -> list[xtgeo.Polygons]:
    """Get all non-empty polygons from a horizon folder stratigraphically ordered."""

    logger.debug("Reading polygons from folder %s", horizon_folder)
    validate_horizon_folder(project, horizon_folder)

    polygons = []
    for horizon in project.horizons:
        rms_object = horizon[horizon_folder]
        if isinstance(rms_object, rmsapi.Polylines) and not rms_object.is_empty():
            polygons.append(
                xtgeo.polygons_from_roxar(
                    project,
                    horizon.name,
                    horizon_folder,
                    attributes=attributes,
                    stype="horizons",
                )
            )
    if not polygons:
        raise RuntimeError(
            f"No polygons detected in the provided folder '{horizon_folder}'"
        )
    return polygons


def get_general2d_folder(project: Any, folder_path: list[str]) -> rmsapi.Folder:
    """
    Get a General 2D Data folder from the project as an rmsapi.Folder.
    If accessing a subfolder provide the full data path to it as a list
    Example: ['main_folder', 'subfolder'].
    """
    try:
        return project.general2d_data.folders[folder_path]
    except KeyError as err:
        raise ValueError(
            f"The requested General 2D Data folder path {'/'.join(folder_path)} "
            "does not exist."
        ) from err


def get_items_in_general2d_folder(
    project: Any, folder_path: list[str]
) -> rmsapi.Points | rmsapi.Polylines | rmsapi.Surface | rmsapi.Function:
    """Get all items within a General 2D Data folder, folders are excluded"""
    return get_general2d_folder(project, folder_path).values()


def list_folder_names_in_general2d_folder(
    project: Any, folder_path: list[str]
) -> list[str]:
    """List all subfolder names within a General 2D Data folder"""
    folder = get_general2d_folder(project, folder_path)
    return folder.folders.keys()


def get_surfaces_in_general2d_folder(
    project: Any, folder_path: list[str]
) -> list[xtgeo.RegularSurface]:
    """Get all surfaces from a General 2D Data folder"""
    folder_items = get_items_in_general2d_folder(project, folder_path)

    surfaces = []
    for item in folder_items:
        if isinstance(item, rmsapi.Surface) and not item.is_empty():
            surfaces.append(
                xtgeo.surface_from_roxar(
                    project, item.name, "/".join(folder_path), stype="general2d_data"
                )
            )
    if not surfaces:
        raise RuntimeError(
            "No surfaces detected in the provided General 2D data "
            f"folder: '{'/'.join(folder_path)}' "
        )
    return surfaces


def get_polygons_in_general2d_folder(
    project: Any, folder_path: list[str]
) -> list[xtgeo.Polygons]:
    """Get all polygons from a General 2D Data folder"""
    folder_items = get_items_in_general2d_folder(project, folder_path)

    polygons = []
    for item in folder_items:
        if isinstance(item, rmsapi.Polylines) and not item.is_empty():
            polygons.append(
                xtgeo.polygons_from_roxar(
                    project, item.name, "/".join(folder_path), stype="general2d_data"
                )
            )
    if not polygons:
        raise RuntimeError(
            "No polygons detected in the provided General 2D data "
            f"folder: '{'/'.join(folder_path)}' "
        )
    return polygons


def get_faultlines_in_folder(project: Any, horizon_folder: str) -> list[xtgeo.Polygons]:
    """
    Get all non-empty fault lines from a horizon folder stratigraphically ordered.
    Fault lines extracted from a horizon model in RMS will have a 'Name' attribute
    indicating fault names. This is included in the dataframe for each fault line
    and is converted to uppercase. Error is raised if the 'Name' attribute is missing.
    """

    fault_lines = get_polygons_in_folder(project, horizon_folder, attributes=True)
    for pol in fault_lines:
        df = pol.get_dataframe(copy=False)

        if "Name" not in df:
            raise ValidationError(
                f"The fault line polygon {pol.name} is missing the 'Name' "
                "attribute. Ensure the fault lines in the horizon folder "
                f"{horizon_folder} have been extracted from a horizon model"
                "using the 'Extract Fault Lines' job in RMS."
            )

        df = df.rename(columns={"Name": enums.FaultLines.TableIndexColumns.NAME.value})
        pol.set_dataframe(df)

    return fault_lines


def validate_name_in_stratigraphy(name: str, config: GlobalConfiguration) -> None:
    """Validate that an input name is present in the config.stratigraphy."""
    if not config.stratigraphy:
        raise ValidationError(
            "The 'stratigraphy' block is lacking in the config. "
            "This is required for the export function to work."
        )
    if name not in config.stratigraphy:
        raise ValidationError(
            f"The stratigraphic {name=} is not listed in the 'stratigraphy' "
            "block in the config. This is required, please add it and rerun."
        )
