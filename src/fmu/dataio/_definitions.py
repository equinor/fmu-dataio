"""Various definitions and hard settings used in fmu-dataio."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, model_validator

from fmu.datamodels.fmu_results.enums import Content
from fmu.datamodels.standard_results.enums import InplaceVolumes

ERT_RELATIVE_CASE_METADATA_FILE: Final = "share/metadata/fmu_case.yml"


class ShareFolder(StrEnum):
    PREPROCESSED = "share/preprocessed/"
    OBSERVATIONS = "share/observations/"
    RESULTS = "share/results/"


class FileExtension(StrEnum):
    gri = ".gri"
    roff = ".roff"
    segy = ".segy"
    csv = ".csv"
    parquet = ".parquet"
    pol = ".pol"
    poi = ".poi"
    json = ".json"
    tsurf = ".ts"


class ExportFolder(StrEnum):
    cubes = "cubes"
    dictionaries = "dictionaries"
    grids = "grids"
    maps = "maps"
    points = "points"
    polygons = "polygons"
    tables = "tables"


class StandardTableIndex(BaseModel):
    columns: list[str]
    """List of all index columns"""
    required: list[str]
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
    Content.production_network: StandardTableIndex(
        columns=["DATE", "CHILD", "PARENT", "KEYWORD"],
        required=["DATE", "CHILD", "PARENT", "KEYWORD"],
    ),
    Content.rft: StandardTableIndex(
        columns=["WELL", "DATE"],
        required=["WELL", "DATE"],
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
    Content.well_completions: StandardTableIndex(
        columns=["WELL", "DATE", "ZONE"],
        required=["WELL", "DATE", "ZONE"],
    ),
}


class RMSExecutionMode(StrEnum):
    """The modes RMS can execute in. These definitions come from
    `runrms.executor._rms_executor`."""

    interactive = "interactive"
    batch = "batch"
