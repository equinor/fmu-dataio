"""Private module for Surface IO in DataIO class."""
import logging
import json

from collections import OrderedDict

from . import _utils

VALID_FORMATS = {"hdf": ".hdf", "irap_binary": ".gri"}


logger = logging.getLogger(__name__)


def surface_to_file(dataio, regsurf, fformat):
    """Saving a RegularSurface to file with rich metadata for SUMO and similar.

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
    )

    if fformat not in VALID_FORMATS.keys():
        raise ValueError(f"The fformat {fformat} is not supported.")

    ext = VALID_FORMATS.get(fformat, ".hdf")
    outfile, metafile = _utils.verify_path(dataio._createfolder, fpath, fname, ext)

    regsurf.metadata.freeform = process_metadata(dataio, regsurf)

    logger.info("Exported file is %s", outfile)
    if "irap" in dataio.surface_fformat:
        regsurf.to_file(outfile, fformat="irap_binary")
        _utils.export_metadata_file(metafile, regsurf.metadata.freeform)
    else:
        regsurf.to_hdf(outfile)


def process_metadata(dataio, regsurf):
    """Process metadata for actual regularsurface instance."""

    dataio._meta_data = OrderedDict()

    # shortform
    meta = dataio._meta_data

    for dollar in dataio._meta_dollars.keys():
        meta[dollar] = dataio._meta_dollars[dollar]

    meta["class"] = "surface"

    meta["access"] = dataio._meta_access
    meta["masterdata"] = dataio._meta_masterdata

    logger.debug("Metadata so far:\n%s", json.dumps(meta, indent=2))

    process_data_metadata(dataio, regsurf, meta)

    logger.debug("Metadata after data:\n%s", json.dumps(meta, indent=2))
    return meta


def process_data_metadata(dataio, regsurf, meta):
    """Process the actual 'data' block in metadata.

    This part has some complex elements...
    """
    meta["data"] = OrderedDict()

    # true name (will backup to model name if not present)
    meta["data"]["name"] = dataio._meta_aux[regsurf.name].get("name", regsurf.name)

    # check stratigraphic bool
    meta["data"]["stratigraphic"] = dataio._meta_aux[regsurf.name].get(
        "stratigraphic", False
    )

    meta["data"]["layout"] = "regular"

    # define spec record
    meta["data"]["spec"] = regsurf.metadata.required
    meta["data"]["spec"]["undef"] = 1.0e30  # irap binary undef

    meta["data"]["bbox"] = OrderedDict()
    meta["data"]["bbox"]["xmin"] = float(regsurf.xmin)
    meta["data"]["bbox"]["xmax"] = float(regsurf.xmax)
    meta["data"]["bbox"]["ymin"] = float(regsurf.ymin)
    meta["data"]["bbox"]["ymax"] = float(regsurf.ymax)
    meta["data"]["bbox"]["zmin"] = float(regsurf.values.min())
    meta["data"]["bbox"]["zmax"] = float(regsurf.values.max())

    # name = regsurf.name
    # strat = dataio._config["stratigraphy"]
    # if name in strat:
    #     is_stratigraphic = strat[name].get("stratigrapic", False)
    #     meta["stratigraphic"] = is_stratigraphic

    # # get visual settings
    # _get_visuals(dataio, regsurf)

    # # collect all metadate
    # master = OrderedDict()
    # master["data"] = dataio._meta_data
    # master["template"] = dataio._meta_master
    # master["fmu"] = dataio._meta_fmu

    # return master


def _get_visuals(dataio, regsurf):
    """Get the visuals from data type combined with visuals config.

    This assumes that "visuals" is a first level entry in the config file.

    Example of visuals::

    visuals:

        TopVolantis:
            name: Top Volantis # display name
            regularsurface:
                depth:
                    contours: true
                    colortable: gist_rainbow
                    fill: true
                    range: [1627, 1958]
                    color: black
                time:
                    contours: true
                    color: #332ed4
                    colortable: gist_rainbow
                    fill: true
                    range: [1600, 1900]

            polygons:
                color: black
                fill: true

    If visuals is not found, Undef (null) is applied

    """
    meta = dataio._meta_data  # shortform
    vis = None
    if dataio._config and "visuals" in dataio._config.keys():
        vis = dataio._config["visuals"]
    else:
        meta["visuals"] = None
        return

    meta["visuals"] = OrderedDict()
    if regsurf.name in vis.keys() and meta["class"] in vis[regsurf.name]:
        attrs = vis[regsurf.name]["regularsurface"]
        if dataio._content in attrs:
            meta["visuals"] = attrs[dataio._content]

        meta["visuals"]["name"] = vis[regsurf.name].get("name", regsurf.name)

    else:
        meta["visuals"] = None
