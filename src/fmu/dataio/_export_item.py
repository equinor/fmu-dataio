"""Private module for Surface IO in DataIO class."""
import warnings
import logging
import json
from datetime import datetime
from collections import OrderedDict

import numpy as np
import pandas as pd

import xtgeo

from . import _utils

VALID_SURFACE_FORMATS = {"irap_binary": ".gri"}
VALID_GRID_FORMATS = {"hdf": ".hdf", "roff": ".roff"}
VALID_TABLE_FORMATS = {"hdf": ".hdf", "csv": ".csv"}
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
    "property": {"attribute": str, "is_discrete": bool},
    "seismic": {
        "attribute": str,
        "zrange": float,
        "filter_size": float,
        "scaling_factor": float,
    },
    "fluid_contact": {"contact": str},
    "field_outline": {"contact": str},
    "volumes": None,
    "volumetrics": None,  # or?
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

    def __init__(self, dataio, obj, verbosity="warning"):
        self.dataio = dataio
        self.obj = obj
        self.verbosity = verbosity
        self.subtype = None
        self.classname = "unset"
        self.name = "unknown"

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
            self.classname = "regularsurface"
        elif isinstance(self.obj, xtgeo.Polygons):
            self.subtype = "Polygons"
            self.classname = "polygons"
        elif isinstance(self.obj, xtgeo.Grid):
            self.subtype = "CPGrid"
            self.classname = "cpgrid"
        elif isinstance(self.obj, xtgeo.GridProperty):
            self.subtype = "CPGridProperty"
            self.classname = "cpgrid_property"
        elif isinstance(self.obj, pd.DataFrame):
            self.subtype = "DataFrame"
            self.classname = "table"
        else:
            raise NotImplementedError(
                "This data type is not (yet) supported: ", type(self.obj)
            )
        logger.info("Found %s", self.subtype)

        self._data_process()
        self._data_process_object()
        self._fmu_inject_workflow()  # this will vary if surface, table, grid, ...
        fpath = self._item_to_file()
        return fpath

    def _data_process(self):
        """Process som potentially common subfields in the data block.

        These subfields are:
        - name
        - top/base (from relation)
        - content
        - time
        - properties? Disabled!
        - grid_model
        - is_observation
        - is_prediction
        - description
        """
        self._data_process_name()
        self._data_process_relation()
        self._data_process_content()
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

    def _data_process_relation(self):
        """Process the relation input which gives offset and top/base settings.

        For example::

          relation:
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
        logger.info("Evaluate relation (offset, top, base), if any")
        meta = self.dataio._meta_data
        if self.dataio._relation is None:
            logger.info("No relation found, which may be ok")
            return  # relation data are missing

        rel = self.dataio._relation  # shall be a dictionary

        offset = rel.get("offset", None)
        if offset is not None:
            logger.info("Offset is found")
            meta["offset"] = offset

        # top process top and base (both must be present in case)
        top = rel.get("top", None)
        base = rel.get("base", None)
        if top is None or base is None:
            logger.info("Relation top and/base is missing, skip further")
            return

        topname = rel["top"].get("ref", None)
        basename = rel["base"].get("ref", None)

        if topname is None or basename is None:
            warnings.warn(
                "Relation top and/base is present but <ref> is missing, skip further",
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
            usecontent = content

        else:
            usecontent = (list(content.keys()))[0]
            useextra = content[usecontent]

        if usecontent not in ALLOWED_CONTENTS.keys():
            raise ValidationError(f"Invalid content: <{usecontent}> is not in list!")

        meta["content"] = usecontent
        if useextra:
            self._data_process_content_validate(usecontent, useextra)
            meta[usecontent] = useextra

    @staticmethod
    def _data_process_content_validate(name, fields):
        valid = ALLOWED_CONTENTS.get(name, None)
        if valid is None:
            raise ValidationError(f"Cannot validate content for <{name}>")

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
            rkey, status = rlist.pop()
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
        elif self.subtype == "CPGrid":
            self._data_process_cpgrid()
        elif self.subtype == "CPGridProperty":
            self._data_process_cpgridproperty()
        elif self.subtype == "Polygons":
            self._data_process_object_polygons()
        elif self.subtype == "DataFrame":
            self._data_process_object_dataframe()

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

    def _fmu_inject_workflow(self):
        """Inject workflow into fmu metadata block."""
        self.dataio._meta_fmu["workflow"] = self.dataio._workflow

    def _item_to_file(self):
        logger.info("Export item to file...")
        if self.subtype == "RegularSurface":
            fpath = self._item_to_file_regularsurface()
        elif self.subtype == "Polygons":
            fpath = self._item_to_file_polygons()
        elif self.subtype in ("CPGrid", "CPGridProperty"):
            fpath = self._item_to_file_gridlike()
        elif self.subtype == "DataFrame":
            fpath = self._item_to_file_dataframe()
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
            tagname=attr,
            loc="surface",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        fmt = dataio.surface_fformat

        if fmt not in VALID_SURFACE_FORMATS.keys():
            raise ValueError(f"The file format {fmt} is not supported.")

        ext = VALID_SURFACE_FORMATS.get(fmt, ".irap_binary")
        outfile, metafile, relpath, abspath = _utils.verify_path(
            dataio, fpath, fname, ext
        )

        logger.info("Exported file is %s", outfile)
        if "irap" in fmt:
            obj.to_file(outfile, fformat="irap_binary")
            md5sum = _utils.md5sum(outfile)
            self.dataio._meta_data["format"] = "irap_binary"

            # populate the file block which needs to done here
            dataio._meta_file["checksum_md5"] = md5sum
            dataio._meta_file["relative_path"] = str(relpath)
            dataio._meta_file["absolute_path"] = str(abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )

        else:
            raise TypeError("Format ... is not implemened")

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
            tagname=attr,
            loc="grid",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        fmt = dataio.grid_fformat

        if fmt not in VALID_GRID_FORMATS.keys():
            raise ValueError(f"The file format {fmt} is not supported.")

        ext = VALID_GRID_FORMATS.get(fmt, ".hdf")
        outfile, metafile, relpath, abspath = _utils.verify_path(
            dataio, fpath, fname, ext
        )

        logger.info("Exported file is %s", outfile)
        if "roff" in fmt:
            obj.to_file(outfile, fformat="roff")
            md5sum = _utils.md5sum(outfile)
            self.dataio._meta_data["format"] = "roff"

            # populate the file block which needs to done here
            dataio._meta_file["checksum_md5"] = md5sum
            dataio._meta_file["relative_path"] = str(relpath)
            dataio._meta_file["absolute_path"] = str(abspath)
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
            tagname=attr,
            loc="polygons",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        fmt = dataio.polygons_fformat

        if fmt not in VALID_POLYGONS_FORMATS.keys():
            raise ValueError(f"The file format {fmt} is not supported.")

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
            md5sum = _utils.md5sum(outfile)
            self.dataio._meta_data["format"] = "csv"

            # populate the file block which needs to done here
            dataio._meta_file["checksum_md5"] = md5sum
            dataio._meta_file["relative_path"] = str(relpath)
            dataio._meta_file["absolute_path"] = str(abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )
        elif "irap_ascii" in fmt:
            obj.to_file(outfile)
            md5sum = _utils.md5sum(outfile)
            self.dataio._meta_data["format"] = "irap_ascii"

            # populate the file block which needs to done here
            dataio._meta_file["checksum_md5"] = md5sum
            dataio._meta_file["relative_path"] = str(relpath)
            dataio._meta_file["absolute_path"] = str(abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )
        else:
            raise TypeError("Format is not supported")

        return str(outfile)

    def _item_to_file_dataframe(self):
        """Write DataFrame to file."""
        dataio = self.dataio  # shorter
        obj = self.obj

        if isinstance(dataio._tagname, str):
            attr = dataio._tagname.lower().replace(" ", "_")
        else:
            attr = None

        fname, fpath = _utils.construct_filename(
            self.name,
            tagname=attr,
            loc="table",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        fmt = dataio.table_fformat

        if fmt not in VALID_TABLE_FORMATS.keys():
            raise ValueError(f"The file format {fmt} is not supported.")

        ext = VALID_TABLE_FORMATS.get(fmt, ".hdf")
        outfile, metafile, relpath, abspath = _utils.verify_path(
            dataio, fpath, fname, ext
        )

        logger.info("Exported file is %s", outfile)
        if "csv" in dataio.table_fformat:
            obj.to_csv(outfile)
            md5sum = _utils.md5sum(outfile)
            self.dataio._meta_data["format"] = "csv"

            # populate the file block which needs to done here
            dataio._meta_file["checksum_md5"] = md5sum
            dataio._meta_file["relative_path"] = str(relpath)
            dataio._meta_file["absolute_path"] = str(abspath)
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
        logger.debug("\n%s", json.dumps(allmeta, indent=2, default=str))

        logger.info("Collect all metadata, done")
        return allmeta
