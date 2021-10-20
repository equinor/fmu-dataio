"""Private module for Surface IO in DataIO class."""
import json
import logging
import warnings
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

try:
    import pyarrow as pa
except ImportError:
    HAS_PYARROW = False
else:
    HAS_PYARROW = True
    from pyarrow import feather

import xtgeo

from . import _utils

VALID_SURFACE_FORMATS = {"irap_binary": ".gri"}
VALID_GRID_FORMATS = {"hdf": ".hdf", "roff": ".roff"}
VALID_CUBE_FORMATS = {"segy": ".segy"}
VALID_TABLE_FORMATS = {"hdf": ".hdf", "csv": ".csv", "arrow": ".arrow"}
VALID_POLYGONS_FORMATS = {"hdf": ".hdf", "csv": ".csv", "irap_ascii": ".pol"}


# the content must conform with the given json schema, e.g.
# https://github.com/equinor/fmu-metadata/blob/dev/definitions/*/schema/fmu_results.json
#
# When value is None, a repeat field shall not be present, otherwise it may be as this:
# content: seismics
# seismics:
#   attribute: mean
#   zrange: 42.0
#   filter_size: 4.0
#   scaling_factor: 1.5

ALLOWED_CONTENTS = {
    "depth": None,
    "time": None,
    "thickness": None,
    "property": {"attribute": str, "is_discrete": bool},
    "seismic": {
        "attribute": str,
        "zrange": float,
        "filter_size": float,
        "scaling_factor": float,
    },
    "fluid_contact": {"contact": str},
    "field_outline": {"contact": str},
    "regions": None,
    "pinchout": None,
    "subcrop": None,
    "fault_lines": None,
    "velocity": None,
    "volumes": None,
    "volumetrics": None,  # or?
    "khproduct": None,
    "timeseries": None,
}

# this setting will set if subkeys is required or not. If not found in list then
# False is assumed.
CONTENTS_REQUIRED = {
    "fluid_contact": {"contact": True},
    "field_outline": {"contact": False},
}

logger = logging.getLogger(__name__)


def _override_arg(obj, vname, proposal, default=None):
    """Return correct argument for export() keys.

    The _ExportItem class can receive args that comes directly from the DataIO class
    attribute *or* from the export function itself. Rules, with examples
    from "name" attribute (obj = dataio):

    * dataio._name == None and name == None => use name
    * dataio._name == "Some" and name == None => use obj._name
    * dataio._name == None and name = "Some" => use name
    * dataio._name == "Some" and name = "Other" => use name

    """
    instance_attr = getattr(obj, "_" + vname)
    logger.info(
        "Instance attribute %s has %s while proposal is %s",
        vname,
        instance_attr,
        proposal,
    )
    result = None

    if instance_attr is default:
        result = proposal

    elif instance_attr is not default and proposal is default:
        result = instance_attr

    elif instance_attr is not default and proposal is not default:
        result = proposal

    return result


class ValidationError(ValueError):
    """Error in validating an item."""


class _ExportItem:
    """Export of the actual data item with metadata."""

    def __init__(
        self,
        dataio,
        obj,
        subfolder=None,
        verbosity="WARNING",
        include_index=False,
        name=None,
        parent=None,
        tagname=None,
        description=None,
        display_name=None,
        unit=None,
        **kwargs,
    ):
        self.dataio = dataio
        self.obj = obj
        self.verbosity = _override_arg(dataio, "verbosity", verbosity)
        self.name = _override_arg(dataio, "name", name)
        self.parent = _override_arg(dataio, "parent", parent)
        self.tagname = _override_arg(dataio, "tagname", tagname)
        self.description = _override_arg(dataio, "description", description)
        self.display_name = _override_arg(dataio, "display_name", display_name)
        self.unit = _override_arg(dataio, "unit", unit)
        self.subfolder = _override_arg(dataio, "subfolder", subfolder)
        self.verbosity = _override_arg(dataio, "verbosity", verbosity)
        self.include_index = _override_arg(
            dataio, "include_index", include_index, default=False
        )
        logger.setLevel(level=self.verbosity)

        self.timedata = self.dataio.timedata  # the a bit complex time input
        self.times = None  # will be populated later as None or list of 2

        if "index" in kwargs:
            self.include_index = kwargs.get(
                "index", self.include_index
            )  # bwcompatibility for deprecated "index"
            warnings.warn(
                "Using 'index' is deprecated and will be removed in future versions, "
                "use 'include_index' instead.",
                DeprecationWarning,
            )
        logger.info("Using Pandas INDEX is %s", self.include_index)

        self.subtype = None
        self.classname = "unset"

        # to be populated later
        self.efolder = "other"
        self.valid = None
        self.fmt = None

        if self.verbosity is None:
            self.verbosity = "WARNING"  # fallback

        self.realfolder = dataio.realfolder
        self.iterfolder = dataio.iterfolder
        self.createfolder = dataio.createfolder

        if subfolder is not None:
            warnings.warn(
                "Exporting to a subfolder is a deviation from the standard "
                "and could have consequences for later dependencies",
                UserWarning,
            )

    def save_to_file(self) -> str:
        """Saving (export) an instance to file with rich metadata for SUMO.

        Many metadata items are object independent and are treated directly in the
        dataio module. Here additional metadata (dependent on this datatype) are
        collected/processed and subsequently both 'independent' and object dependent
        a final metadata file (or part of file if HDF) are collected and
        written to disk here.
        """
        logger.info("Save to file...")
        if isinstance(self.obj, xtgeo.RegularSurface):
            self.subtype = "RegularSurface"
            self.classname = "surface"
            self.efolder = "maps"
            self.valid = VALID_SURFACE_FORMATS
            self.fmt = self.dataio.surface_fformat
        elif isinstance(self.obj, xtgeo.Polygons):
            self.subtype = "Polygons"
            self.classname = "polygons"
            self.efolder = "polygons"
            self.valid = VALID_POLYGONS_FORMATS
            self.fmt = self.dataio.polygons_fformat
        elif isinstance(self.obj, xtgeo.Cube):
            self.subtype = "RegularCube"
            self.classname = "cube"
            self.efolder = "cubes"
            self.valid = VALID_CUBE_FORMATS
            self.fmt = self.dataio.cube_fformat
        elif isinstance(self.obj, xtgeo.Grid):
            self.subtype = "CPGrid"
            self.classname = "cpgrid"
            self.efolder = "grids"
            self.valid = VALID_GRID_FORMATS
            self.fmt = self.dataio.grid_fformat
        elif isinstance(self.obj, xtgeo.GridProperty):
            self.subtype = "CPGridProperty"
            self.classname = "cpgrid_property"
            self.efolder = "grids"
            self.valid = VALID_GRID_FORMATS
            self.fmt = self.dataio.grid_fformat
        elif isinstance(self.obj, pd.DataFrame):
            self.subtype = "DataFrame"
            self.classname = "table"
            self.efolder = "tables"
            self.valid = VALID_TABLE_FORMATS
            self.fmt = self.dataio.table_fformat
        elif HAS_PYARROW and isinstance(self.obj, pa.Table):
            self.subtype = "ArrowTable"
            self.classname = "table"
            self.efolder = "tables"
            self.valid = VALID_TABLE_FORMATS
            self.fmt = self.dataio.arrow_fformat
        else:
            raise NotImplementedError(
                "This data type is not (yet) supported: ", type(self.obj)
            )
        logger.info("Found %s", self.subtype)

        self._data_process()
        self._data_process_object()
        self._fmu_inject_workflow()  # this will vary if surface, table, grid, ...
        self._display()
        fpath = self._item_to_file()
        return str(fpath)

    def _data_process(self):
        """Process som potentially common subfields in the data block.

        These subfields are:
        - name
        - top/base (from context)
        - content
        - time
        - properties? Disabled!
        - context
        - is_observation
        - is_prediction
        - description
        """
        self._data_process_name()
        self._data_process_context()
        self._data_process_content()
        self._data_process_parent()
        self._data_process_timedata()
        self._data_process_various()

    def _data_process_name(self):
        """Process the name  and alos the display_name subfield."""
        # first detect if name is given, or infer name from object if possible
        # then determine if name is stratgraphic and assing a "true" valid name
        logger.info("Evaluate data:name attribute")
        usename = "unknown"
        meta = self.dataio.metadata4data

        if self.name is None or self.name == "unknown":
            try:
                usename = self.obj.name
            except AttributeError:
                warnings.warn(
                    "Cannot get name from object, assume 'unknown'", UserWarning
                )
                usename = "unknown"
        else:
            usename = self.name

        self.name = usename
        # next check if usename has a "truename" and/or aliases from the config
        strat = self.dataio.metadata4strat  # shortform

        logger.debug("self.dataio.metadata4strat is %s", self.dataio.metadata4strat)

        if strat is None or usename not in strat:
            meta["stratigraphic"] = False
            meta["name"] = usename
        else:
            meta["name"] = strat[usename].get("name", usename)
            meta["stratigraphic"] = strat[usename].get("stratigraphic", False)
            meta["alias"] = strat[usename].get("alias", None)
            meta["stratigraphic_alias"] = strat[usename].get(
                "stratigraphic_alias", None
            )
        logger.info(
            "Evaluate data:name attribute done, true name is <%s>", meta["name"]
        )

        if self.display_name is None or self.display_name == "unknown":
            self.display_name = self.name

    def _data_process_context(self):
        """Process the context input which gives offset and top/base settings.

        For example::

          context:
             offset: 3.5

             top:
                ref: TopVolantis
                offset: 2.0
             base:
                ref: BaseVolantis
                offset: 8.3

        The stratigraphic input in fmuconfig may look like this::

          TopVolantis:                    <-- RMS modelling name -> ref
            stratigraphic: true
            name: VOLANTIS GP. Top        <-- SMDA / official name -> name

        So the dilemmea is that in the input, it is natural for the end user
        to use the RMS modelling name, but it may be that the SMDA name also
        is applied? And what if not found? Assume OK or complain? Should one
        validate at all?

        """
        logger.info("Evaluate context (offset, top, base), if any")
        meta = self.dataio.metadata4data
        if self.dataio.context is None:
            logger.info("No context found, which may be ok")
            return  # context data are missing

        rel = self.dataio.context  # shall be a dictionary

        offset = rel.get("offset", None)
        if offset is not None:
            logger.info("Offset is found")
            meta["offset"] = offset

        # top process top and base (both must be present in case)
        top = rel.get("top", None)
        base = rel.get("base", None)
        if top is None or base is None:
            logger.info("context top and/base is missing, skip further")
            return

        topname = rel["top"].get("ref", None)
        basename = rel["base"].get("ref", None)

        if topname is None or basename is None:
            warnings.warn(
                "context top and/base is present but <ref> is missing, skip further",
                UserWarning,
            )
            return

        # finally, validate if top/base name is stratigraphic and set metadata
        group = {"top": topname, "base": basename}
        strat = self.dataio.metadata4strat
        for item, somename in group.items():
            usename = somename
            offset = 0.0
            stratigraphic = False
            if somename in strat:
                logger.info("Found <%s> in stratigraphy", somename)
                usename = strat[somename].get("name", somename)
                stratigraphic = strat[somename].get("stratigraphic", False)
                offset = rel[item].get("offset", 0.0)
            else:
                logger.error("Did not find <%s> in stratigraphy input", somename)
                raise ValueError(f"Cannot find {somename} in stratigraphy input")
            meta[item] = OrderedDict()
            meta[item]["name"] = usename
            meta[item]["stratigraphic"] = stratigraphic
            meta[item]["offset"] = offset

    def _data_process_content(self):
        """Process the content block (within data block) which can complex."""
        logger.info("Evaluate content")
        content = self.dataio.content
        logger.debug("content is %s of type %s", str(content), type(content))
        meta = self.dataio.metadata4data
        usecontent = "unset"
        useextra = None
        if content is None:
            warnings.warn(
                "The <content> is not provided which defaults to 'depth'. "
                "It is strongly recommended that content is given explicitly!",
                UserWarning,
            )
            usecontent = "depth"

        elif isinstance(content, str):
            if content in CONTENTS_REQUIRED:
                raise ValidationError(f"content {content} requires additional input")
            usecontent = content

        elif isinstance(content, dict):
            usecontent = (list(content.keys()))[0]
            useextra = content[usecontent]

        else:
            raise ValidationError("content must be string or dict")

        if usecontent not in ALLOWED_CONTENTS.keys():
            raise ValidationError(
                f"Invalid content: <{usecontent}>! "
                f"Valid content: {', '.join(ALLOWED_CONTENTS.keys())}"
            )

        meta["content"] = usecontent
        logger.debug("outgoing content is set to %s", usecontent)
        if useextra:
            self._data_process_content_validate(usecontent, useextra)
            meta[usecontent] = useextra
        else:
            logger.debug("content has no extra information")
            logger.debug("content was %s", content)

    def _data_process_parent(self):
        """Process the parent block within data block.

        A parent is only required for few datatypes, in particular a GridProperty
        which will need a grid geometry name.
        """
        logger.info("Evaluate parent")
        parent = self.parent
        meta = self.dataio.metadata4data

        if self.classname == "cpgrid_property" and parent is None:
            raise ValidationError("Input 'parent' is required for GridProperty!")
        else:
            if parent is None:
                return

        # evaluate 'parent' which can be a str or a dict
        if isinstance(parent, str):
            meta["parent"] = {"name": parent}
            self.parent = parent
        else:
            if "name" not in parent:
                raise ValidationError("Input 'parent' shall have a 'name' attribute!")
            meta["parent"] = parent
            self.parent = parent["name"]

    @staticmethod
    def _data_process_content_validate(name, fields):
        logger.debug("starting staticmethod _data_process_content_validate")
        valid = ALLOWED_CONTENTS.get(name, None)
        if valid is None:
            raise ValidationError(f"Cannot validate content for <{name}>")

        logger.info("name: %s", name)

        for key, dtype in fields.items():
            if key in valid.keys():
                wanted_type = valid[key]
                if not isinstance(dtype, wanted_type):
                    raise ValidationError(
                        f"Invalid type for <{key}> with value <{dtype}>, not of "
                        f"type <{wanted_type}>"
                    )
            else:
                raise ValidationError(f"Key <{key}> is not valid for <{name}>")

        required = CONTENTS_REQUIRED.get(name, None)
        if isinstance(required, dict):
            rlist = list(required.items())
            logger.info("rlist is %s", rlist)
            logger.info("fields is %s", fields)
            rkey, status = rlist.pop()
            logger.info("rkey not in fields.keys(): %s", str(rkey not in fields.keys()))
            logger.info("rkey: %s", rkey)
            logger.info("fields.keys(): %s", str(fields.keys()))
            if rkey not in fields.keys() and status is True:
                raise ValidationError(
                    f"The subkey <{rkey}> is required for content <{name}> ",
                    "but is not found",
                )

            # if name in CONTENTS_REQUIRED.keys():
            #     if key in CONTENTS_REQUIRED[name] and CONTENTS_REQUIRED[name] is True

    def _data_process_timedata(self):
        """Process the time subfield and also contruct self.times."""
        # first detect if timedata is given, the process it
        logger.info("Evaluate data:name attribute")
        meta = self.dataio.metadata4data

        datelimits = (18140517, 33000101)

        if self.timedata is None:
            return

        self.times = []  # e.g. ["20211102", "20231101"] or ["20211102", None]
        for xtime in self.timedata:
            if isinstance(xtime[0], int):
                if xtime[0] < datelimits[0] or xtime[0] > datelimits[1]:
                    raise ValidationError(
                        "Integer date input seems to be outside reasonable "
                        f"limits: {datelimits}"
                    )
            tdate = str(xtime[0])
            tlabel = None
            if len(xtime) > 1:
                tlabel = xtime[1]
            tdate = tdate.replace("-", "")  # 2021-04-23  -->  20210403
            if tdate and int(tdate) < datelimits[0] or int(tdate) > datelimits[1]:
                raise ValidationError(
                    f"Date input outside reasonable limits: {datelimits}"
                )
            tdate = datetime.strptime(tdate, "%Y%m%d")
            self.times.append(tdate)
            tdate = tdate.strftime("%Y-%m-%dT%H:%M:%S")
            if "time" not in meta:
                meta["time"] = list()
            usetime = OrderedDict()
            usetime["value"] = tdate
            if tlabel:
                usetime["label"] = tlabel
            meta["time"].append(usetime)

    def _data_process_various(self):
        """Process "all the rest" of the generic items.

        i.e.::
            unit,
            vertical_domain
            depth_reference
            properties  (as tmp)
            grid_model
            is_prediction
            is_observation
        """
        logger.info("Process various general items in data block")
        meta = self.dataio.metadata4data
        meta["unit"] = self.unit
        (meta["vertical_domain"], meta["depth_reference"],) = list(
            self.dataio.vertical_domain.items()
        )[0]
        meta["is_prediction"] = self.dataio.is_prediction
        meta["is_observation"] = self.dataio.is_observation

        # tmp solution for properties
        # meta["properties"] = list()
        # props = OrderedDict()
        # props["name"] = "SomeName"
        # props["attribute"] = "SomeAttribute"
        # props["is_discrete"] = False
        # props["calculation"] = None
        # meta["properties"].append(props)

        # tmp:
        meta["grid_model"] = None

        # tmp:
        if self.description is not None:
            meta["description"] = self.description

    def _data_process_object(self):
        """Process data fileds which are object dependent.

        I.e::

            layout
            spec
            bbox

        Note that 'format' field will be added in _item_to_file
        """

        if self.subtype == "RegularSurface":
            self._data_process_object_regularsurface()
        elif self.subtype == "RegularCube":
            self._data_process_object_regularcube()
        elif self.subtype == "CPGrid":
            self._data_process_cpgrid()
        elif self.subtype == "CPGridProperty":
            self._data_process_cpgridproperty()
        elif self.subtype == "Polygons":
            self._data_process_object_polygons()
        elif self.subtype == "DataFrame":
            self._data_process_object_dataframe()
        elif self.subtype == "ArrowTable":
            self._data_process_object_arrowtable()

    def _data_process_cpgrid(self):
        """Process/collect the data items for Corner Point Grid"""
        logger.info("Process data metadata for CP Grid")

        dataio = self.dataio
        grid = self.obj

        meta = dataio.metadata4data  # shortform

        meta["layout"] = "cornerpoint"

        # define spec record
        specs = grid.metadata.required
        newspecs = OrderedDict()
        for spec, val in specs.items():
            if isinstance(val, (np.float32, np.float64)):
                val = float(val)
            newspecs[spec] = val
        meta["spec"] = newspecs

        geox = grid.get_geometrics(cellcenter=False, allcells=True, return_dict=True)

        meta["bbox"] = OrderedDict()
        meta["bbox"]["xmin"] = round(float(geox["xmin"]), 4)
        meta["bbox"]["xmax"] = round(float(geox["xmax"]), 4)
        meta["bbox"]["ymin"] = round(float(geox["ymin"]), 4)
        meta["bbox"]["ymax"] = round(float(geox["ymax"]), 4)
        meta["bbox"]["zmin"] = round(float(geox["zmin"]), 4)
        meta["bbox"]["zmax"] = round(float(geox["zmax"]), 4)
        logger.info("Process data metadata for Grid... done!!")

    def _data_process_cpgridproperty(self):
        """Process/collect the data items for Corner Point GridProperty"""
        logger.info("Process data metadata for CPGridProperty")

        dataio = self.dataio
        gridprop = self.obj

        meta = dataio.metadata4data  # shortform

        meta["layout"] = "cornerpoint_property"

        # define spec record
        specs = OrderedDict()
        specs["ncol"] = gridprop.ncol
        specs["nrow"] = gridprop.nrow
        specs["nlay"] = gridprop.nlay
        meta["spec"] = specs

        logger.info("Process data metadata for GridProperty... done!!")

    def _data_process_object_regularsurface(self):
        """Process/collect the data items for RegularSurface"""
        logger.info("Process data metadata for RegularSurface")

        dataio = self.dataio
        regsurf = self.obj

        meta = dataio.metadata4data  # shortform

        meta["layout"] = "regular"

        # define spec record
        specs = regsurf.metadata.required
        newspecs = OrderedDict()
        for spec, val in specs.items():
            if isinstance(val, (np.float32, np.float64)):
                val = float(val)
            newspecs[spec] = val
        meta["spec"] = newspecs
        meta["spec"]["undef"] = 1.0e30  # irap binary undef

        meta["bbox"] = OrderedDict()
        meta["bbox"]["xmin"] = float(regsurf.xmin)
        meta["bbox"]["xmax"] = float(regsurf.xmax)
        meta["bbox"]["ymin"] = float(regsurf.ymin)
        meta["bbox"]["ymax"] = float(regsurf.ymax)
        meta["bbox"]["zmin"] = float(regsurf.values.min())
        meta["bbox"]["zmax"] = float(regsurf.values.max())
        logger.info("Process data metadata for RegularSurface... done!!")

    def _data_process_object_regularcube(self):
        """Process/collect the data items for RegularCube"""
        logger.info("Process data metadata for RegularCube")

        dataio = self.dataio
        cube = self.obj

        meta = dataio.metadata4data  # shortform

        meta["layout"] = "regular"

        # define spec record
        specs = cube.metadata.required
        newspecs = OrderedDict()
        for spec, val in specs.items():
            if isinstance(val, (np.float32, np.float64)):
                val = float(val)
            newspecs[spec] = val
        meta["spec"] = newspecs

        meta["bbox"] = OrderedDict()

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

        meta["bbox"]["xmin"] = xmin
        meta["bbox"]["xmax"] = xmax
        meta["bbox"]["ymin"] = ymin
        meta["bbox"]["ymax"] = ymax
        meta["bbox"]["zmin"] = float(cube.zori)
        meta["bbox"]["zmax"] = float(cube.zori + cube.zinc * (cube.nlay - 1))
        logger.info("Process data metadata for RegularCube... done!!")

    def _data_process_object_polygons(self):
        """Process/collect the data items for Polygons"""
        logger.info("Process data metadata for Polygons/Polylines")

        dataio = self.dataio
        poly = self.obj

        meta = dataio.metadata4data  # shortform
        meta["spec"] = OrderedDict()
        # number of polygons:
        meta["spec"]["npolys"] = np.unique(poly.dataframe[poly.pname].values).size
        xmin, xmax, ymin, ymax, zmin, zmax = poly.get_boundary()

        meta["bbox"] = OrderedDict()
        meta["bbox"]["xmin"] = float(xmin)
        meta["bbox"]["xmax"] = float(xmax)
        meta["bbox"]["ymin"] = float(ymin)
        meta["bbox"]["ymax"] = float(ymax)
        meta["bbox"]["zmin"] = float(zmin)
        meta["bbox"]["zmax"] = float(zmax)
        logger.info("Process data metadata for Polygons... done!!")

    def _data_process_object_dataframe(self):
        """Process/collect the data items for DataFrame."""
        logger.info("Process data metadata for DataFrame (tables)")

        dataio = self.dataio
        dfr = self.obj

        meta = dataio.metadata4data  # shortform

        meta["layout"] = "table"

        # define spec record
        meta["spec"] = OrderedDict()
        meta["spec"]["columns"] = list(dfr.columns)
        meta["spec"]["size"] = int(dfr.size)

        meta["bbox"] = None
        logger.info("Process data metadata for DataFrame... done!!")

    def _data_process_object_arrowtable(self):
        """Process/collect the data items for pa.Table"""
        logger.info("Process data metadata for ArrowTables (tables)")

        dataio = self.dataio
        table = self.obj
        meta = dataio.metadata4data  # shortform

        meta["layout"] = "table"

        # define spec record
        meta["spec"] = OrderedDict()
        meta["spec"]["columns"] = list(table.column_names)
        meta["spec"]["size"] = table.num_columns * table.num_rows

        meta["bbox"] = None
        logger.info("Process data metadata for ArrowTable... done!!")

    def _fmu_inject_workflow(self):
        """Inject workflow into fmu metadata block."""
        self.dataio.metadata4fmu["workflow"] = self.dataio.workflow

    def _display(self):
        """Process common subfields in the display block.

        For now, this is simply injecting a skeleton with loose
        defaults. We might want to be more elaborate in the future.

        Pending discussions and learning from usage.

        The main 'name' attribute may be related to master-data and/or
        be a reference to other things, hence it cannot be prettified
        for display on maps. The display.name serves this purpose.

        display.name can be set through the display_name argument to
        fmu.dataio.ExportData. If not set, the first fallback is the
        name argument. If that is not set either, the last fallback is
        the object name. If that is not set, display.name will be exported
        as None/null.

        The main concept followed for now is that the visualising client
        is to take the most responsibility for how a data object is
        visualized.

        """

        logger.info("Processing display")
        meta = self.dataio.metadata4display

        # display.name
        if self.display_name is not None:
            # first choice: display_name argument
            logger.debug("display.name is set from arguments")
            meta["name"] = self.display_name
        elif self.name is not None:
            # second choice: name argument
            logger.debug("display.name is set to name argument as fallback")
            meta["name"] = self.name
        else:
            # third choice: object name, unless the XTgeo default "unknown"
            try:
                meta["name"] = self.obj.name
                logger.debug("display.name is set to object name as fallback")

                if meta["name"] == "unknown":
                    logger.debug("Got default object name from XTgeo, changing to None")
                    meta["name"] = None
            except AttributeError:
                logger.debug("display.name could not be set")
                meta["name"] = None

        logger.info("Processing display is done!")

    def _item_to_file(self):
        logger.info("Export item to file...")
        logger.debug("Subtype is %s", self.subtype)

        # fstem is filename without suffix
        fstem, fpath = self._construct_filename_fmustandard1()

        if self.fmt not in self.valid.keys():
            raise ValueError(
                f"The file format {self.fmt} is not supported.",
                f"Valid {self.subtype} formats are: {list(self.valid.keys())}",
            )

        ext = self.valid.get(self.fmt, None)
        if ext is None:
            raise RuntimeError(f"Cannot get correct file extension for {self.fmt}")

        outfile, metafile, relpath, abspath = self._verify_path(fstem, fpath, ext)

        self._export_actual_object(outfile, metafile, relpath, abspath)

        return abspath

    def _construct_filename_fmustandard1(self):
        """Construct filename stem according to datatype (class) and fmu style 1.

        fmu style/standard 1:

            surface:
                namehorizon--tagname
                namehorizon--tagname--t1
                namehorizon--tagname--t1_t2  # t1 is monitor time while t2 is base time

                e.g.
                topvolantis--ds_gf_extracted
                therys--facies_fraction_lowershoreface

            grid (geometry):
                gridname

            gridproperty
                gridname--proptagname
                gridname--tagname--t1
                gridname--tagname--t1_t2

                e.g.
                geogrid_valysar--phit

        Destinations accoring to datatype.

        For timedata with two dates, the standard is some--monitortime_basetime. Hence
        t1 is newer than t2.

        Removing dots from filename: Currently, when multiple dots in a filename stem,
        XTgeo, using pathlib, will interpret the part after the last dot as the file
        suffix, and remove it. This causes errors in the output filenames. While this is
        being taken care of in XTgeo, we temporarily sanitize dots from the outgoing
        filename only to avoid this.

        Space will also be replaced in file names.

        Returns stem for file name and destination
        """
        stem = "unset"
        outroot = self.dataio.runpath / "share" / "results"
        loc = self.efolder

        stem = self.name.lower()

        if self.tagname:
            stem += "--" + self.tagname.lower()

        if self.parent:
            stem = self.parent.lower() + "--" + stem

        if self.times:
            time0 = self.times[0]
            time1 = self.times[1]
            if time0 and not time1:
                stem += "--" + (str(time0)[0:10]).replace("-", "")

            elif time0 and time1:
                monitor = (str(time0)[0:10]).replace("-", "")
                base = (str(time1)[0:10]).replace("-", "")
                if monitor == base:
                    warnings.warn(
                        "The monitor date and base date are equal", UserWarning
                    )  # TODO: consider add clocktimes in such cases?
                stem += "--" + monitor + "_" + base

        stem = stem.replace(".", "_").replace(" ", "_")

        dest = outroot / loc

        if self.subfolder:
            dest = dest / self.subfolder

        dest.mkdir(parents=True, exist_ok=True)

        return stem, dest

    def _verify_path(
        self, filestem: str, filepath: Path, ext: str, dryrun=False
    ) -> Tuple[Path, Path, Path, Path]:
        """Combine file name, extensions, etc, verify paths and return cleaned items."""

        logger.info("Incoming file stem is %s", filestem)
        logger.info("Incoming file path is %s", filepath)
        logger.info("Incoming ext is %s", ext)

        path = Path(filepath) / filestem.lower()
        path = path.with_suffix(path.suffix + ext)
        # resolve() will fix ".." e.g. change /some/path/../other to /some/other
        abspath = path.resolve()

        logger.info("Path with suffix is %s", path)
        logger.info("Absolute path (resolved) is %s", abspath)
        logger.info("The RUNPATH is %s", self.dataio.runpath)

        if not dryrun:
            if path.parent.exists():
                logger.info("Folder exists")
            else:
                # this folder should have been made in _construct_filename...
                raise IOError(f"Folder {str(path.parent)} is not present.")

        # create metafile path
        metapath = (
            (Path(filepath) / ("." + filestem.lower())).with_suffix(ext + ".yml")
        ).resolve()

        # get the relative path (relative to runptah if interactive, and to casedir
        # if this is an ERT run)

        useroot = self.dataio.runpath.resolve()
        logger.info("The useroot (initial) is %s", useroot)
        if self.iterfolder:
            useroot = (useroot / "../..").resolve()
            logger.info("The useroot (updated) is %s", useroot)

        relpath = abspath.relative_to(useroot)

        path = path.absolute()  # may contain "../.." in path (not resolved)
        logger.info("Full path to the actual file is: %s", path)
        logger.info("Full path to the actual file is (resolved): %s", abspath)
        logger.info("Full path to the metadata file (if used) is: %s", metapath)
        logger.info("Relative path to actual file: %s", relpath)

        return path, metapath, relpath, abspath

    def _export_actual_object(self, outfile, metafile, relpath, abspath):
        """Export to file, dependent on format and object type."""

        if "irap" in self.fmt and self.subtype == "RegularSurface":
            self.obj.to_file(outfile, fformat="irap_binary")
            self.dataio.metadata4data["format"] = "irap_binary"
        elif "segy" in self.fmt:
            self.obj.to_file(outfile, fformat="segy")
            self.dataio.metadata4data["format"] = "segy"
        elif "roff" in self.fmt:
            self.obj.to_file(outfile, fformat="roff")
            self.dataio.metadata4data["format"] = "roff"
        elif "csv" in self.fmt and self.subtype == "Polygons":
            renamings = {"X_UTME": "X", "Y_UTMN": "Y", "Z_TVDSS": "Z", "POLY_ID": "ID"}
            worker = self.obj.dataframe.copy()
            worker.rename(columns=renamings, inplace=True)
            worker.to_csv(outfile, index=False)
            self.dataio.metadata4data["format"] = "csv"
        elif "irap_ascii" in self.fmt and self.subtype == "Polygons":
            self.obj.to_file(outfile)
            self.dataio.metadata4data["format"] = "irap_ascii"
        elif self.fmt == "csv" and self.subtype == "DataFrame":
            logger.info("Exporting table as csv, with INDEX %s", self.include_index)
            self.obj.to_csv(outfile, index=self.include_index)
            self.dataio.metadata4data["format"] = "csv"
        elif self.fmt == "arrow":
            logger.info("Exporting table as arrow")
            # comment taken from equinor/webviz_subsurface/smry2arrow.py

            # Writing here is done through the feather import, but could also be
            # done using pa.RecordBatchFileWriter.write_table() with a few
            # pa.ipc.IpcWriteOptions(). It is convenient to use feather since it
            # has ready configured defaults and the actual file format is the same
            # (https://arrow.apache.org/docs/python/feather.html)
            feather.write_feather(self.obj, dest=outfile)
            self.dataio.metadata4data["format"] = "arrow"
        else:
            raise TypeError(f"Exporting {self.fmt} for {self.subtype} is not supported")

        # metadata:
        self._item_to_file_create_file_block(outfile, relpath, abspath)
        allmeta = self._item_to_file_collect_all_metadata()
        _utils.export_metadata_file(
            metafile, allmeta, verbosity=self.verbosity, savefmt=self.dataio.meta_format
        )

        return str(outfile)

    def _item_to_file_collect_all_metadata(self):
        """Process all metadata for actual instance."""
        logger.info("Collect all metadata")

        dataio = self.dataio
        allmeta = OrderedDict()

        for dollar in dataio.metadata4dollars.keys():
            allmeta[dollar] = dataio.metadata4dollars[dollar]

        allmeta["class"] = self.classname
        allmeta["file"] = dataio.metadata4file
        allmeta["access"] = dataio.metadata4access
        allmeta["masterdata"] = dataio.metadata4masterdata
        allmeta["tracklog"] = dataio.metadata4tracklog
        allmeta["fmu"] = dataio.metadata4fmu
        allmeta["data"] = dataio.metadata4data
        allmeta["display"] = dataio.metadata4display
        logger.debug("\n%s", json.dumps(allmeta, indent=2, default=str))

        logger.info("Collect all metadata, done")
        return allmeta

    def _item_to_file_create_file_block(self, outfile, relpath, abspath):
        """Process the file block.

        The file block contains relative and absolute paths, file size
        and md5 checksum. This function receives the paths, calculates
        size and checksum, and populates the file block by inserting
        directly to the premade dataio.metadata4file.

        """

        self.dataio.metadata4file["relative_path"] = str(relpath)
        self.dataio.metadata4file["absolute_path"] = str(abspath)

        md5sum = _utils.md5sum(outfile)
        self.dataio.metadata4file["checksum_md5"] = md5sum

        size_bytes = _utils.size(outfile)
        self.dataio.metadata4file["size_bytes"] = size_bytes
