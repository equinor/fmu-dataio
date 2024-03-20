"""Module for DataIO _ObjectData

This contains evaluation of the valid objects that can be handled and is mostly used
in the ``data`` block but some settings are applied later in the other blocks

Example data block::

data:

    # if stratigraphic, name must match the strat column; official name of this surface.
    name: volantis_top-volantis_base
    stratigraphic: false  # if true, this is a stratigraphic surf found in strat column
    offset: 0.0  # to be used if a specific horizon is represented with an offset.

    top: # not required, but allowed
        name: volantis_gp_top
        stratigraphic: true
        offset: 2.0
    base:
        name: volantis_gp_top
        stratigraphic: true
        offset: 8.3

    stratigraphic_alias: # other stratigraphic entities this corresponds to
                         # in the strat column, e.g. Top Viking vs Top Draupne.
        - SomeName Fm. 1 Top
    alias: # other known-as names, such as name used inside RMS etc
        - somename_fm_1_top
        - top_somename

    # content is white-listed and standardized
    content: depth

    # tagname is flexible. The tag is intended primarily for providing uniqueness.
    # The tagname will also be part of the outgoing file name on disk.
    tagname: ds_extract_geogrid

    # no content-specific attribute for "depth" but can come in the future

    properties: # what the values actually show. List, only one for IRAP Binary
                # surfaces. Multiple for 3d grid or multi-parameter surfaces.
                # First is geometry.
        - name: PropertyName
          attribute: owc
          is_discrete: false # to be used for discrete values in surfaces.
          calculation: null # max/min/rms/var/maxpos/sum/etc

    format: irap_binary
    layout: regular # / cornerpoint / structured / etc
    unit: m
    vertical_domain: depth # / time / null
    depth_reference: msl # / seabed / etc # mandatory when vertical_domain is depth?
    grid_model: # Making this an object to allow for expanding in the future
        name: MyGrid # important for data identification, also for other data types
    spec: # class/layout dependent, optional? Can spec be expanded to work for all
          # data types?
        ncol: 281
        nrow: 441
        ...
    bbox:
        xmin: 456012.5003497944
        xmax: 467540.52762886323
        ...

    # --- NB two variants of time, here old:
    time:
        - value: 2029-10-28T11:21:12
          label: "some label"
        - value: 2020-10-28T14:28:02
          label: "some other label"

    # --- Here new:
    t0:
        value: 2020-10-28T14:28:02
        label: "some other label"
    t1:
        value: 2029-10-28T11:21:12
        label: "some label"

    is_prediction: true # For separating pure QC output from actual predictions
    is_observation: true # Used for 4D data currently but also valid for other data?
    description:
        - Depth surfaces extracted from the structural model

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import pandas as pd
import xtgeo

from fmu.dataio._definitions import STANDARD_TABLE_INDEX_COLUMNS, ValidFormats
from fmu.dataio._logging import null_logger
from fmu.dataio.datastructure.meta import meta, specification

from ._objectdata_base import (
    DerivedObjectDescriptor,
    ObjectDataProvider,
    SpecificationAndBoundingBox,
)

if TYPE_CHECKING:
    from fmu.dataio.dataio import ExportData
    from fmu.dataio.types import Inferrable

logger: Final = null_logger(__name__)


def objectdata_provider_factory(
    obj: Inferrable, dataio: ExportData, meta_existing: dict | None = None
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
    if meta_existing:
        return ExistingDataProvider(obj=obj, dataio=dataio, meta_existing=meta_existing)

    meta_existing = {}
    if isinstance(obj, xtgeo.RegularSurface):
        return RegularSurfaceDataProvider(
            obj=obj, dataio=dataio, meta_existing=meta_existing
        )
    if isinstance(obj, xtgeo.Polygons):
        return PolygonsDataProvider(obj=obj, dataio=dataio, meta_existing=meta_existing)
    if isinstance(obj, xtgeo.Points):
        return PointsDataProvider(obj=obj, dataio=dataio, meta_existing=meta_existing)
    if isinstance(obj, xtgeo.Cube):
        return CubeDataProvider(obj=obj, dataio=dataio, meta_existing=meta_existing)
    if isinstance(obj, xtgeo.Grid):
        return CPGridDataProvider(obj=obj, dataio=dataio, meta_existing=meta_existing)
    if isinstance(obj, xtgeo.GridProperty):
        return CPGridPropertyDataProvider(
            obj=obj, dataio=dataio, meta_existing=meta_existing
        )
    if isinstance(obj, pd.DataFrame):
        return DataFrameDataProvider(
            obj=obj, dataio=dataio, meta_existing=meta_existing
        )
    if isinstance(obj, dict):
        return DictionaryDataProvider(
            obj=obj, dataio=dataio, meta_existing=meta_existing
        )

    from pyarrow import Table

    if isinstance(obj, Table):
        return ArrowTableDataProvider(
            obj=obj, dataio=dataio, meta_existing=meta_existing
        )

    raise NotImplementedError("This data type is not (yet) supported: ", type(obj))


def npfloat_to_float(v: Any) -> Any:
    return float(v) if isinstance(v, (np.float64, np.float32)) else v


@dataclass
class RegularSurfaceDataProvider(ObjectDataProvider):
    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data.spec and data.bbox for RegularSurface"""
        logger.info("Derive bbox and specs for RegularSurface")
        regsurf: xtgeo.RegularSurface = self.obj
        required = regsurf.metadata.required

        return SpecificationAndBoundingBox(
            spec=specification.SurfaceSpecification(
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
            ),
            bbox=meta.content.BoundingBox3D(
                xmin=float(regsurf.xmin),
                xmax=float(regsurf.xmax),
                ymin=float(regsurf.ymin),
                ymax=float(regsurf.ymax),
                zmin=float(regsurf.values.min()),
                zmax=float(regsurf.values.max()),
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
        )

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            subtype="RegularSurface",
            classname="surface",
            layout="regular",
            efolder="maps",
            fmt=(fmt := self.dataio.surface_fformat),
            spec=spec,
            bbox=bbox,
            extension=self._validate_get_ext(
                fmt, "RegularSurface", ValidFormats().surface
            ),
            table_index=None,
        )


@dataclass
class PolygonsDataProvider(ObjectDataProvider):
    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data.spec and data.bbox for Polygons"""
        logger.info("Derive bbox and specs for Polygons")
        poly: xtgeo.Polygons = self.obj
        xmin, xmax, ymin, ymax, zmin, zmax = poly.get_boundary()

        return SpecificationAndBoundingBox(
            spec=specification.PolygonsSpecification(
                npolys=np.unique(poly.get_dataframe(copy=False)[poly.pname].values).size
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
            bbox=meta.content.BoundingBox3D(
                xmin=float(xmin),
                xmax=float(xmax),
                ymin=float(ymin),
                ymax=float(ymax),
                zmin=float(zmin),
                zmax=float(zmax),
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
        )

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            subtype="Polygons",
            classname="polygons",
            layout="unset",
            efolder="polygons",
            fmt=(fmt := self.dataio.polygons_fformat),
            extension=self._validate_get_ext(fmt, "Polygons", ValidFormats().polygons),
            spec=spec,
            bbox=bbox,
            table_index=None,
        )


@dataclass
class PointsDataProvider(ObjectDataProvider):
    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data.spec and data.bbox for Points"""
        logger.info("Derive bbox and specs for Points")
        pnts: xtgeo.Points = self.obj
        df: pd.DataFrame = pnts.get_dataframe(copy=False)

        return SpecificationAndBoundingBox(
            spec=specification.PointSpecification(
                attributes=list(df.columns[3:]) if len(df.columns) > 3 else None,
                size=int(df.size),
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
            bbox=meta.content.BoundingBox3D(
                xmin=float(df[pnts.xname].min()),
                xmax=float(df[pnts.xname].max()),
                ymax=float(df[pnts.yname].min()),
                ymin=float(df[pnts.yname].max()),
                zmin=float(df[pnts.zname].min()),
                zmax=float(df[pnts.zname].max()),
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
        )

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            subtype="Points",
            classname="points",
            layout="unset",
            efolder="points",
            fmt=(fmt := self.dataio.points_fformat),
            extension=self._validate_get_ext(fmt, "Points", ValidFormats().points),
            spec=spec,
            bbox=bbox,
            table_index=None,
        )


@dataclass
class CubeDataProvider(ObjectDataProvider):
    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data.spec and data.bbox Cube"""
        logger.info("Derive bbox and specs for Cube")
        cube: xtgeo.Cube = self.obj
        required = cube.metadata.required

        # current xtgeo is missing xmin, xmax etc attributes for cube, so need
        # to compute (simplify when xtgeo has this):
        xmin, ymin = 1.0e23, 1.0e23
        xmax, ymax = -xmin, -ymin

        for corner in ((1, 1), (1, cube.nrow), (cube.ncol, 1), (cube.ncol, cube.nrow)):
            xco, yco = cube.get_xy_value_from_ij(*corner)
            xmin = min(xmin, xco)
            xmax = max(xmax, xco)
            ymin = min(ymin, yco)
            ymax = max(ymax, yco)

        return SpecificationAndBoundingBox(
            spec=specification.CubeSpecification(
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
            ),
            bbox=meta.content.BoundingBox3D(
                xmin=float(xmin),
                xmax=float(xmax),
                ymin=float(ymin),
                ymax=float(ymax),
                zmin=float(cube.zori),
                zmax=float(cube.zori + cube.zinc * (cube.nlay - 1)),
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
        )

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            subtype="RegularCube",
            classname="cube",
            layout="regular",
            efolder="cubes",
            fmt=(fmt := self.dataio.cube_fformat),
            extension=self._validate_get_ext(fmt, "RegularCube", ValidFormats().cube),
            spec=spec,
            bbox=bbox,
            table_index=None,
        )


@dataclass
class CPGridDataProvider(ObjectDataProvider):
    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data.spec and data.bbox CornerPoint Grid geometry"""
        logger.info("Derive bbox and specs for Gride (geometry)")
        grid: xtgeo.Grid = self.obj
        required = grid.metadata.required

        geox: dict = grid.get_geometrics(
            cellcenter=False,
            allcells=True,
            return_dict=True,
        )

        return SpecificationAndBoundingBox(
            spec=specification.CPGridSpecification(
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
            ),
            bbox=meta.content.BoundingBox3D(
                xmin=round(float(geox["xmin"]), 4),
                xmax=round(float(geox["xmax"]), 4),
                ymin=round(float(geox["ymin"]), 4),
                ymax=round(float(geox["ymax"]), 4),
                zmin=round(float(geox["zmin"]), 4),
                zmax=round(float(geox["zmax"]), 4),
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
        )

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            subtype="CPGrid",
            classname="cpgrid",
            layout="cornerpoint",
            efolder="grids",
            fmt=(fmt := self.dataio.grid_fformat),
            extension=self._validate_get_ext(fmt, "CPGrid", ValidFormats().grid),
            spec=spec,
            bbox=bbox,
            table_index=None,
        )


@dataclass
class CPGridPropertyDataProvider(ObjectDataProvider):
    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data.spec and data.bbox GridProperty"""
        logger.info("Derive bbox and specs for GridProperty")
        gridprop: xtgeo.GridProperty = self.obj

        return SpecificationAndBoundingBox(
            spec=specification.CPGridPropertySpecification(
                nrow=gridprop.nrow,
                ncol=gridprop.ncol,
                nlay=gridprop.nlay,
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
            bbox={},
        )

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            subtype="CPGridProperty",
            classname="cpgrid_property",
            layout="cornerpoint",
            efolder="grids",
            fmt=(fmt := self.dataio.grid_fformat),
            extension=self._validate_get_ext(
                fmt, "CPGridProperty", ValidFormats().grid
            ),
            spec=spec,
            bbox=bbox,
            table_index=None,
        )


@dataclass
class DataFrameDataProvider(ObjectDataProvider):
    def _get_columns(self) -> list[str]:
        """Get the columns from table"""
        if isinstance(self.obj, pd.DataFrame):
            logger.debug("pandas")
            columns = list(self.obj.columns)
        else:
            logger.debug("arrow")
            from pyarrow import Table

            assert isinstance(self.obj, Table)
            columns = self.obj.column_names
        logger.debug("Available columns in table %s ", columns)
        return columns

    def _derive_index(self) -> list[str]:
        """Derive table index"""
        # This could in the future also return context
        columns = self._get_columns()
        index = []

        if self.dataio.table_index is None:
            logger.debug("Finding index to include")
            for context, standard_cols in STANDARD_TABLE_INDEX_COLUMNS.items():
                for valid_col in standard_cols:
                    if valid_col in columns:
                        index.append(valid_col)
                if index:
                    logger.info("Context is %s ", context)
            logger.debug("Proudly presenting the index: %s", index)
        else:
            index = self.dataio.table_index

        if "REAL" in columns:
            index.append("REAL")
        self._check_index(index)
        return index

    def _check_index(self, index: list[str]) -> None:
        """Check the table index.
        Args:
            index (list): list of column names

        Raises:
            KeyError: if index contains names that are not in self
        """

        not_founds = (item for item in index if item not in self._get_columns())
        for not_found in not_founds:
            raise KeyError(f"{not_found} is not in table")

    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data items for DataFrame."""
        logger.info("Process data metadata for DataFrame (tables)")
        assert isinstance(self.obj, pd.DataFrame)
        return SpecificationAndBoundingBox(
            spec=specification.TableSpecification(
                columns=list(self.obj.columns),
                size=int(self.obj.size),
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
            bbox={},
        )

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            subtype="DataFrame",
            classname="table",
            layout="table",
            efolder="tables",
            fmt=(fmt := self.dataio.table_fformat),
            extension=self._validate_get_ext(fmt, "DataFrame", ValidFormats().table),
            spec=spec,
            bbox=bbox,
            table_index=self._derive_index(),
        )


@dataclass
class DictionaryDataProvider(ObjectDataProvider):
    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data items for dictionary."""
        logger.info("Process data metadata for dictionary")
        return SpecificationAndBoundingBox({}, {})

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            subtype="JSON",
            classname="dictionary",
            layout="dictionary",
            efolder="dictionaries",
            fmt=(fmt := self.dataio.dict_fformat),
            extension=self._validate_get_ext(fmt, "JSON", ValidFormats().dictionary),
            spec=spec,
            bbox=bbox,
            table_index=None,
        )


class ArrowTableDataProvider(ObjectDataProvider):
    def _get_columns(self) -> list[str]:
        """Get the columns from table"""
        if isinstance(self.obj, pd.DataFrame):
            logger.debug("pandas")
            columns = list(self.obj.columns)
        else:
            logger.debug("arrow")
            from pyarrow import Table

            assert isinstance(self.obj, Table)
            columns = self.obj.column_names
        logger.debug("Available columns in table %s ", columns)
        return columns

    def _derive_index(self) -> list[str]:
        """Derive table index"""
        # This could in the future also return context
        columns = self._get_columns()
        index = []

        if self.dataio.table_index is None:
            logger.debug("Finding index to include")
            for context, standard_cols in STANDARD_TABLE_INDEX_COLUMNS.items():
                for valid_col in standard_cols:
                    if valid_col in columns:
                        index.append(valid_col)
                if index:
                    logger.info("Context is %s ", context)
            logger.debug("Proudly presenting the index: %s", index)
        else:
            index = self.dataio.table_index

        if "REAL" in columns:
            index.append("REAL")
        self._check_index(index)
        return index

    def _check_index(self, index: list[str]) -> None:
        """Check the table index.
        Args:
            index (list): list of column names

        Raises:
            KeyError: if index contains names that are not in self
        """

        not_founds = (item for item in index if item not in self._get_columns())
        for not_found in not_founds:
            raise KeyError(f"{not_found} is not in table")

    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data items for Arrow table."""
        logger.info("Process data metadata for arrow (tables)")
        from pyarrow import Table

        assert isinstance(self.obj, Table)
        return SpecificationAndBoundingBox(
            spec=specification.TableSpecification(
                columns=list(self.obj.column_names),
                size=self.obj.num_columns * self.obj.num_rows,
            ).model_dump(
                mode="json",
                exclude_none=True,
            ),
            bbox={},
        )

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            table_index=self._derive_index(),
            subtype="ArrowTable",
            classname="table",
            layout="table",
            efolder="tables",
            fmt=(fmt := self.dataio.arrow_fformat),
            extension=self._validate_get_ext(fmt, "ArrowTable", ValidFormats().table),
            spec=spec,
            bbox=bbox,
        )


@dataclass
class ExistingDataProvider(ObjectDataProvider):
    """These functions should never be called because derive_metadata will populate the
    object data from existing metadata, by calling _derive_from_existing, and return
    before calling them."""

    def _derive_spec_and_bbox(self) -> SpecificationAndBoundingBox:
        """Process/collect the data items for dictionary."""
        logger.info("Process data metadata for dictionary")
        return SpecificationAndBoundingBox(
            self.meta_existing["spec"], self.meta_existing["bbox"]
        )

    def _derive_objectdata(self) -> DerivedObjectDescriptor:
        spec, bbox = self._derive_spec_and_bbox()
        return DerivedObjectDescriptor(
            subtype=self.meta_existing["subtype"],
            classname=self.meta_existing["class"],
            layout=self.meta_existing["layout"],
            efolder=self.efolder,
            fmt=self.meta_existing["format"],
            extension=self.extension,
            spec=spec,
            bbox=bbox,
            table_index=None,
        )
