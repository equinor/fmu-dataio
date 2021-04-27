"""Private module for Surface IO in DataIO class."""
import logging
import json
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
            self._surface_to_file()

    def _surface_to_file(self):
        """Save a RegularSurface instance."""
        dataio = self.dataio  # shorter
        obj = self.obj

        if isinstance(dataio._description, str):
            attr = dataio._description.lower().replace(" ", "_")
        else:
            attr = None

        fname, fpath = _utils.construct_filename(
            obj.name,
            descr=attr,
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

            # populate the file block which needs to done here
            dataio._meta_file["md5sum"] = md5sum
            dataio._meta_file["relative_path"] = str(relpath)
            dataio._meta_file["absolute_path"] = str(abspath)
            allmeta = self._process_all_metadata("RegularSurface")
            _utils.export_metadata_file(metafile, allmeta, verbosity=self.verbosity)
        else:
            obj.to_hdf(outfile)

    def _process_all_metadata(self, subtype):
        """Process all metadata for actual instance."""
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

        data_meta = None
        if subtype == "RegularSurface":
            data_meta = self._process_data_regularsurface_metadata()
        allmeta["data"] = data_meta

        # process_display_metadata(dataio, regsurf)
        # allmeta["display"] = dataio._meta_display

        logger.debug(
            "Metadata after data:\n%s", json.dumps(allmeta, indent=2, default=str)
        )
        return allmeta

    def _process_data_regularsurface_metadata(self):
        """Process the actual 'data' block in metadata for RegularSurface."""
        logger.info("Process data metadata for RegularSurface")

        dataio = self.dataio
        regsurf = self.obj

        meta = dataio._meta_data  # shortform
        strat = dataio._meta_strat  # shortform

        meta["layout"] = "regular"

        # true name (will backup to model name if not present)
        if strat is None:
            meta["name"] = regsurf.name
        elif strat is not None and regsurf.name not in strat:
            meta["name"] = regsurf.name
        else:
            meta["name"] = strat[regsurf.name].get("name", regsurf.name)
            meta["stratigraphic"] = strat[regsurf.name].get("stratigraphic", False)
            meta["alias"] = strat[regsurf.name].get("alias", None)
            meta["stratigraphic_alias"] = strat[regsurf.name].get(
                "stratigraphic_alias", None
            )

        content, extra = self.process_data_content()
        meta["content"] = content
        if extra is not None:
            meta[content] = extra

        # meta["properties"] = dataio._details.get("properties", None)
        meta["unit"] = dataio._unit
        meta["vertical_domain"] = dataio._vertical_domain
        meta["is_prediction"] = dataio._is_prediction
        meta["is_observation"] = dataio._is_observation
        if dataio._timedata is not None:
            meta["time1"] = dataio._timedata.get("time1", None)
            meta["time2"] = dataio._timedata.get("time2", None)

        # define spec record
        specs = regsurf.metadata.required
        newspecs = OrderedDict()
        for spec, val in specs.items():
            if isinstance(val, np.float):
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
        return meta

    def process_data_content(self):
        """Process the content block (within data block) which can complex."""
        content = self.dataio._content

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

        return usecontent, useextra
