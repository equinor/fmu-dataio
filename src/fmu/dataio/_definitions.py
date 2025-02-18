"""Various definitions and hard settings used in fmu-dataio."""

from __future__ import annotations

from enum import Enum
from typing import Final, List

from pydantic import BaseModel, model_validator

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


class StandardTableIndex(BaseModel):
    columns: List[str]
    """List of all index columns"""
    required: List[str]
    """List of required index columns"""

    @model_validator(mode="after")
    def _required_in_columns(self) -> StandardTableIndex:
        if not all(c in self.columns for c in self.required):
            raise ValueError("Not all required columns are listed in columns")
        return self


STANDARD_TABLE_INDEX_COLUMNS: Final[dict[Content, StandardTableIndex]] = {
    Content.volumes: StandardTableIndex(
        columns=InplaceVolumes.index_columns(),
        required=InplaceVolumes.required_index_columns(),
    ),
    Content.rft: StandardTableIndex(
        columns=["measured_depth", "well", "time"],
        required=["measured_depth", "well", "time"],
    ),
    Content.timeseries: StandardTableIndex(
        columns=["DATE"],
        required=["DATE"],
    ),
    Content.simulationtimeseries: StandardTableIndex(
        columns=["DATE"],
        required=["DATE"],
    ),
    Content.wellpicks: StandardTableIndex(
        columns=["WELL", "HORIZON"],
        required=["WELL", "HORIZON"],
    ),
    Content.relperm: StandardTableIndex(
        columns=["SATNUM"],
        required=["SATNUM"],
    ),
}
