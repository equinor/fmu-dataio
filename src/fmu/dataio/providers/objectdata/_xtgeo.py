from __future__ import annotations

import warnings
from dataclasses import dataclass
from textwrap import dedent
from typing import TYPE_CHECKING, Final

import numpy as np

from fmu.dataio._definitions import ExportFolder, ValidFormats
from fmu.dataio._logging import null_logger
from fmu.dataio._model.data import BoundingBox2D, BoundingBox3D, Geometry
from fmu.dataio._model.enums import FMUClass, Layout
from fmu.dataio._model.specification import (
    CPGridPropertySpecification,
    CPGridSpecification,
    CubeSpecification,
    PointSpecification,
    PolygonsSpecification,
    SurfaceSpecification,
    ZoneDefinition,
)
from fmu.dataio._utils import get_geometry_ref, npfloat_to_float

from ._base import ObjectDataProvider

if TYPE_CHECKING:
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
    def classname(self) -> FMUClass:
        return FMUClass.surface

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.maps.value

    @property
    def extension(self) -> str:
        return self._validate_get_ext(self.fmt, ValidFormats.surface)

    @property
    def fmt(self) -> str:
        return self.dataio.surface_fformat

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


@dataclass
class PolygonsDataProvider(ObjectDataProvider):
    obj: xtgeo.Polygons

    @property
    def classname(self) -> FMUClass:
        return FMUClass.polygons

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.polygons.value

    @property
    def extension(self) -> str:
        return self._validate_get_ext(self.fmt, ValidFormats.polygons)

    @property
    def fmt(self) -> str:
        return self.dataio.polygons_fformat

    @property
    def layout(self) -> Layout:
        return Layout.unset

    @property
    def table_index(self) -> None:
        """Return the table index."""

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

        return PolygonsSpecification(
            npolys=np.unique(
                self.obj.get_dataframe(copy=False)[self.obj.pname].values
            ).size
        )


@dataclass
class PointsDataProvider(ObjectDataProvider):
    obj: xtgeo.Points

    @property
    def classname(self) -> FMUClass:
        return FMUClass.points

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.points.value

    @property
    def extension(self) -> str:
        return self._validate_get_ext(self.fmt, ValidFormats.points)

    @property
    def fmt(self) -> str:
        return self.dataio.points_fformat

    @property
    def layout(self) -> Layout:
        return Layout.unset

    @property
    def table_index(self) -> None:
        """Return the table index."""

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
        return PointSpecification(
            attributes=list(df.columns[3:]) if len(df.columns) > 3 else None,
            size=int(df.size),
        )


@dataclass
class CubeDataProvider(ObjectDataProvider):
    obj: xtgeo.Cube

    @property
    def classname(self) -> FMUClass:
        return FMUClass.cube

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.cubes.value

    @property
    def extension(self) -> str:
        return self._validate_get_ext(self.fmt, ValidFormats.cube)

    @property
    def fmt(self) -> str:
        return self.dataio.cube_fformat

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


@dataclass
class CPGridDataProvider(ObjectDataProvider):
    obj: xtgeo.Grid

    @property
    def classname(self) -> FMUClass:
        return FMUClass.cpgrid

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.grids.value

    @property
    def extension(self) -> str:
        return self._validate_get_ext(self.fmt, ValidFormats.grid)

    @property
    def fmt(self) -> str:
        return self.dataio.grid_fformat

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


@dataclass
class CPGridPropertyDataProvider(ObjectDataProvider):
    obj: xtgeo.GridProperty

    @property
    def classname(self) -> FMUClass:
        return FMUClass.cpgrid_property

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.grids.value

    @property
    def extension(self) -> str:
        return self._validate_get_ext(self.fmt, ValidFormats.grid)

    @property
    def fmt(self) -> str:
        return self.dataio.grid_fformat

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

        name, relpath = get_geometry_ref(self.dataio.geometry, self.obj)

        # issue a warning if geometry is missing:
        if not relpath:
            lack_of_geometry_warn()

        return Geometry(name=name, relative_path=relpath) if name and relpath else None
