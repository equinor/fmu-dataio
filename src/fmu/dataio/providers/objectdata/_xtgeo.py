from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import pandas as pd
import xtgeo

from fmu.dataio._definitions import ValidFormats
from fmu.dataio._logging import null_logger
from fmu.dataio._utils import npfloat_to_float
from fmu.dataio.datastructure.meta import meta, specification

from ._base import (
    DerivedObjectDescriptor,
    ObjectDataProvider,
)

if TYPE_CHECKING:
    import pandas as pd

logger: Final = null_logger(__name__)


@dataclass
class RegularSurfaceDataProvider(ObjectDataProvider):
    obj: xtgeo.RegularSurface

    def get_spec(self) -> dict[str, Any]:
        """Derive data.spec for xtgeo.RegularSurface."""
        logger.info("Get spec for RegularSurface")

        required = self.obj.metadata.required
        return specification.SurfaceSpecification(
            ncol=npfloat_to_float(required["ncol"]),
            nrow=npfloat_to_float(required["nrow"]),
            xori=npfloat_to_float(required["xori"]),
            yori=npfloat_to_float(required["yori"]),
            xinc=npfloat_to_float(required["xinc"]),
            yinc=npfloat_to_float(required["yinc"]),
            yflip=npfloat_to_float(required["yflip"]),
            rotation=npfloat_to_float(required["rotation"]),
            undef=1.0e30,
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_bbox(self) -> dict[str, Any]:
        """Derive data.bbox for xtgeo.RegularSurface."""
        logger.info("Get bbox for RegularSurface")

        return meta.content.BoundingBox3D(
            xmin=float(self.obj.xmin),
            xmax=float(self.obj.xmax),
            ymin=float(self.obj.ymin),
            ymax=float(self.obj.ymax),
            zmin=float(self.obj.values.min()),
            zmax=float(self.obj.values.max()),
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for xtgeo.RegularSurface."""
        return DerivedObjectDescriptor(
            subtype="RegularSurface",
            classname="surface",
            layout="regular",
            efolder="maps",
            fmt=(fmt := self.dataio.surface_fformat),
            spec=self.get_spec(),
            bbox=self.get_bbox(),
            extension=self._validate_get_ext(
                fmt, "RegularSurface", ValidFormats().surface
            ),
            table_index=None,
        )


@dataclass
class PolygonsDataProvider(ObjectDataProvider):
    obj: xtgeo.Polygons

    def get_spec(self) -> dict[str, Any]:
        """Derive data.spec for xtgeo.Polygons."""
        logger.info("Get spec for Polygons")

        return specification.PolygonsSpecification(
            npolys=np.unique(
                self.obj.get_dataframe(copy=False)[self.obj.pname].values
            ).size
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_bbox(self) -> dict[str, Any]:
        """Derive data.bbox for xtgeo.Polygons"""
        logger.info("Get bbox for Polygons")

        xmin, xmax, ymin, ymax, zmin, zmax = self.obj.get_boundary()
        return meta.content.BoundingBox3D(
            xmin=float(xmin),
            xmax=float(xmax),
            ymin=float(ymin),
            ymax=float(ymax),
            zmin=float(zmin),
            zmax=float(zmax),
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for xtgeo.Polygons."""
        return DerivedObjectDescriptor(
            subtype="Polygons",
            classname="polygons",
            layout="unset",
            efolder="polygons",
            fmt=(fmt := self.dataio.polygons_fformat),
            extension=self._validate_get_ext(fmt, "Polygons", ValidFormats().polygons),
            spec=self.get_spec(),
            bbox=self.get_bbox(),
            table_index=None,
        )


@dataclass
class PointsDataProvider(ObjectDataProvider):
    obj: xtgeo.Points

    @property
    def obj_dataframe(self) -> pd.DataFrame:
        """Returns a dataframe of the referenced xtgeo.Points object."""
        return self.obj.get_dataframe(copy=False)

    def get_spec(self) -> dict[str, Any]:
        """Derive data.spec for xtgeo.Points."""
        logger.info("Get spec for Points")

        df = self.obj_dataframe
        return specification.PointSpecification(
            attributes=list(df.columns[3:]) if len(df.columns) > 3 else None,
            size=int(df.size),
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_bbox(self) -> dict[str, Any]:
        """Derive data.bbox for xtgeo.Points."""
        logger.info("Get bbox for Points")

        df = self.obj_dataframe
        return meta.content.BoundingBox3D(
            xmin=float(df[self.obj.xname].min()),
            xmax=float(df[self.obj.xname].max()),
            ymax=float(df[self.obj.yname].min()),
            ymin=float(df[self.obj.yname].max()),
            zmin=float(df[self.obj.zname].min()),
            zmax=float(df[self.obj.zname].max()),
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for xtgeo.Points."""
        return DerivedObjectDescriptor(
            subtype="Points",
            classname="points",
            layout="unset",
            efolder="points",
            fmt=(fmt := self.dataio.points_fformat),
            extension=self._validate_get_ext(fmt, "Points", ValidFormats().points),
            spec=self.get_spec(),
            bbox=self.get_bbox(),
            table_index=None,
        )


@dataclass
class CubeDataProvider(ObjectDataProvider):
    obj: xtgeo.Cube

    def get_spec(self) -> dict[str, Any]:
        """Derive data.spec for xtgeo.Cube."""
        logger.info("Get spec for Cube")

        required = self.obj.metadata.required
        return specification.CubeSpecification(
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
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_bbox(self) -> dict[str, Any]:
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

        return meta.content.BoundingBox3D(
            xmin=float(xmin),
            xmax=float(xmax),
            ymin=float(ymin),
            ymax=float(ymax),
            zmin=float(self.obj.zori),
            zmax=float(self.obj.zori + self.obj.zinc * (self.obj.nlay - 1)),
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for xtgeo.Cube."""
        return DerivedObjectDescriptor(
            subtype="RegularCube",
            classname="cube",
            layout="regular",
            efolder="cubes",
            fmt=(fmt := self.dataio.cube_fformat),
            extension=self._validate_get_ext(fmt, "RegularCube", ValidFormats().cube),
            spec=self.get_spec(),
            bbox=self.get_bbox(),
            table_index=None,
        )


@dataclass
class CPGridDataProvider(ObjectDataProvider):
    obj: xtgeo.Grid

    def get_spec(self) -> dict[str, Any]:
        """Derive data.spec for xtgeo.Grid."""
        logger.info("Get spec for Grid geometry")

        required = self.obj.metadata.required
        return specification.CPGridSpecification(
            ncol=npfloat_to_float(required["ncol"]),
            nrow=npfloat_to_float(required["nrow"]),
            nlay=npfloat_to_float(required["nlay"]),
            xshift=npfloat_to_float(required["xshift"]),
            yshift=npfloat_to_float(required["yshift"]),
            zshift=npfloat_to_float(required["zshift"]),
            xscale=npfloat_to_float(required["xscale"]),
            yscale=npfloat_to_float(required["yscale"]),
            zscale=npfloat_to_float(required["zscale"]),
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_bbox(self) -> dict[str, Any]:
        """Derive data.bbox for xtgeo.Grid."""
        logger.info("Get bbox for Grid geometry")

        geox = self.obj.get_geometrics(
            cellcenter=False,
            allcells=True,
            return_dict=True,
        )
        return meta.content.BoundingBox3D(
            xmin=round(float(geox["xmin"]), 4),
            xmax=round(float(geox["xmax"]), 4),
            ymin=round(float(geox["ymin"]), 4),
            ymax=round(float(geox["ymax"]), 4),
            zmin=round(float(geox["zmin"]), 4),
            zmax=round(float(geox["zmax"]), 4),
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for xtgeo.Grid."""
        return DerivedObjectDescriptor(
            subtype="CPGrid",
            classname="cpgrid",
            layout="cornerpoint",
            efolder="grids",
            fmt=(fmt := self.dataio.grid_fformat),
            extension=self._validate_get_ext(fmt, "CPGrid", ValidFormats().grid),
            spec=self.get_spec(),
            bbox=self.get_bbox(),
            table_index=None,
        )


@dataclass
class CPGridPropertyDataProvider(ObjectDataProvider):
    obj: xtgeo.GridProperty

    def get_spec(self) -> dict[str, Any]:
        """Derive data.spec for xtgeo.GridProperty."""
        logger.info("Get spec for GridProperty")

        return specification.CPGridPropertySpecification(
            nrow=self.obj.nrow,
            ncol=self.obj.ncol,
            nlay=self.obj.nlay,
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_bbox(self) -> dict[str, Any]:
        """Derive data.bbox for xtgeo.GridProperty."""
        logger.info("Get bbox for GridProperty")
        return {}

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for xtgeo.GridProperty."""
        return DerivedObjectDescriptor(
            subtype="CPGridProperty",
            classname="cpgrid_property",
            layout="cornerpoint",
            efolder="grids",
            fmt=(fmt := self.dataio.grid_fformat),
            extension=self._validate_get_ext(
                fmt, "CPGridProperty", ValidFormats().grid
            ),
            spec=self.get_spec(),
            bbox=self.get_bbox() or None,
            table_index=None,
        )
