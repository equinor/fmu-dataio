"""Module for DataIO _ObjectData

This contains evaluation of the valid objects that can be handled and is mostly used
in the ``data`` block but some settings are applied later in the other blocks
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pandas as pd
import pyarrow as pa
import xtgeo

from fmu.dataio._definitions import ExportFolder, FileExtension
from fmu.dataio._export_config import ExportConfig
from fmu.dataio._logging import null_logger
from fmu.dataio._readers.faultroom import FaultRoomSurface
from fmu.dataio._readers.tsurf import TSurfData
from fmu.datamodels.fmu_results.enums import FileFormat, Layout, ObjectMetadataClass

from ._base import (
    ObjectDataProvider,
)
from ._faultroom import FaultRoomSurfaceProvider
from ._tables import ArrowTableDataProvider, DataFrameDataProvider
from ._triangulated_surface import TriangulatedSurfaceProvider
from ._xtgeo import (
    CPGridDataProvider,
    CPGridPropertyDataProvider,
    CubeDataProvider,
    PointsDataProvider,
    PolygonsDataProvider,
    RegularSurfaceDataProvider,
)

if TYPE_CHECKING:
    from io import BytesIO

    from fmu.dataio.types import Inferrable
    from fmu.datamodels.fmu_results.standard_result import StandardResult

logger: Final = null_logger(__name__)


def objectdata_provider_factory(
    obj: Inferrable,
    export_config: ExportConfig,
    standard_result: StandardResult | None = None,
) -> ObjectDataProvider:
    """Factory function that generates metadata for a particular data object. This
    function will return an instance of an object-independent (i.e., typeable) class
    derived from ObjectDataProvider.

    Returns:
        A subclass of ObjectDataProvider

    Raises:
        NotImplementedError: when receiving an object we don't know how to generated
        metadata for.
    """
    if isinstance(obj, xtgeo.RegularSurface):
        return RegularSurfaceDataProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, xtgeo.Polygons):
        return PolygonsDataProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, xtgeo.Points):
        return PointsDataProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, xtgeo.Cube):
        return CubeDataProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, xtgeo.Grid):
        return CPGridDataProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, xtgeo.GridProperty):
        return CPGridPropertyDataProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, pd.DataFrame):
        return DataFrameDataProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, FaultRoomSurface):
        return FaultRoomSurfaceProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, TSurfData):
        return TriangulatedSurfaceProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, dict):
        return DictionaryDataProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )
    if isinstance(obj, pa.Table):
        return ArrowTableDataProvider(
            obj=obj, export_config=export_config, standard_result=standard_result
        )

    raise NotImplementedError(f"This data type is not currently supported: {type(obj)}")


@dataclass
class DictionaryDataProvider(ObjectDataProvider):
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

    def export_to_file(self, file: Path | BytesIO) -> None:
        """Export the object to file or memory buffer"""

        serialized_json = json.dumps(self.obj)

        if isinstance(file, Path):
            with open(file, "w", encoding="utf-8") as stream:
                stream.write(serialized_json)
        else:
            file.write(serialized_json.encode("utf-8"))
