"""Private module for Surface IO in DataIO class."""
import logging
from collections import OrderedDict

from . import _utils

VALID_FORMATS = {"hdf": ".hdf", "irap_binary": ".gri"}


logger = logging.getLogger(__name__)


def surface_to_file(dataio, regsurf, fformat, fileroot="."):
    """Saving a RegularSurface to file with rich metadata for SUMO and similar.

    Args:
        dataio: DataIO instance.
        regsurf: XTGeo RegularSurface instance.
        fformat: File format spesifier string.
    """
    attr = regsurf._roxmeta.folder

    fname, fpath = _utils.construct_filename(
        regsurf.name,
        regsurf.generate_hash(),
        descr=attr,
        loc="surface",
        filedest=fileroot,
    )

    if fformat not in VALID_FORMATS.keys():
        raise ValueError(f"The fformat {fformat} is not supported.")

    ext = VALID_FORMATS.get(fformat, ".hdf")
    outfile = _utils.verify_path(dataio._createfolder, fpath, fname, ext)

    regsurf.metadata.freeform = process_surf_data_metadata(dataio, regsurf)

    logging.info("Exported file is %s", outfile)
    if "irap" in dataio.surface_fformat:
        regsurf.to_file(outfile, fformat="irap_binary", metadata=True)
    else:
        regsurf.to_hdf(outfile)


def process_surf_data_metadata(dataio, regsurf):
    """Process data metadata for actual regsurfect."""

    dataio._meta_data = OrderedDict()

    # shortform
    meta = dataio._meta_data
    meta["class"] = "regularsurface"
    meta["content"] = dataio._content

    # define spec record
    meta["spec"] = regsurf.metadata.required
    meta["spec"]["undef"] = 1.0e30  # irap binary undef
    meta["spec"]["xmin"] = float(regsurf.xmin)
    meta["spec"]["xmax"] = float(regsurf.xmax)
    meta["spec"]["ymin"] = float(regsurf.ymin)
    meta["spec"]["ymax"] = float(regsurf.ymax)

    name = regsurf.name
    strat = dataio._config["stratigraphy"]
    if name in strat:
        is_stratigraphic = strat[name].get("stratigrapic", False)
        meta["stratigraphic"] = is_stratigraphic

    # get visual settings
    _get_visuals(dataio, regsurf)

    # collect all metadate
    master = OrderedDict()
    master["data"] = dataio._meta_data
    master["template"] = dataio._meta_master
    master["fmu"] = dataio._meta_fmu

    return master


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
