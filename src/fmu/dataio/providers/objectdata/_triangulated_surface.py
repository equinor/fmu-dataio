from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from fmu.dataio._definitions import ExportFolder, FileExtension
from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.data import BoundingBox3D
from fmu.dataio._models.fmu_results.enums import FileFormat, FMUClass, Layout
from fmu.dataio._models.fmu_results.specification import (
    TriangulatedSurfaceSpecification,
)
from fmu.dataio._readers import tsurf as reader

from ._base import (
    ObjectDataProvider,
)

if TYPE_CHECKING:
    from io import BytesIO

    from fmu.dataio._readers.tsurf import TSurfData

logger: Final = null_logger(__name__)


@dataclass
class TriangulatedSurfaceProvider(ObjectDataProvider):
    """Provider for triangulated surface data."""

    obj: TSurfData

    @property
    def classname(self) -> FMUClass:
        return FMUClass.triangulated_surface

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.maps.value

    @property
    def extension(self) -> str:
        return FileExtension.tsurf.value

    @property
    def fmt(self) -> FileFormat:
        return FileFormat.tsurf

    @property
    def layout(self) -> Layout:
        return Layout.triangulated_surface

    @property
    def table_index(self) -> None:
        """Return the table index."""

    def get_geometry(self) -> None:
        """Derive data.geometry for TriangulatedSurface."""

    def get_bbox(self) -> BoundingBox3D:
        """Derive data.bbox for TriangulatedSurface."""
        logger.info("Get bounding box for TriangulatedSurface")

        return BoundingBox3D.model_validate(self.obj.bbox())

    def get_spec(self) -> TriangulatedSurfaceSpecification:
        """Derive data.spec for TriangulatedSurface"""
        logger.info("Get spec for TriangulatedSurface")

        return TriangulatedSurfaceSpecification(
            num_vertices=self.obj.num_vertices(),
            num_triangles=self.obj.num_triangles(),
        )

    def export_to_file(self, output: Path | BytesIO) -> None:
        """Export the object to file or memory buffer"""

        reader.write_tsurf_to_file(self.obj, output)
