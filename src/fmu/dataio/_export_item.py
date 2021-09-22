"""Private module for Surface IO in DataIO class."""
import json
import logging
import warnings
from collections import OrderedDict
from datetime import datetime

import numpy as np
import pandas as pd
import pyarrow as pa
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


class ValidationError(ValueError):
    pass


class _ExportItem:  # pylint disable=too-few-public-methods
    """Export of the actual data item with metadata."""

    def __init__(self, dataio, obj, subfolder=None, verbosity="warning", index=False):
        self.dataio = dataio
        self.obj = obj
        self.subfolder = subfolder
        self.verbosity = verbosity
        self.index_df = index
        self.subtype = None
        self.classname = "unset"
        self.name = "unknown"
        self.parent_name = None

        if self.verbosity is None:
            self.verbosity = self.dataio._verbosity

        logger.setLevel(level=self.verbosity)

        if self.dataio._name is not None:
            self.name = self.dataio._name
        else:
            try:
                self.name = self.obj.name
            except AttributeError:
                pass

        if self.name is None:
            self.name = "unknown"

        if subfolder is not None:
            warnings.warn(
                "Exporting to a subfolder is a deviation from the standard "
                "and could have consequences for later dependencies",
                UserWarning,
            )

    def save_to_file(self) -> str:
        """Saving an instance to file with rich metadata for SUMO.

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
        elif isinstance(self.obj, xtgeo.Polygons):
            self.subtype = "Polygons"
            self.classname = "polygons"
        elif isinstance(self.obj, xtgeo.Cube):
            self.subtype = "RegularCube"
            self.classname = "cube"
        elif isinstance(self.obj, xtgeo.Grid):
            self.subtype = "CPGrid"
            self.classname = "cpgrid"
        elif isinstance(self.obj, xtgeo.GridProperty):
            self.subtype = "CPGridProperty"
            self.classname = "cpgrid_property"
        elif isinstance(self.obj, pd.DataFrame):
            self.subtype = "DataFrame"
            self.classname = "table"
        elif isinstance(self.obj, pa.Table):
            self.subtype = "ArrowTable"
            self.classname = "table"
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
        return fpath

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
        """Process the name subfield."""
        # first detect if name is given, or infer name from object if possible
        # then determine if name is stratgraphic and assing a "true" valid name
        logger.info("Evaluate data:name attribute")
        usename = "unknown"
        meta = self.dataio._meta_data

        if self.dataio._name is None:
            try:
                usename = self.obj._name
            except AttributeError:
                warnings.warn("Cannot set name", UserWarning)
        else:
            usename = self.dataio._name

        # next check if usename has a "truename" and/or aliases from the config
        strat = self.dataio._meta_strat  # shortform

        logger.debug("self.dataio._meta_strat is %s", self.dataio._meta_strat)

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
        meta = self.dataio._meta_data
        if self.dataio._context is None:
            logger.info("No context found, which may be ok")
            return  # context data are missing

        rel = self.dataio._context  # shall be a dictionary

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
        strat = self.dataio._meta_strat
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
        content = self.dataio._content
        logger.debug("content is %s of type %s", str(content), type(content))
        meta = self.dataio._meta_data
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
            if content in CONTENTS_REQUIRED.keys():
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
        parent = self.dataio._parent
        meta = self.dataio._meta_data

        if self.classname == "cpgrid_property" and parent is None:
            raise ValidationError("Input 'parent' is required for GridProperty!")
        else:
            if parent is None:
                return

        # evaluate 'parent' which can be a str or a dict
        if isinstance(parent, str):
            meta["parent"] = {"name": parent}
            self.parent_name = parent
        else:
            if "name" not in parent:
                raise ValidationError("Input 'parent' shall have a 'name' attribute!")
            meta["parent"] = parent
            self.parent_name = parent["name"]

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
        """Process the time subfield."""
        # first detect if timedata is given, the process it
        logger.info("Evaluate data:name attribute")
        meta = self.dataio._meta_data
        timedata = self.dataio._timedata
        if timedata is None:
            return

        for xtime in timedata:
            tdate = str(xtime[0])
            tlabel = None
            if len(xtime) > 1:
                tlabel = xtime[1]
            tdate = tdate.replace("-", "")  # 2021-04-23  -->  20210403
            tdate = datetime.strptime(tdate, "%Y%m%d")
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
        meta = self.dataio._meta_data
        meta["unit"] = self.dataio._unit
        (meta["vertical_domain"], meta["depth_reference"],) = list(
            self.dataio._vertical_domain.items()
        )[0]
        meta["is_prediction"] = self.dataio._is_prediction
        meta["is_observation"] = self.dataio._is_observation

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
        if self.dataio._description is not None:
            meta["description"] = self.dataio._description

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

        meta = dataio._meta_data  # shortform

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

        meta = dataio._meta_data  # shortform

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

        meta = dataio._meta_data  # shortform

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

        meta = dataio._meta_data  # shortform

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
            xc, yc = cube.get_xy_value_from_ij(*corner)
            xmin = xc if xc < xmin else xmin
            xmax = xc if xc > xmax else xmax
            ymin = yc if yc < ymin else ymin
            ymax = yc if yc > ymax else ymax

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

        meta = dataio._meta_data  # shortform
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

        meta = dataio._meta_data  # shortform

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
        meta = dataio._meta_data  # shortform

        meta["layout"] = "table"

        # define spec record
        meta["spec"] = OrderedDict()
        meta["spec"]["columns"] = list(table.column_names)
        meta["spec"]["size"] = table.num_columns * table.num_rows

        meta["bbox"] = None
        logger.info("Process data metadata for ArrowTable... done!!")

    def _fmu_inject_workflow(self):
        """Inject workflow into fmu metadata block."""
        self.dataio._meta_fmu["workflow"] = self.dataio._workflow

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
        meta = self.dataio._meta_display

        # display.name
        if self.dataio._display_name is not None:
            # first choice: display_name argument
            logger.debug("display.name is set from arguments")
            meta["name"] = self.dataio._display_name
        elif self.dataio._name is not None:
            # second choice: name argument
            logger.debug("display.name is set to name argument as fallback")
            meta["name"] = self.dataio._name
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
        logger.debug(f"subtype is {self.subtype}")
        if self.subtype == "RegularSurface":
            fpath = self._item_to_file_regularsurface()
        elif self.subtype == "RegularCube":
            fpath = self._item_to_file_cube()
        elif self.subtype == "Polygons":
            fpath = self._item_to_file_polygons()
        elif self.subtype in ("CPGrid", "CPGridProperty"):
            fpath = self._item_to_file_gridlike()
        elif self.subtype in ("DataFrame", "ArrowTable"):
            fpath = self._item_to_file_table()
        return fpath

    def _item_to_file_regularsurface(self):
        """Write RegularSurface to file"""
        logger.info("Export %s to file...", self.subtype)
        dataio = self.dataio  # shorter
        obj = self.obj

        if isinstance(dataio._tagname, str):
            attr = dataio._tagname.lower().replace(" ", "_")
        else:
            attr = None

        fname, fpath = _utils.construct_filename(
            self.name,
            pretagname=None,
            tagname=attr,
            subfolder=self.subfolder,
            loc="surface",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        fmt = dataio.surface_fformat

        if fmt not in VALID_SURFACE_FORMATS.keys():
            raise ValueError(
                f"The file format {fmt} is not supported.",
                f"Valid surface formats are: {list(VALID_SURFACE_FORMATS.keys())}",
            )

        ext = VALID_SURFACE_FORMATS.get(fmt, ".irap_binary")
        outfile, metafile, relpath, abspath = _utils.verify_path(
            dataio, fpath, fname, ext
        )

        logger.info("Exported file is %s", outfile)
        if "irap" in fmt:
            obj.to_file(outfile, fformat="irap_binary")
            self.dataio._meta_data["format"] = "irap_binary"
            self._item_to_file_create_file_block(outfile, relpath, abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )

        else:
            raise TypeError("Format ... is not implemened")

        return str(outfile)

    def _item_to_file_cube(self):
        """Write Cube to file"""
        logger.info("Export %s to file...", self.subtype)
        dataio = self.dataio  # shorter
        obj = self.obj

        if isinstance(dataio._tagname, str):
            attr = dataio._tagname.lower().replace(" ", "_")
        else:
            attr = None

        fname, fpath = _utils.construct_filename(
            self.name,
            pretagname=None,
            tagname=attr,
            subfolder=self.subfolder,
            loc="cube",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        fmt = dataio.cube_fformat

        if fmt not in VALID_CUBE_FORMATS.keys():
            raise ValueError(
                f"The file format {fmt} is not supported.",
                f"Valid cube formats are: {list(VALID_CUBE_FORMATS.keys())}",
            )

        ext = VALID_CUBE_FORMATS.get(fmt, ".irap_binary")
        outfile, metafile, relpath, abspath = _utils.verify_path(
            dataio, fpath, fname, ext
        )

        logger.info("Exported file is %s", outfile)
        if "segy" in fmt:
            obj.to_file(outfile, fformat="segy")
            self.dataio._meta_data["format"] = "segy"
            self._item_to_file_create_file_block(outfile, relpath, abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )

        else:
            raise TypeError(f"Format <{fmt}> is not implemened")

        return str(outfile)

    def _item_to_file_gridlike(self):
        """Write Grid (geometry) or GridProperty to file"""
        logger.info("Export %s to file...", self.subtype)
        dataio = self.dataio  # shorter
        obj = self.obj

        if isinstance(dataio._tagname, str):
            attr = dataio._tagname.lower().replace(" ", "_")
        else:
            attr = None

        fname, fpath = _utils.construct_filename(
            self.name,
            pretagname=self.parent_name,
            tagname=attr,
            subfolder=self.subfolder,
            loc="grid",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        fmt = dataio.grid_fformat

        if fmt not in VALID_GRID_FORMATS.keys():
            raise ValueError(
                f"The file format {fmt} is not supported.",
                f"Valid grid(-prop) formats are: {list(VALID_GRID_FORMATS.keys())}",
            )

        ext = VALID_GRID_FORMATS.get(fmt, ".hdf")
        outfile, metafile, relpath, abspath = _utils.verify_path(
            dataio, fpath, fname, ext
        )

        logger.info("Exported file is %s", outfile)
        if "roff" in fmt:
            obj.to_file(outfile, fformat="roff")
            self.dataio._meta_data["format"] = "roff"
            self._item_to_file_create_file_block(outfile, relpath, abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )
        else:
            raise TypeError("Format ... is not implemened")

        return str(outfile)

    def _item_to_file_polygons(self):
        """Write Polygons to file."""
        logger.info("Export %s to file...", self.subtype)
        dataio = self.dataio  # shorter
        obj = self.obj

        if isinstance(dataio._tagname, str):
            attr = dataio._tagname.lower().replace(" ", "_")
        else:
            attr = None

        fname, fpath = _utils.construct_filename(
            self.name,
            pretagname=None,
            tagname=attr,
            subfolder=self.subfolder,
            loc="polygons",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        fmt = dataio.polygons_fformat

        if fmt not in VALID_POLYGONS_FORMATS.keys():
            raise ValueError(
                f"The file format {fmt} is not supported.",
                f"Valid polygons formats are: {list(VALID_POLYGONS_FORMATS.keys())}",
            )

        ext = VALID_POLYGONS_FORMATS.get(fmt, ".hdf")

        outfile, metafile, relpath, abspath = _utils.verify_path(
            dataio, fpath, fname, ext
        )

        logger.info("Exported file is %s", outfile)
        if "csv" in fmt:
            renamings = {"X_UTME": "X", "Y_UTMN": "Y", "Z_TVDSS": "Z", "POLY_ID": "ID"}
            worker = obj.dataframe.copy()
            worker.rename(columns=renamings, inplace=True)
            worker.to_csv(outfile, index=False)
            self.dataio._meta_data["format"] = "csv"
            self._item_to_file_create_file_block(outfile, relpath, abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )
        elif "irap_ascii" in fmt:
            obj.to_file(outfile)
            self.dataio._meta_data["format"] = "irap_ascii"
            self._item_to_file_create_file_block(outfile, relpath, abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )
        else:
            raise TypeError("Format is not supported")

        return str(outfile)

    def _item_to_file_table(self):
        """Write table to file."""
        dataio = self.dataio  # shorter
        obj = self.obj

        if isinstance(dataio._tagname, str):
            attr = dataio._tagname.lower().replace(" ", "_")
        else:
            attr = None

        fname, fpath = _utils.construct_filename(
            self.name,
            pretagname=None,
            tagname=attr,
            subfolder=self.subfolder,
            loc="table",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        # Temporary (?) override so that pa.Table in can only become .arrow out for now
        # Perhaps better to make the fmt an input argument rather than a class constant

        if isinstance(obj, pa.Table):
            logger.info(
                "Incoming object is pa.Table, so setting outgoing table "
                "format to 'arrow'"
            )
            fmt = "arrow"
        else:
            fmt = dataio.table_fformat

        if fmt not in VALID_TABLE_FORMATS.keys():
            raise ValueError(
                f"The file format {fmt} is not supported.",
                f"Valid table formats are: {list(VALID_TABLE_FORMATS.keys())}",
            )

        ext = VALID_TABLE_FORMATS.get(fmt, ".hdf")
        outfile, metafile, relpath, abspath = _utils.verify_path(
            dataio, fpath, fname, ext
        )

        logger.info("Exported file is %s", outfile)

        if fmt == "csv":
            logger.info("Exporting table as csv")
            obj.to_csv(outfile, index=self.index_df)
            self.dataio._meta_data["format"] = "csv"
            self._item_to_file_create_file_block(outfile, relpath, abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )
        elif fmt == "arrow":
            logger.info("Exporting table as arrow")
            # comment taken from equinor/webviz_subsurface/smry2arrow.py

            # Writing here is done through the feather import, but could also be
            # done using pa.RecordBatchFileWriter.write_table() with a few
            # pa.ipc.IpcWriteOptions(). It is convenient to use feather since it
            # has ready configured defaults and the actual file format is the same
            # (https://arrow.apache.org/docs/python/feather.html)
            feather.write_feather(obj, dest=outfile)
            self.dataio._meta_data["format"] = "arrow"
            self._item_to_file_create_file_block(outfile, relpath, abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )
        else:
            raise TypeError("Other formats not supported yet for tables!")

        return str(outfile)

    def _item_to_file_collect_all_metadata(self):
        """Process all metadata for actual instance."""
        logger.info("Collect all metadata")

        dataio = self.dataio
        allmeta = OrderedDict()

        for dollar in dataio._meta_dollars.keys():
            allmeta[dollar] = dataio._meta_dollars[dollar]

        allmeta["class"] = self.classname
        allmeta["file"] = dataio._meta_file
        allmeta["access"] = dataio._meta_access
        allmeta["masterdata"] = dataio._meta_masterdata
        allmeta["tracklog"] = dataio._meta_tracklog
        allmeta["fmu"] = dataio._meta_fmu
        allmeta["data"] = dataio._meta_data
        allmeta["display"] = dataio._meta_display
        logger.debug("\n%s", json.dumps(allmeta, indent=2, default=str))

        logger.info("Collect all metadata, done")
        return allmeta

    def _item_to_file_create_file_block(self, outfile, relpath, abspath):
        """Process the file block.

        The file block contains relative and absolute paths, file size
        and md5 checksum. This function receives the paths, calculates
        size and checksum, and populates the file block by inserting
        directly to the premade dataio._meta_file.

        """

        self.dataio._meta_file["relative_path"] = str(relpath)
        self.dataio._meta_file["absolute_path"] = str(abspath)

        md5sum = _utils.md5sum(outfile)
        self.dataio._meta_file["checksum_md5"] = md5sum

        size_bytes = _utils.size(outfile)
        self.dataio._meta_file["size_bytes"] = size_bytes
