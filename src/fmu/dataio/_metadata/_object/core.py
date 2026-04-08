"""Module for creating ObjectData instances.

This contains evaluation of the valid objects that can be handled and is mostly used
in the ``data`` block but some settings are applied later in the other blocks
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pandas as pd
import pyarrow as pa
import xtgeo

from fmu.dataio._definitions import ExportFolder, FileExtension
from fmu.dataio._export import ExportConfig
from fmu.dataio._logging import null_logger
from fmu.dataio._readers.faultroom import FaultRoomSurface
from fmu.dataio._readers.tsurf import TSurfData
from fmu.datamodels.fmu_results.enums import FileFormat, Layout, ObjectMetadataClass

from ._base import (
    ObjectData,
)
from ._faultroom import FaultRoomSurfaceData
from ._tables import ArrowTableData, DataFrameData
from ._triangulated_surface import TriangulatedSurfaceData
from ._xtgeo import (
    CPGridData,
    CPGridPropertyData,
    CubeData,
    PointsData,
    PolygonsData,
    RegularSurfaceData,
)

if TYPE_CHECKING:
    from fmu.dataio.types import ExportableData

logger: Final = null_logger(__name__)


def create_object_data(obj: ExportableData, export_config: ExportConfig) -> ObjectData:
    """Factory function that generates metadata for a particular data object. This
    function will return an instance of an object-independent (i.e., typeable) class
    derived from ObjectData.

    Returns:
        A subclass of ObjectData

    Raises:
        NotImplementedError: when receiving an object we don't know how to generate
        metadata for.
    """
    if isinstance(obj, xtgeo.RegularSurface):
        return RegularSurfaceData(obj, export_config)
    if isinstance(obj, xtgeo.Polygons):
        return PolygonsData(obj, export_config)
    if isinstance(obj, xtgeo.Points):
        return PointsData(obj, export_config)
    if isinstance(obj, xtgeo.Cube):
        return CubeData(obj, export_config)
    if isinstance(obj, xtgeo.Grid):
        return CPGridData(obj, export_config)
    if isinstance(obj, xtgeo.GridProperty):
        return CPGridPropertyData(obj, export_config)
    if isinstance(obj, pd.DataFrame):
        return DataFrameData(obj, export_config)
    if isinstance(obj, FaultRoomSurface):
        return FaultRoomSurfaceData(obj, export_config)
    if isinstance(obj, TSurfData):
        return TriangulatedSurfaceData(obj, export_config)
    if isinstance(obj, dict):
        return DictionaryData(obj, export_config)
    if isinstance(obj, pa.Table):
        return ArrowTableData(obj, export_config)

    raise NotImplementedError(f"This data type is not currently supported: {type(obj)}")


class DictionaryData(ObjectData):
    obj: dict

    @property
    def classname(self) -> ObjectMetadataClass:
        return ObjectMetadataClass.dictionary

    @property
    def efolder(self) -> str:
        return self.export_config.forcefolder or ExportFolder.dictionaries.value

    @property
    def extension(self) -> str:
        return FileExtension.json.value

    @property
    def fmt(self) -> FileFormat:
        return FileFormat.json

    @property
    def layout(self) -> Layout:
        return Layout.dictionary

    @property
    def table_index(self) -> None:
        """Return the table index."""

    def get_geometry(self) -> None:
        """Derive data.geometry for dictionary."""

    def get_bbox(self) -> None:
        """Derive data.bbox for dict."""

    def get_spec(self) -> None:
        """Derive data.spec for dict."""
