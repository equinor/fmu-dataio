"""Private module for Surface IO in DataIO class."""
import warnings
import logging
import json
from datetime import datetime
import numpy as np

from collections import OrderedDict
import xtgeo

from . import _utils

VALID_SURFACE_FORMATS = {"hdf": ".hdf", "irap_binary": ".gri"}
ALLOWED_CONTENTS = ["depth", "time", "seismic", "fluid_contact", "undefined"]

logger = logging.getLogger(__name__)


class _ExportItem:
    """Export of the actual data item with metadata."""

    def __init__(self, dataio, obj, verbosity="warning"):
        self.dataio = dataio
        self.obj = obj
        self.verbosity = verbosity
        self.subtype = None
        if self.verbosity is None:
            self.verbosity = self.dataio._verbosity

        logger.setLevel(level=self.verbosity)

    def save_to_file(self):
        """Saving an instance to file with rich metadata for SUMO.

        Many metadata items are object independent and are treated directly in the
        dataio module. Here additional metadata (dependent on this datatype) are
        collected/processed and subsequently both 'independent' and object dependent
        a final metadata file (or part of file if HDF) are collected and
        written to disk here.
        """
        if isinstance(self.obj, xtgeo.RegularSurface):
            self.subtype = "RegularSurface"

        self._data_process()
        self._data_process_object()
        self._fmu_inject_workflow()  # this will vary if surface, table, grid, ...
        self._item_to_file()

    def _data_process(self):
        """Process som potentially common subfields in the data block.

        These subfields are:
        - name
        - top/base (from relation)
        - content
        - time
        - properties
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

        if strat is None:
            meta["name"] = usename
        elif strat is not None and usename not in strat:
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
            usecontent = "undefined"

        elif isinstance(content, str):
            usecontent = content

        else:
            usecontent = (list(content.keys()))[0]
            useextra = content[usecontent]

        if usecontent not in ALLOWED_CONTENTS:
            raise ValueError(f"Sorry, content <{usecontent}> is not in list!")

        meta["content"] = usecontent
        if useextra:
            meta[usecontent] = useextra

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
        print("XXXX", self.dataio._vertical_domain)
        meta["unit"] = self.dataio._unit
        (meta["vertical_domain"], meta["depth_reference"],) = list(
            self.dataio._vertical_domain.items()
        )[0]
        meta["is_prediction"] = self.dataio._is_prediction
        meta["is_observation"] = self.dataio._is_observation

        # tmp solution for properties
        meta["properties"] = list()
        props = OrderedDict()
        props["name"] = "SomeName"
        props["attribute"] = "SomeAttribute"
        props["is_discrete"] = False
        props["calculation"] = None
        meta["properties"].append(props)

        # tmp:
        meta["grid_model"] = OrderedDict()
        meta["grid_model"]["name"] = "SomeGrid"

        # tmp:
        meta["description"] = list()
        meta["description"].append("This is description line 1")
        meta["description"].append("This is description line 2")

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

    def _fmu_inject_workflow(self):
        """Inject workflow into fmu metadata block."""
        self.dataio._meta_fmu["workflow"] = self.dataio._workflow

    def _item_to_file(self):
        logger.info("Export item to file...")
        if self.subtype == "RegularSurface":
            self._item_to_file_regularsurface()

    def _item_to_file_regularsurface(self):
        """Write RegularSurface to file"""
        logger.info(f"Export {self.subtype} to file...")
        dataio = self.dataio  # shorter
        obj = self.obj

        if isinstance(dataio._tagname, str):
            attr = dataio._tagname.lower().replace(" ", "_")
        else:
            attr = None

        fname, fpath = _utils.construct_filename(
            obj.name,
            tagname=attr,
            loc="surface",
            outroot=dataio.export_root,
            verbosity=dataio._verbosity,
        )

        fmt = dataio.surface_fformat

        if fmt not in VALID_SURFACE_FORMATS.keys():
            raise ValueError(f"The file format {fmt} is not supported.")

        ext = VALID_SURFACE_FORMATS.get(fmt, ".hdf")
        outfile, metafile, relpath, abspath = _utils.verify_path(
            dataio.createfolder, fpath, fname, ext, verbosity=dataio._verbosity
        )

        logger.info("Exported file is %s", outfile)
        if "irap" in dataio.surface_fformat:
            obj.to_file(outfile, fformat="irap_binary")
            md5sum = _utils.md5sum(outfile)
            self.dataio._meta_data["format"] = "irap_binary"

            # populate the file block which needs to done here
            dataio._meta_file["md5sum"] = md5sum
            dataio._meta_file["relative_path"] = str(relpath)
            dataio._meta_file["absolute_path"] = str(abspath)
            allmeta = self._item_to_file_collect_all_metadata()
            _utils.export_metadata_file(
                metafile, allmeta, verbosity=self.verbosity, savefmt=dataio.meta_format
            )
        else:
            self.dataio._meta_data["format"] = "hdf"
            obj.to_hdf(outfile)

    def _item_to_file_collect_all_metadata(self):
        """Process all metadata for actual instance."""
        logger.info("Collect all metadata")

        dataio = self.dataio
        allmeta = OrderedDict()

        for dollar in dataio._meta_dollars.keys():
            allmeta[dollar] = dataio._meta_dollars[dollar]

        allmeta["class"] = "surface"
        allmeta["file"] = dataio._meta_file
        allmeta["access"] = dataio._meta_access
        allmeta["masterdata"] = dataio._meta_masterdata
        allmeta["tracklog"] = dataio._meta_tracklog
        allmeta["fmu"] = dataio._meta_fmu
        allmeta["data"] = dataio._meta_data
        print("YYY+n", json.dumps(allmeta, indent=2, default=str))

        return allmeta
