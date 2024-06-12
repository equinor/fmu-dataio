"""Various definitions and hard settings used in fmu-dataio."""

from __future__ import annotations

from enum import Enum, unique
from typing import Final, Type

SCHEMA: Final = (
    "https://main-fmu-schemas-prod.radix.equinor.com/schemas/0.8.0/fmu_results.json"
)
VERSION: Final = "0.8.0"
SOURCE: Final = "fmu"


class ValidationError(ValueError, KeyError):
    """Raise error while validating."""


class ConfigurationError(ValueError):
    pass


class ValidFormats(Enum):
    surface = {
        "irap_binary": ".gri",
    }

    grid = {
        "hdf": ".hdf",
        "roff": ".roff",
    }

    cube = {
        "segy": ".segy",
    }

    table = {
        "hdf": ".hdf",
        "csv": ".csv",
        "parquet": ".parquet",
    }

    polygons = {
        "hdf": ".hdf",
        "csv": ".csv",  # columns will be X Y Z, ID
        "csv|xtgeo": ".csv",  # use default xtgeo columns: X_UTME, ... POLY_ID
        "irap_ascii": ".pol",
    }

    points = {
        "hdf": ".hdf",
        "csv": ".csv",  # columns will be X Y Z
        "csv|xtgeo": ".csv",  # use default xtgeo columns: X_UTME, Y_UTMN, Z_TVDSS
        "irap_ascii": ".poi",
    }

    dictionary = {
        "json": ".json",
    }


class ExportFolder(str, Enum):
    cubes = "cubes"
    dictionaries = "dictionaries"
    grids = "grids"
    maps = "maps"
    points = "points"
    polygons = "polygons"
    tables = "tables"


STANDARD_TABLE_INDEX_COLUMNS: Final[dict[str, list[str]]] = {
    "volumes": ["ZONE", "REGION", "FACIES", "LICENCE"],
    "rft": ["measured_depth", "well", "time"],
    "timeseries": ["DATE"],  # summary
    "wellpicks": ["WELL", "HORIZON"],
}


@unique
class FmuContext(str, Enum):
    """
    Use a Enum class for fmu_context entries.

    The different entries will impact where data is exported:
    REALIZATION = "To realization-N/iter_M/share"
    CASE = "To casename/share, but will also work on project disk"
    PREPROCESSED = "To share/preprocessed; from interactive runs but re-used later"
    NON_FMU = "Not ran in a FMU setting, e.g. interactive RMS"

    """

    REALIZATION = "realization"
    CASE = "case"
    PREPROCESSED = "preprocessed"
    NON_FMU = "non-fmu"

    @classmethod
    def list_valid_values(cls) -> list[str]:
        return [m.value for m in cls]

    @classmethod
    def _missing_(cls: Type[FmuContext], value: object) -> None:
        raise ValueError(
            f"Invalid FmuContext {value=}. Valid entries are {cls.list_valid_values()}"
        )
