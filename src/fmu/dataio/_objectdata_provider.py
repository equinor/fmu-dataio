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

from dataclasses import dataclass, field
from datetime import datetime as dt
from pathlib import Path
from typing import Any, Final, Optional
from warnings import warn

import numpy as np
import pandas as pd
import xtgeo

from ._definitions import ALLOWED_CONTENTS, STANDARD_TABLE_INDEX_COLUMNS, _ValidFormats
from ._logging import null_logger
from ._utils import generate_description, parse_timedata

logger: Final = null_logger(__name__)


class ConfigurationError(ValueError):
    pass


@dataclass
class _ObjectDataProvider:
    """Class for providing metadata for data objects in fmu-dataio, e.g. a surface.

    The metadata for the 'data' are constructed by:

    * Investigating (parsing) the object (e.g. a XTGeo RegularSurface) itself
    * Combine the object info with user settings, globalconfig and class variables
    * OR
    * investigate current metadata if that is provided
    """

    # input fields
    obj: Any
    dataio: Any
    meta_existing: Optional[dict] = None

    # result properties; the most important is metadata which IS the 'data' part in
    # the resulting metadata. But other variables needed later are also given
    # as instance properties in addition (for simplicity in other classes/functions)
    metadata: dict = field(default_factory=dict, init=False)
    name: str = field(default="", init=False)
    classname: str = field(default="", init=False)
    efolder: str = field(default="", init=False)
    fmt: str = field(default="", init=False)
    extension: str = field(default="", init=False)
    layout: str = field(default="", init=False)
    bbox: dict = field(default_factory=dict, init=False)
    specs: dict = field(default_factory=dict, init=False)
    time0: str = field(default="", init=False)
    time1: str = field(default="", init=False)

    def __post_init__(self) -> None:
        logger.info("Ran __post_init__")

    def _derive_name_stratigraphy(self) -> dict:
        """Derive the name and stratigraphy for the object; may have several sources.

        If not in input settings it is tried to be inferred from the xtgeo/pandas/...
        object. The name is then checked towards the stratigraphy list, and name is
        replaced with official stratigraphic name if found in static metadata
        `stratigraphy`. For example, if "TopValysar" is the model name and the actual
        name is "Valysar Top Fm." that latter name will be used.

        """
        logger.info("Evaluate data:name attribute and stratigraphy")
        result: dict[str, Any] = {}

        name = self.dataio.name

        if not name:
            try:
                name = self.obj.name
            except AttributeError:
                name = ""

        # next check if usename has a "truename" and/or aliases from the config
        strat = self.dataio.config.get("stratigraphy", None)  # shortform

        if strat is None or name not in strat:
            logger.info("None of name not in strat")
            result["stratigraphic"] = False
            result["name"] = name
        else:
            logger.info("The name in strat...")
            result["name"] = strat[name].get("name", name)
            result["alias"] = strat[name].get("alias", [])
            if result["name"] != "name":
                result["alias"].append(name)
            result["stratigraphic"] = strat[name].get("stratigraphic", False)
            result["stratigraphic_alias"] = strat[name].get("stratigraphic_alias", None)
            result["offset"] = strat[name].get("offset", None)
            result["top"] = strat[name].get("top", None)
            result["base"] = strat[name].get("base", None)

        logger.info("Evaluated data:name attribute, true name is <%s>", result["name"])
        return result

    @staticmethod
    def _validate_get_ext(
        fmt: str,
        subtype: str,
        validator: dict[str, Any],
    ) -> object | None:
        """Validate that fmt (file format) matches data and return legal extension."""
        if fmt not in validator:
            raise ConfigurationError(
                f"The file format {fmt} is not supported.",
                f"Valid {subtype} formats are: {list(validator.keys())}",
            )

        return validator.get(fmt, None)

    def _derive_objectdata(self) -> dict:
        """Derive object spesific data."""
        logger.info("Evaluate data settings for object")
        result: dict[str, Any] = {}

        if isinstance(self.obj, xtgeo.RegularSurface):
            result["subtype"] = "RegularSurface"
            result["classname"] = "surface"
            result["layout"] = "regular"
            result["efolder"] = "maps"
            result["fmt"] = self.dataio.surface_fformat
            result["extension"] = self._validate_get_ext(
                result["fmt"],
                result["subtype"],
                _ValidFormats().surface,
            )
            result["spec"], result["bbox"] = self._derive_spec_bbox_regularsurface()

        elif isinstance(self.obj, xtgeo.Polygons):
            result["subtype"] = "Polygons"
            result["classname"] = "polygons"
            result["layout"] = "unset"
            result["efolder"] = "polygons"
            result["fmt"] = self.dataio.polygons_fformat
            result["extension"] = self._validate_get_ext(
                result["fmt"],
                result["subtype"],
                _ValidFormats().polygons,
            )
            result["spec"], result["bbox"] = self._derive_spec_bbox_polygons()

        elif isinstance(self.obj, xtgeo.Points):
            result["subtype"] = "Points"
            result["classname"] = "points"
            result["layout"] = "unset"
            result["efolder"] = "points"
            result["fmt"] = self.dataio.points_fformat
            result["extension"] = self._validate_get_ext(
                result["fmt"],
                result["subtype"],
                _ValidFormats().points,
            )
            result["spec"], result["bbox"] = self._derive_spec_bbox_points()

        elif isinstance(self.obj, xtgeo.Cube):
            result["subtype"] = "RegularCube"
            result["classname"] = "cube"
            result["layout"] = "regular"
            result["efolder"] = "cubes"
            result["fmt"] = self.dataio.cube_fformat
            result["extension"] = self._validate_get_ext(
                result["fmt"],
                result["subtype"],
                _ValidFormats().cube,
            )
            result["spec"], result["bbox"] = self._derive_spec_bbox_cube()

        elif isinstance(self.obj, xtgeo.Grid):
            result["subtype"] = "CPGrid"
            result["classname"] = "cpgrid"
            result["layout"] = "cornerpoint"
            result["efolder"] = "grids"
            result["fmt"] = self.dataio.grid_fformat
            result["extension"] = self._validate_get_ext(
                result["fmt"],
                result["subtype"],
                _ValidFormats().grid,
            )
            result["spec"], result["bbox"] = self._derive_spec_bbox_cpgrid()

        elif isinstance(self.obj, xtgeo.GridProperty):
            result["subtype"] = "CPGridProperty"
            result["classname"] = "cpgrid_property"
            result["layout"] = "cornerpoint"
            result["efolder"] = "grids"
            result["fmt"] = self.dataio.grid_fformat
            result["extension"] = self._validate_get_ext(
                result["fmt"],
                result["subtype"],
                _ValidFormats().grid,
            )
            result["spec"], result["bbox"] = self._derive_spec_bbox_cpgridproperty()

        elif isinstance(self.obj, pd.DataFrame):
            result["table_index"] = self._derive_index()

            result["subtype"] = "DataFrame"
            result["classname"] = "table"
            result["layout"] = "table"
            result["efolder"] = "tables"
            result["fmt"] = self.dataio.table_fformat
            result["extension"] = self._validate_get_ext(
                result["fmt"],
                result["subtype"],
                _ValidFormats().table,
            )
            result["spec"], result["bbox"] = self._derive_spec_bbox_dataframe()

        elif isinstance(self.obj, dict):
            result["subtype"] = "JSON"
            result["classname"] = "dictionary"
            result["layout"] = "dictionary"
            result["efolder"] = "dictionaries"
            result["fmt"] = self.dataio.dict_fformat
            result["extension"] = self._validate_get_ext(
                result["fmt"],
                result["subtype"],
                _ValidFormats().dictionary,
            )
            result["spec"], result["bbox"] = self._derive_spec_bbox_dict()

        else:
            from pyarrow import Table

            if isinstance(self.obj, Table):
                result["table_index"] = self._derive_index()

                result["subtype"] = "ArrowTable"
                result["classname"] = "table"
                result["layout"] = "table"
                result["efolder"] = "tables"
                result["fmt"] = self.dataio.arrow_fformat
                result["extension"] = self._validate_get_ext(
                    result["fmt"],
                    result["subtype"],
                    _ValidFormats().table,
                )
                result["spec"], result["bbox"] = self._derive_spec_bbox_arrowtable()
            else:
                raise NotImplementedError(
                    "This data type is not (yet) supported: ", type(self.obj)
                )

        # override efolder with forcefolder as exception!
        if self.dataio.forcefolder and not self.dataio.forcefolder.startswith("/"):
            ewas = result["efolder"]
            result["efolder"] = self.dataio.forcefolder
            msg = (
                f"The standard folder name is overrided from {ewas} to "
                f"{self.dataio.forcefolder}"
            )
            logger.info(msg)
            warn(msg, UserWarning)

        return result

    def _derive_spec_bbox_regularsurface(self) -> tuple[dict, dict]:
        """Process/collect the data.spec and data.bbox for RegularSurface"""
        logger.info("Derive bbox and specs for RegularSurface")
        regsurf = self.obj

        specs = {}
        bbox = {}

        xtgeo_specs = regsurf.metadata.required
        for spec, val in xtgeo_specs.items():
            if isinstance(val, (np.float32, np.float64)):
                val = float(val)
            specs[spec] = val
        specs["undef"] = 1.0e30  # irap binary undef

        bbox["xmin"] = float(regsurf.xmin)
        bbox["xmax"] = float(regsurf.xmax)
        bbox["ymin"] = float(regsurf.ymin)
        bbox["ymax"] = float(regsurf.ymax)
        bbox["zmin"] = float(regsurf.values.min())
        bbox["zmax"] = float(regsurf.values.max())

        return specs, bbox

    def _derive_spec_bbox_polygons(self) -> tuple[dict, dict]:
        """Process/collect the data.spec and data.bbox for Polygons"""
        logger.info("Derive bbox and specs for Polygons")
        poly = self.obj

        specs = {}
        bbox = {}
        # number of polygons:
        specs["npolys"] = np.unique(
            poly.get_dataframe(copy=False)[poly.pname].values
        ).size
        xmin, xmax, ymin, ymax, zmin, zmax = poly.get_boundary()

        bbox["xmin"] = float(xmin)
        bbox["xmax"] = float(xmax)
        bbox["ymin"] = float(ymin)
        bbox["ymax"] = float(ymax)
        bbox["zmin"] = float(zmin)
        bbox["zmax"] = float(zmax)
        return specs, bbox

    def _derive_spec_bbox_points(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Process/collect the data.spec and data.bbox for Points"""
        logger.info("Derive bbox and specs for Points")
        pnts = self.obj

        specs: dict[str, Any] = {}

        bbox: dict[str, Any] = {}

        if len(pnts.get_dataframe(copy=False).columns) > 3:
            attrnames = pnts.get_dataframe(copy=False).columns[3:]
            specs["attributes"] = list(attrnames)
        specs["size"] = int(pnts.get_dataframe(copy=False).size)

        bbox["xmin"] = float(pnts.get_dataframe(copy=False)[pnts.xname].min())
        bbox["xmax"] = float(pnts.get_dataframe(copy=False)[pnts.xname].max())
        bbox["ymax"] = float(pnts.get_dataframe(copy=False)[pnts.yname].min())
        bbox["ymin"] = float(pnts.get_dataframe(copy=False)[pnts.yname].max())
        bbox["zmin"] = float(pnts.get_dataframe(copy=False)[pnts.zname].min())
        bbox["zmax"] = float(pnts.get_dataframe(copy=False)[pnts.zname].max())

        return specs, bbox

    def _derive_spec_bbox_cube(self) -> tuple[dict, dict]:
        """Process/collect the data.spec and data.bbox Cube"""
        logger.info("Derive bbox and specs for Cube")
        cube = self.obj

        specs = {}
        bbox = {}

        xtgeo_specs = cube.metadata.required
        for spec, val in xtgeo_specs.items():
            if isinstance(val, (np.float32, np.float64)):
                val = float(val)
            specs[spec] = val

        # current xtgeo is missing xmin, xmax etc attributes for cube, so need
        # to compute (simplify when xtgeo has this):
        xmin = 1.0e23
        ymin = xmin
        xmax = -1 * xmin
        ymax = -1 * ymin

        for corner in ((1, 1), (1, cube.nrow), (cube.ncol, 1), (cube.ncol, cube.nrow)):
            xco, yco = cube.get_xy_value_from_ij(*corner)
            xmin = xco if xco < xmin else xmin
            xmax = xco if xco > xmax else xmax
            ymin = yco if yco < ymin else ymin
            ymax = yco if yco > ymax else ymax

        bbox["xmin"] = float(xmin)
        bbox["xmax"] = float(xmax)
        bbox["ymin"] = float(ymin)
        bbox["ymax"] = float(ymax)
        bbox["zmin"] = float(cube.zori)
        bbox["zmax"] = float(cube.zori + cube.zinc * (cube.nlay - 1))

        return specs, bbox

    def _derive_spec_bbox_cpgrid(self) -> tuple[dict, dict]:
        """Process/collect the data.spec and data.bbox CornerPoint Grid geometry"""
        logger.info("Derive bbox and specs for Gride (geometry)")
        grid = self.obj

        specs = {}
        bbox = {}

        xtgeo_specs = grid.metadata.required
        for spec, val in xtgeo_specs.items():
            if isinstance(val, (np.float32, np.float64)):
                val = float(val)
            specs[spec] = val

        geox = grid.get_geometrics(cellcenter=False, allcells=True, return_dict=True)

        bbox["xmin"] = round(float(geox["xmin"]), 4)
        bbox["xmax"] = round(float(geox["xmax"]), 4)
        bbox["ymin"] = round(float(geox["ymin"]), 4)
        bbox["ymax"] = round(float(geox["ymax"]), 4)
        bbox["zmin"] = round(float(geox["zmin"]), 4)
        bbox["zmax"] = round(float(geox["zmax"]), 4)
        return specs, bbox

    def _derive_spec_bbox_cpgridproperty(self) -> tuple[dict, dict]:
        """Process/collect the data.spec and data.bbox GridProperty"""
        logger.info("Derive bbox and specs for GridProperty")
        gridprop = self.obj

        specs: dict[str, Any] = {}
        bbox: dict[str, Any] = {}

        specs["ncol"] = gridprop.ncol
        specs["nrow"] = gridprop.nrow
        specs["nlay"] = gridprop.nlay
        return specs, bbox

    def _derive_spec_bbox_dataframe(
        self,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
    ]:
        """Process/collect the data items for DataFrame."""
        logger.info("Process data metadata for DataFrame (tables)")
        dfr = self.obj

        specs: dict[str, Any] = {}
        bbox: dict[str, Any] = {}

        specs["columns"] = list(dfr.columns)
        specs["size"] = int(dfr.size)

        return specs, bbox

    def _derive_spec_bbox_arrowtable(
        self,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
    ]:
        """Process/collect the data items for Arrow table."""
        logger.info("Process data metadata for arrow (tables)")
        table = self.obj

        specs: dict[str, Any] = {}
        bbox: dict[str, Any] = {}

        specs["columns"] = list(table.column_names)
        specs["size"] = table.num_columns * table.num_rows

        return specs, bbox

    def _derive_spec_bbox_dict(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Process/collect the data items for dictionary."""
        logger.info("Process data metadata for dictionary")
        return {}, {}

    def _get_columns(self) -> list[str]:
        """Get the columns from table"""
        if isinstance(self.obj, pd.DataFrame):
            logger.debug("pandas")
            columns = list(self.obj.columns)
        else:
            logger.debug("arrow")
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

    def _derive_timedata(self) -> dict:
        """Format input timedata to metadata."""

        tdata = self.dataio.timedata
        if not tdata:
            return {}

        if self.dataio.legacy_time_format:
            timedata = self._derive_timedata_legacy()
        else:
            timedata = self._derive_timedata_newformat()
        return timedata

    def _derive_timedata_legacy(self) -> dict[str, Any]:
        """Format input timedata to metadata. legacy version."""
        # TODO(JB): Covnert tresult to TypedDict or Dataclass.
        tdata = self.dataio.timedata

        tresult: dict[str, Any] = {}
        tresult["time"] = []
        if len(tdata) == 1:
            elem = tdata[0]
            tresult["time"] = []
            xfield = {"value": dt.strptime(str(elem[0]), "%Y%m%d").isoformat()}
            self.time0 = str(elem[0])
            if len(elem) == 2:
                xfield["label"] = elem[1]
            tresult["time"].append(xfield)
        if len(tdata) == 2:
            elem1 = tdata[0]
            xfield1 = {"value": dt.strptime(str(elem1[0]), "%Y%m%d").isoformat()}
            if len(elem1) == 2:
                xfield1["label"] = elem1[1]

            elem2 = tdata[1]
            xfield2 = {"value": dt.strptime(str(elem2[0]), "%Y%m%d").isoformat()}
            if len(elem2) == 2:
                xfield2["label"] = elem2[1]

            if xfield1["value"] < xfield2["value"]:
                tresult["time"].append(xfield1)
                tresult["time"].append(xfield2)
            else:
                tresult["time"].append(xfield2)
                tresult["time"].append(xfield1)

            self.time0 = tresult["time"][0]["value"]
            self.time1 = tresult["time"][1]["value"]

        logger.info("Timedata: time0 is %s while time1 is %s", self.time0, self.time1)
        return tresult

    def _derive_timedata_newformat(self) -> dict[str, Any]:
        """Format input timedata to metadata, new format.

        When using two dates, input convention is [[newestdate, "monitor"], [oldestdate,
        "base"]] but it is possible to turn around. But in the metadata the output t0
        shall always be older than t1 so need to check, and by general rule the file
        will be some--time1_time0 where time1 is the newest (unless a class variable is
        set for those who wants it turned around).
        """
        tdata = self.dataio.timedata
        tresult: dict[str, Any] = {}

        if len(tdata) == 1:
            elem = tdata[0]
            tresult["t0"] = {}
            xfield = {"value": dt.strptime(str(elem[0]), "%Y%m%d").isoformat()}
            self.time0 = str(elem[0])
            if len(elem) == 2:
                xfield["label"] = elem[1]
            tresult["t0"] = xfield
        if len(tdata) == 2:
            elem1 = tdata[0]
            xfield1 = {"value": dt.strptime(str(elem1[0]), "%Y%m%d").isoformat()}
            if len(elem1) == 2:
                xfield1["label"] = elem1[1]

            elem2 = tdata[1]
            xfield2 = {"value": dt.strptime(str(elem2[0]), "%Y%m%d").isoformat()}
            if len(elem2) == 2:
                xfield2["label"] = elem2[1]

            if xfield1["value"] < xfield2["value"]:
                tresult["t0"] = xfield1
                tresult["t1"] = xfield2
            else:
                tresult["t0"] = xfield2
                tresult["t1"] = xfield1

            self.time0 = tresult["t0"]["value"]
            self.time1 = tresult["t1"]["value"]

        logger.info("Timedata: time0 is %s while time1 is %s", self.time0, self.time1)
        return tresult

    def _derive_from_existing(self) -> None:
        """Derive from existing metadata."""

        # do not change any items in 'data' block, as it may ruin e.g. stratigrapical
        # setting (i.e. changing data.name is not allowed)
        assert self.meta_existing is not None
        self.metadata = self.meta_existing["data"]
        self.name = self.meta_existing["data"]["name"]

        # derive the additional attributes needed later e.g. in Filedata provider:
        relpath = Path(self.meta_existing["file"]["relative_path"])
        if self.dataio.subfolder:
            self.efolder = relpath.parent.parent.name
        else:
            self.efolder = relpath.parent.name

        self.classname = self.meta_existing["class"]
        self.extension = relpath.suffix
        self.fmt = self.meta_existing["data"]["format"]

        # TODO: Clean up types below.
        self.time0, self.time1 = parse_timedata(self.meta_existing["data"])  # type: ignore

    def _process_content(self) -> tuple[str, dict | None]:
        """Work with the `content` metadata"""

        # content == "unset" is not wanted, but in case metadata has been produced while
        # doing a preprocessing step first, and this step is re-using metadata, the
        # check is not done.
        if self.dataio._usecontent == "unset" and (
            self.dataio.reuse_metadata_rule is None
            or self.dataio.reuse_metadata_rule != "preprocessed"
        ):
            warn(
                "The <content> is not provided which defaults to 'unset'. "
                "It is strongly recommended that content is given explicitly! "
                f"\n\nValid contents are: {', '.join(ALLOWED_CONTENTS.keys())} "
                "\n\nThis list can be extended upon request and need.",
                UserWarning,
            )

        content = self.dataio._usecontent
        content_spesific = None

        # Outgoing content is always a string, but it can be given as a dict if content-
        # specific information is to be included in the metadata.
        # In that case, it shall be inserted in the data block as a key with name as the
        # content, e.g. "seismic" or "field_outline"
        if self.dataio._content_specific is not None:
            content_spesific = self.dataio._content_specific

        return content, content_spesific

    def derive_metadata(self) -> None:
        """Main function here, will populate the metadata block for 'data'."""
        logger.info("Derive all metadata for data object...")

        if self.meta_existing:
            self._derive_from_existing()
            return

        nameres = self._derive_name_stratigraphy()
        objres = self._derive_objectdata()

        meta = self.metadata  # shortform

        meta["name"] = nameres["name"]
        meta["stratigraphic"] = nameres.get("stratigraphic", None)
        meta["offset"] = nameres.get("offset", None)
        meta["alias"] = nameres.get("alias", None)
        meta["top"] = nameres.get("top", None)
        meta["base"] = nameres.get("base", None)

        content, content_spesific = self._process_content()
        meta["content"] = content
        if content_spesific:
            meta[self.dataio._usecontent] = content_spesific

        meta["tagname"] = self.dataio.tagname
        meta["format"] = objres["fmt"]
        meta["layout"] = objres["layout"]
        meta["unit"] = self.dataio.unit
        meta["vertical_domain"] = list(self.dataio.vertical_domain.keys())[0]
        meta["depth_reference"] = list(self.dataio.vertical_domain.values())[0]
        meta["spec"] = objres["spec"]
        meta["bbox"] = objres["bbox"]
        meta["table_index"] = objres.get("table_index")
        meta["undef_is_zero"] = self.dataio.undef_is_zero

        # timedata:
        tresult = self._derive_timedata()
        if tresult:
            if self.dataio.legacy_time_format:
                for key, val in tresult.items():
                    meta[key] = val
            else:
                meta["time"] = {}
                for key, val in tresult.items():
                    meta["time"][key] = val

        meta["is_prediction"] = self.dataio.is_prediction
        meta["is_observation"] = self.dataio.is_observation
        meta["description"] = generate_description(self.dataio.description)

        # the next is to give addition state variables identical values, and for
        # consistency these are derived after all eventual validation and directly from
        # the self.metadata fields:

        self.name = meta["name"]

        # then there are a few settings that are not in the ``data`` metadata, but
        # needed as data/variables in other classes:

        self.efolder = objres["efolder"]
        self.classname = objres["classname"]
        self.extension = objres["extension"]
        self.fmt = objres["fmt"]
        logger.info("Derive all metadata for data object... DONE")
