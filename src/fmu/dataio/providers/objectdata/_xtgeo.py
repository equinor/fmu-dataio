from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Final

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from fmu.dataio._definitions import ExportFolder, FileExtension
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import get_geometry_ref, npfloat_to_float
from fmu.dataio.exceptions import ConfigurationError
from fmu.datamodels.fmu_results.data import BoundingBox2D, BoundingBox3D, Geometry
from fmu.datamodels.fmu_results.enums import FileFormat, Layout, ObjectMetadataClass
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.datamodels.fmu_results.specification import (
    CPGridPropertySpecification,
    CPGridSpecification,
    CubeSpecification,
    PointSpecification,
    PolygonsSpecification,
    SurfaceSpecification,
    ZoneDefinition,
)

from ._base import ObjectDataProvider
from ._tables import _derive_index

if TYPE_CHECKING:
    from io import BytesIO

    import pandas as pd
    import xtgeo

logger: Final = null_logger(__name__)


def lack_of_geometry_warn() -> None:
    warnings.warn(
        dedent(
            """
            From fmu.dataio version 2.3:

            When exporting a grid property, linking it to a geometry is strongly
            recommended and may be mandatory in the near future!
            See example in the documentation.
            """
        ),
        FutureWarning,
    )


@dataclass
class RegularSurfaceDataProvider(ObjectDataProvider):
    obj: xtgeo.RegularSurface

    @property
    def classname(self) -> ObjectMetadataClass:
        return ObjectMetadataClass.surface

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.maps.value

    @property
    def extension(self) -> str:
        return FileExtension.gri.value

    @property
    def fmt(self) -> FileFormat:
        return FileFormat.irap_binary

    @property
    def layout(self) -> Layout:
        return Layout.regular

    @property
    def table_index(self) -> None:
        """Return the table index."""

    def get_geometry(self) -> None:
        """Derive data.geometry for xtgeo.RegularSurface."""

    def get_bbox(self) -> BoundingBox2D | BoundingBox3D:
        """
        Derive data.bbox for xtgeo.RegularSurface. The zmin/zmax fields represents
        the minimum/maximum surface values and should be absent in the metadata if the
        surface only has undefined values.
        """
        logger.info("Get bbox for RegularSurface")

        if np.isfinite(self.obj.values).any():
            return BoundingBox3D(
                xmin=float(self.obj.xmin),
                xmax=float(self.obj.xmax),
                ymin=float(self.obj.ymin),
                ymax=float(self.obj.ymax),
                zmin=float(self.obj.values.min()),
                zmax=float(self.obj.values.max()),
            )

        return BoundingBox2D(
            xmin=float(self.obj.xmin),
            xmax=float(self.obj.xmax),
            ymin=float(self.obj.ymin),
            ymax=float(self.obj.ymax),
        )

    def get_spec(self) -> SurfaceSpecification:
        """Derive data.spec for xtgeo.RegularSurface."""
        logger.info("Get spec for RegularSurface")

        required = self.obj.metadata.required
        return SurfaceSpecification(
            ncol=npfloat_to_float(required["ncol"]),
            nrow=npfloat_to_float(required["nrow"]),
            xori=npfloat_to_float(required["xori"]),
            yori=npfloat_to_float(required["yori"]),
            xinc=npfloat_to_float(required["xinc"]),
            yinc=npfloat_to_float(required["yinc"]),
            yflip=npfloat_to_float(required["yflip"]),
            rotation=npfloat_to_float(required["rotation"]),
            undef=1.0e30,
        )

    def export_to_file(self, file: Path | BytesIO) -> None:
        """Export the object to file or memory buffer"""

        self.obj.to_file(file, fformat="irap_binary")


@dataclass
class PolygonsDataProvider(ObjectDataProvider):
    obj: xtgeo.Polygons

    def __post_init__(self) -> None:
        if self.fmt == FileFormat.csv:
            self.obj = self.obj.copy()

            self.obj.xname = "X"
            self.obj.yname = "Y"
            self.obj.zname = "Z"
            self.obj.pname = "ID"

        super().__post_init__()

    @property
    def classname(self) -> ObjectMetadataClass:
        return ObjectMetadataClass.polygons

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.polygons.value

    @property
    def extension(self) -> str:
        if self.fmt == FileFormat.irap_ascii:
            return FileExtension.pol.value

        if self.fmt == FileFormat.parquet:
            return FileExtension.parquet.value

        if self.fmt in [FileFormat.csv, FileFormat.csv_xtgeo]:
            return FileExtension.csv.value

        raise ConfigurationError(
            f"The file format {self.fmt.value} is not supported. ",
            f"Valid formats are: {['irap_ascii', 'csv', 'csv|xtgeo', 'parquet']}",
        )

    @property
    def fmt(self) -> FileFormat:
        return FileFormat(self.dataio.polygons_fformat)

    @property
    def layout(self) -> Layout:
        return Layout.unset

    @property
    def table_index(self) -> list[str] | None:
        """Return the table index."""
        if self.fmt == FileFormat.irap_ascii:
            return None

        return (
            _derive_index(
                table_index=self.dataio.table_index,
                table_columns=list(self.obj_dataframe.columns),
                content=self.dataio._get_content_enum(),
            )
            or None
        )

    @property
    def obj_dataframe(self) -> pd.DataFrame:
        """Returns a dataframe of the referenced xtgeo.Polygons object."""
        return self.obj.get_dataframe(copy=False)

    def get_geometry(self) -> None:
        """Derive data.geometry for xtgeo.Polygons."""

    def get_bbox(self) -> BoundingBox3D:
        """Derive data.bbox for xtgeo.Polygons"""
        logger.info("Get bbox for Polygons")

        xmin, xmax, ymin, ymax, zmin, zmax = self.obj.get_boundary()
        return BoundingBox3D(
            xmin=float(xmin),
            xmax=float(xmax),
            ymin=float(ymin),
            ymax=float(ymax),
            zmin=float(zmin),
            zmax=float(zmax),
        )

    def get_spec(self) -> PolygonsSpecification:
        """Derive data.spec for xtgeo.Polygons."""
        logger.info("Get spec for Polygons")

        df = self.obj_dataframe
        num_rows, num_columns = df.shape

        if self.fmt == FileFormat.irap_ascii:
            return PolygonsSpecification(
                npolys=df[self.obj.pname].nunique(),
            )
        return PolygonsSpecification(
            npolys=df[self.obj.pname].nunique(),
            columns=list(df.columns),
            num_columns=num_columns,
            num_rows=num_rows,
            size=int(df.size),
        )

    def export_to_file(self, file: Path | BytesIO) -> None:
        """Export the object to file or memory buffer"""

        if self.fmt == FileFormat.parquet:
            table = pa.Table.from_pandas(self.obj_dataframe)
            pq.write_table(table, where=pa.output_stream(file))

        elif self.fmt == FileFormat.irap_ascii:
            self.obj.to_file(file)

        else:
            self.obj_dataframe.to_csv(file, index=False)


@dataclass
class PointsDataProvider(ObjectDataProvider):
    obj: xtgeo.Points

    def __post_init__(self) -> None:
        if self.fmt == FileFormat.csv:
            self.obj = self.obj.copy()

            self.obj.xname = "X"
            self.obj.yname = "Y"
            self.obj.zname = "Z"

        super().__post_init__()

    @property
    def classname(self) -> ObjectMetadataClass:
        return ObjectMetadataClass.points

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.points.value

    @property
    def extension(self) -> str:
        if self.fmt == FileFormat.irap_ascii:
            return FileExtension.poi.value

        if self.fmt == FileFormat.parquet:
            return FileExtension.parquet.value

        if self.fmt in [FileFormat.csv, FileFormat.csv_xtgeo]:
            return FileExtension.csv.value

        raise ConfigurationError(
            f"The file format {self.fmt.value} is not supported. ",
            f"Valid formats are: {['irap_ascii', 'csv', 'csv|xtgeo', 'parquet']}",
        )

    @property
    def fmt(self) -> FileFormat:
        return FileFormat(self.dataio.points_fformat)

    @property
    def layout(self) -> Layout:
        return Layout.unset

    @property
    def table_index(self) -> list[str] | None:
        """Return the table index."""
        if self.fmt == FileFormat.irap_ascii:
            return None

        return (
            _derive_index(
                table_index=self.dataio.table_index,
                table_columns=list(self.obj_dataframe.columns),
                content=self.dataio._get_content_enum(),
            )
            or None
        )

    @property
    def obj_dataframe(self) -> pd.DataFrame:
        """Returns a dataframe of the referenced xtgeo.Points object."""
        return self.obj.get_dataframe(copy=False)

    def get_geometry(self) -> None:
        """Derive data.geometry for xtgeo.Points."""

    def get_bbox(self) -> BoundingBox3D:
        """Derive data.bbox for xtgeo.Points."""
        logger.info("Get bbox for Points")

        df = self.obj_dataframe
        return BoundingBox3D(
            xmin=float(df[self.obj.xname].min()),
            xmax=float(df[self.obj.xname].max()),
            ymax=float(df[self.obj.yname].min()),
            ymin=float(df[self.obj.yname].max()),
            zmin=float(df[self.obj.zname].min()),
            zmax=float(df[self.obj.zname].max()),
        )

    def get_spec(self) -> PointSpecification:
        """Derive data.spec for xtgeo.Points."""
        logger.info("Get spec for Points")

        df = self.obj_dataframe
        num_rows, num_columns = df.shape

        if self.fmt == FileFormat.irap_ascii:
            return PointSpecification(
                attributes=list(df.columns[3:]) if len(df.columns) > 3 else None,
                size=int(df.size),
            )
        return PointSpecification(
            attributes=list(df.columns[3:]) if len(df.columns) > 3 else None,
            size=int(df.size),
            columns=list(df.columns),
            num_columns=num_columns,
            num_rows=num_rows,
        )

    def export_to_file(self, file: Path | BytesIO) -> None:
        """Export the object to file or memory buffer"""

        if self.fmt == FileFormat.parquet:
            table = pa.Table.from_pandas(self.obj_dataframe)
            pq.write_table(table, where=pa.output_stream(file))

        elif self.fmt == FileFormat.irap_ascii:
            self.obj.to_file(file)

        else:
            self.obj_dataframe.to_csv(file, index=False)


@dataclass
class CubeDataProvider(ObjectDataProvider):
    obj: xtgeo.Cube

    @property
    def classname(self) -> ObjectMetadataClass:
        return ObjectMetadataClass.cube

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.cubes.value

    @property
    def extension(self) -> str:
        return FileExtension.segy.value

    @property
    def fmt(self) -> FileFormat:
        return FileFormat.segy

    @property
    def layout(self) -> Layout:
        return Layout.regular

    @property
    def table_index(self) -> None:
        """Return the table index."""

    def get_geometry(self) -> None:
        """Derive data.geometry for xtgeo.Cube."""

    def get_bbox(self) -> BoundingBox3D:
        """Derive data.bbox for xtgeo.Cube."""
        logger.info("Get bbox for Cube")

        # current xtgeo is missing xmin, xmax etc attributes for cube, so need
        # to compute (simplify when xtgeo has this):
        xmin, ymin = 1.0e23, 1.0e23
        xmax, ymax = -xmin, -ymin

        for corner in (
            (1, 1),
            (1, self.obj.nrow),
            (self.obj.ncol, 1),
            (self.obj.ncol, self.obj.nrow),
        ):
            xco, yco = self.obj.get_xy_value_from_ij(*corner)
            xmin = min(xmin, xco)
            xmax = max(xmax, xco)
            ymin = min(ymin, yco)
            ymax = max(ymax, yco)

        return BoundingBox3D(
            xmin=float(xmin),
            xmax=float(xmax),
            ymin=float(ymin),
            ymax=float(ymax),
            zmin=float(self.obj.zori),
            zmax=float(self.obj.zori + self.obj.zinc * (self.obj.nlay - 1)),
        )

    def get_spec(self) -> CubeSpecification:
        """Derive data.spec for xtgeo.Cube."""
        logger.info("Get spec for Cube")

        required = self.obj.metadata.required
        return CubeSpecification(
            ncol=npfloat_to_float(required["ncol"]),
            nrow=npfloat_to_float(required["nrow"]),
            nlay=npfloat_to_float(required["nlay"]),
            xori=npfloat_to_float(required["xori"]),
            yori=npfloat_to_float(required["yori"]),
            zori=npfloat_to_float(required["zori"]),
            xinc=npfloat_to_float(required["xinc"]),
            yinc=npfloat_to_float(required["yinc"]),
            zinc=npfloat_to_float(required["zinc"]),
            yflip=npfloat_to_float(required["yflip"]),
            zflip=npfloat_to_float(required["zflip"]),
            rotation=npfloat_to_float(required["rotation"]),
            undef=npfloat_to_float(required["undef"]),
        )

    def export_to_file(self, file: Path | BytesIO) -> None:
        """Export the object to file or memory buffer"""

        self.obj.to_file(file, fformat="segy")


@dataclass
class CPGridDataProvider(ObjectDataProvider):
    obj: xtgeo.Grid

    @property
    def classname(self) -> ObjectMetadataClass:
        return ObjectMetadataClass.cpgrid

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.grids.value

    @property
    def extension(self) -> str:
        return FileExtension.roff.value

    @property
    def fmt(self) -> FileFormat:
        return FileFormat.roff

    @property
    def layout(self) -> Layout:
        return Layout.cornerpoint

    @property
    def table_index(self) -> None:
        """Return the table index."""

    def get_geometry(self) -> None:
        """Derive data.geometry for xtgeo.Grid."""

    def get_bbox(self) -> BoundingBox3D:
        """Derive data.bbox for xtgeo.Grid."""
        logger.info("Get bbox for Grid geometry")

        geox = self.obj.get_geometrics(
            cellcenter=False,
            allcells=True,
            return_dict=True,
        )
        return BoundingBox3D(
            xmin=round(float(geox["xmin"]), 4),
            xmax=round(float(geox["xmax"]), 4),
            ymin=round(float(geox["ymin"]), 4),
            ymax=round(float(geox["ymax"]), 4),
            zmin=round(float(geox["zmin"]), 4),
            zmax=round(float(geox["zmax"]), 4),
        )

    def get_spec(self) -> CPGridSpecification:
        """Derive data.spec for xtgeo.Grid."""
        logger.info("Get spec for Grid geometry")

        required = self.obj.metadata.required
        return CPGridSpecification(
            ncol=npfloat_to_float(required["ncol"]),
            nrow=npfloat_to_float(required["nrow"]),
            nlay=npfloat_to_float(required["nlay"]),
            xshift=npfloat_to_float(required["xshift"]),
            yshift=npfloat_to_float(required["yshift"]),
            zshift=npfloat_to_float(required["zshift"]),
            xscale=npfloat_to_float(required["xscale"]),
            yscale=npfloat_to_float(required["yscale"]),
            zscale=npfloat_to_float(required["zscale"]),
            zonation=self._get_zonation() if self.obj.subgrids else None,
        )

    def _get_zonation(self) -> list[ZoneDefinition]:
        """
        Get the zonation for the grid as a list of zone definitions.
        The list will be ordered from shallowest zone to deepest.
        """
        return sorted(
            [
                ZoneDefinition(
                    name=zone,
                    min_layer_idx=min(layerlist) - 1,
                    max_layer_idx=max(layerlist) - 1,
                )
                for zone, layerlist in self.obj.subgrids.items()
            ],
            key=lambda x: x.min_layer_idx,
        )

    def export_to_file(self, file: Path | BytesIO) -> None:
        """Export the object to file or memory buffer"""

        self.obj.to_file(file, fformat="roff")


@dataclass
class CPGridPropertyDataProvider(ObjectDataProvider):
    obj: xtgeo.GridProperty

    @property
    def classname(self) -> ObjectMetadataClass:
        return ObjectMetadataClass.cpgrid_property

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.grids.value

    @property
    def extension(self) -> str:
        return FileExtension.roff.value

    @property
    def fmt(self) -> FileFormat:
        return FileFormat.roff

    @property
    def layout(self) -> Layout:
        return Layout.cornerpoint

    @property
    def table_index(self) -> None:
        """Return the table index."""

    def get_bbox(self) -> None:
        """Derive data.bbox for xtgeo.GridProperty."""

    def get_spec(self) -> CPGridPropertySpecification:
        """Derive data.spec for xtgeo.GridProperty."""
        logger.info("Get spec for GridProperty")

        return CPGridPropertySpecification(
            nrow=self.obj.nrow,
            ncol=self.obj.ncol,
            nlay=self.obj.nlay,
        )

    def get_geometry(self) -> Geometry | None:
        """Derive data.geometry for xtgeo.GridProperty."""
        logger.info("Get geometry for a GridProperty, if present")

        # when invalid config this is not relevant
        if not isinstance(self.dataio.config, GlobalConfiguration):
            return None

        geometry_path = self.dataio.geometry
        if not geometry_path or not isinstance(geometry_path, str | Path):
            lack_of_geometry_warn()
            return None

        return get_geometry_ref(Path(geometry_path), self.obj)

    def export_to_file(self, file: Path | BytesIO) -> None:
        """Export the object to file or memory buffer"""

        self.obj.to_file(file, fformat="roff")
