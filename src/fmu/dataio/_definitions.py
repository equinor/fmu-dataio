"""Various definitions and hard settings used in fmu-dataio."""

from __future__ import annotations

from enum import Enum
from typing import Final

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
