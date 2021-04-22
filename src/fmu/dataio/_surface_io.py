"""Private module for Surface IO in DataIO class."""
import logging
import json

from collections import OrderedDict

from . import _utils

VALID_FORMATS = {"hdf": ".hdf", "irap_binary": ".gri"}


logger = logging.getLogger(__name__)


def surface_to_file(dataio, regsurf):
    """Saving a RegularSurface to file with rich metadata for SUMO and similar.

    Many metadata items are object independent an are treated directly in the
    dataio module. Here additional metadata (dependent on this datatype) are
    collected/processed and subsequently both 'independent' and object dependent
    a final metadata file (or part of file if HDF) are collected and
    written to disk here.

    Args:
        dataio: DataIO instance.
        regsurf: XTGeo RegularSurface instance.
        fformat: File format spesifier string.
    """
    logger.setLevel(level=dataio._verbosity)

    attr = dataio._description

    fname, fpath = _utils.construct_filename(
        regsurf.name,
        descr=attr,
        loc="surface",
        outroot=dataio.export_root,
        verbosity=dataio._verbosity,
    )

    fmt = dataio.surface_fformat

    if fmt not in VALID_FORMATS.keys():
        raise ValueError(f"The file format {fmt} is not supported.")

    ext = VALID_FORMATS.get(fmt, ".hdf")
    outfile, metafile, relpath, abspath = _utils.verify_path(
        dataio._createfolder, fpath, fname, ext, verbosity=dataio._verbosity
    )

    logger.info("Exported file is %s", outfile)
    if "irap" in dataio.surface_fformat:
        regsurf.to_file(outfile, fformat="irap_binary")
        md5sum = _utils.md5sum(outfile)

        # populate the file block which needs to done here
        dataio._meta_file["md5sum"] = md5sum
        dataio._meta_file["relative_path"] = relpath
        dataio._meta_file["absolute_path"] = abspath
        allmeta = process_all_metadata(dataio, regsurf)
        _utils.export_metadata_file(metafile, allmeta)
    else:
        regsurf.to_hdf(outfile)


def process_all_metadata(dataio, regsurf):
    """Process all metadata for actual regularsurface instance."""

    allmeta = OrderedDict()

    for dollar in dataio._meta_dollars.keys():
        allmeta[dollar] = dataio._meta_dollars[dollar]

    allmeta["class"] = "surface"
    allmeta["file"] = dataio._meta_file
    allmeta["access"] = dataio._meta_access
    allmeta["masterdata"] = dataio._meta_masterdata
    allmeta["tracklog"] = dataio._meta_tracklog
    allmeta["fmu"] = dataio._meta_fmu

    process_data_metadata(dataio, regsurf)
    allmeta["data"] = dataio._meta_data

    process_display_metadata(dataio, regsurf)
    allmeta["display"] = dataio._meta_display

    logger.debug("Metadata after data:\n%s", json.dumps(allmeta, indent=2, default=str))
    return allmeta


def process_data_metadata(dataio, regsurf):
    """Process the actual 'data' block in metadata.

    This part has some complex elements...
    """
    logger.info("Process data metadata for instance...")

    meta = dataio._meta_data  # shortform
    strat = dataio._meta_strat  # shortform

    # true name (will backup to model name if not present)
    meta["name"] = strat[regsurf.name].get("name", regsurf.name)
    meta["layout"] = "regular"

    # check stratigraphic bool
    meta["stratigraphic"] = strat[regsurf.name].get("stratigraphic", False)
    meta["alias"] = strat[regsurf.name].get("alias", None)
    meta["stratigraphic_alias"] = strat[regsurf.name].get("stratigraphic_alias", None)

    meta["content"] = dataio._content  # depth, time, fluid_contacts, ...

    # some content have additional fields, e.g. fluid_contact
    if meta["content"] == "fluid_contact" and "fluid_contact" in strat[regsurf.name]:
        meta["fluidcontact"] = {
            "contact": strat["regsurf.name"].get("fluid_contact", None)
        }

    # properties, unit, domain, ...
    meta["properties"] = dataio._details.get("properties", None)
    meta["unit"] = dataio._details.get("unit", None)
    meta["vertical_domain"] = dataio._details.get("vertical_domain", None)
    meta["depth_reference"] = dataio._details.get("depth_reference", "msl")
    meta["is_prediction"] = dataio._details.get("is_prediction", True)
    meta["is_observation"] = dataio._details.get("is_observation", False)
    meta["time1"] = dataio._details.get("time1", None)
    meta["time2"] = dataio._details.get("time2", False)

    # define spec record
    meta["spec"] = regsurf.metadata.required
    meta["spec"]["undef"] = 1.0e30  # irap binary undef

    meta["bbox"] = OrderedDict()
    meta["bbox"]["xmin"] = regsurf.xmin
    meta["bbox"]["xmax"] = regsurf.xmax
    meta["bbox"]["ymin"] = regsurf.ymin
    meta["bbox"]["ymax"] = regsurf.ymax
    meta["bbox"]["zmin"] = regsurf.values.min()
    meta["bbox"]["zmax"] = regsurf.values.max()
    logger.info("Process data metadata for instance... done")


def process_display_metadata(dataio, regsurf) -> None:
    """Get metadata from for display (fully optional).

    These metadata are extracted from the config auxiliary section. They
    are derived by key name and possibly using default. e.g.:

    TopVolantis
        display:
            # DEFAULT is fallback content for missing data and shall be complete
            DEFAULT:
                name: Top Valysar
                line: {show: true, color: black}
                points: {show: true, color: red}
                contours: {show: true, color: black}
                fill: {show: true, colors: gist_earth}
            depth:
                points: {show: true, color: blue}
                contours: {show: true, color: black}
                fill: {show: true, colors: gist_earth, range: [1300, 1900]}
            time:
                contours: {show: true, color: magenta}

    TODO:
    Possible extension: overriding settings from the actual function call?
    """
    logger.info("Process display metadata for instance with name %s ...", regsurf.name)
    merged = None
    if regsurf._name in dataio._meta_strat.keys():

        display = dataio._meta_strat[regsurf.name].get("display", None)

        if not display:
            return None

        default = display.get("DEFAULT", None)
        # next try the content
        content = display.get(dataio._content, None)

        if default is None and content is None:
            return None

        # merge the keys
        merged = OrderedDict()

        if default:
            for key, values in default.items():
                if content and key in content.keys():
                    merged[key] = content[key]
                else:
                    merged[key] = values
        elif not default and content:
            merged = content

    dataio._meta_display = merged
    logger.info("Process display metadata for instance with name %s done", regsurf.name)
