"""Private module for Grid and GridProperty IO in DataIO class."""
import logging
from collections import OrderedDict

from . import _utils

VALID_FORMATS = {"hdf": ".hdf", "roff": ".roff"}


logger = logging.getLogger(__name__)


def grid_to_file(_dataio_, grd, fformat, prop=False):
    """Saving a Grid to file with rich metadata for SUMO and similar.

    Args:
        _dataio_: DataIO instance.
        grd: xtgeo Grid _or_ GridProperty instance.
        fformat: File format specifier string.
        prop: If True then GridProperty, else Grid
    """

    if not prop:
        fname, fpath = _utils.construct_filename(
            grd._roxmeta.gridname, grd.generate_hash(), loc="grid"
        )
    else:
        fname, fpath = _utils.construct_filename(
            grd._roxmeta.gridname,
            grd.generate_hash(),
            descr=grd._roxmeta.propname,
            loc="grid",
        )

    if fformat not in VALID_FORMATS.keys():
        raise ValueError(f"The fformat {fformat} is not supported.")

    ext = VALID_FORMATS.get(fformat, ".hdf")
    filepath = _utils.verify_path(_dataio_._createfolder, fpath, fname, ext)

    grd.metadata.freeform = _process_grid_data_metadata(_dataio_, grd, prop=prop)

    if fformat == "roff":
        grd.to_file(filepath, fformat="roff", metadata=True)
    else:
        grd.to_hdf(filepath, compression="blosc")


def _process_grid_data_metadata(_dataio_, grd, prop=False):
    """Process data metadata for actual grdect."""

    _dataio_._meta_data = OrderedDict()

    # shortform
    meta = _dataio_._meta_data
    if prop:
        meta["class"] = "cornerpointgridproperty"
    else:
        meta["class"] = "cornerpointgrid"

    meta["content"] = _dataio_._content

    # define spec record
    meta["spec"] = grd.metadata.required

    # get visual settings
    _get_visuals(_dataio_, grd)

    # collect all metadate
    master = OrderedDict()
    master["data"] = _dataio_._meta_data
    master["template"] = _dataio_._meta_master
    master["fmu"] = _dataio_._meta_fmu

    return master


def _get_visuals(_dataio_, grd):
    """Get the visuals from data type combined with visuals config.

    This assumes that "visuals" is a first level entry in the config file.

    Example of visuals::

    visuals:
        Valysar:
            name: Valysar Fm.
            regularsurface:
                isochore:
                    color: red
                    colortable: physics
                    fill: true
                    range: [0, 20]
                gridproperty:
                    porosity:
                        colortable: physics
                        fill: true
                        range: AUTO
                        facies:
                        discrete: true
                        colortable:
                            0: black
                            1: #3ddd
                            4: #8d2222

    If visuals is not found, Undef (null) is applied

    """
    meta = _dataio_._meta_data  # shortform
    vis = None
    if _dataio_._config and "visuals" in _dataio_._config.keys():
        vis = _dataio_._config["visuals"]
    else:
        meta["visuals"] = None
        return

    meta["visuals"] = OrderedDict()
    if grd.name in vis.keys() and meta["class"] in vis[grd.name]:
        attrs = vis[grd.name]["regularsurface"]
        if _dataio_._content in attrs:
            meta["visuals"] = attrs[_dataio_._content]

        meta["visuals"]["name"] = vis[grd.name].get("name", grd.name)

    else:
        meta["visuals"] = None
