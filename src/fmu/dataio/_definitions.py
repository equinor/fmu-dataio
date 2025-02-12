"""Various definitions and hard settings used in fmu-dataio."""

from __future__ import annotations

from enum import Enum
from typing import Final

from fmu.dataio._models.fmu_results.enums import Content
from fmu.dataio.export._enums import InplaceVolumes


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


STANDARD_TABLE_INDEX_COLUMNS: Final[dict[Content, list[str]]] = {
    Content.volumes: InplaceVolumes.index_columns(),
    Content.rft: ["measured_depth", "well", "time"],
    Content.timeseries: ["DATE"],
    Content.simulationtimeseries: ["DATE"],
    Content.wellpicks: ["WELL", "HORIZON"],
    Content.relperm: ["SATNUM"],
}
