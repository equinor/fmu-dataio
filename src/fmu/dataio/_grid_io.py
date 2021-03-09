"""Private module for Grid and GridProperty IO in DataIO class."""
import logging
from collections import OrderedDict

from . import _utils

VALID_FORMATS = {"hdf": ".hdf", "roff": ".roff"}


logger = logging.getLogger(__name__)


def grid_to_file(self, obj, fformat, prop=False):
    """Saving a Grid to file with rich metadata for SUMO and similar.

    Args:
        self: DataIO instance.
        obj: XTGeo instance.
        fformat: File format spesifier string.
        prop: If True then GridProperty, else Grid
    """

    if not prop:
        fname, fpath = _utils.construct_filename(
            obj._roxmeta.gridname, obj.generate_hash(), loc="grid"
        )
    else:
        fname, fpath = _utils.construct_filename(
            obj._roxmeta.gridname,
            obj.generate_hash(),
            descr=obj._roxmeta.propname,
            loc="grid",
        )

    if fformat not in VALID_FORMATS.keys():
        raise ValueError(f"The fformat {fformat} is not supported.")

    ext = VALID_FORMATS.get(fformat, ".hdf")
    filepath = _utils.verify_path(self._createfolder, fpath, fname, ext)

    obj.metadata.freeform = _process_grid_data_metadata(self, obj, prop=prop)

    if fformat == "roff":
        obj.to_file(filepath, fformat="roff", metadata=True)
    else:
        obj.to_hdf(filepath, compression="blosc")


def _process_grid_data_metadata(self, obj, prop=False):
    """Process data metadata for actual object."""

    self._meta_data = OrderedDict()

    # shortform
    meta = self._meta_data
    if prop:
        meta["class"] = "cornerpointgridproperty"
    else:
        meta["class"] = "cornerpointgrid"

    meta["content"] = self._content

    # define spec record
    meta["spec"] = obj.metadata.required

    # get visual settings
    _get_visuals(self, obj)

    # collect all metadate
    master = OrderedDict()
    master["data"] = self._meta_data
    master["template"] = self._meta_master
    master["fmu"] = self._meta_fmu

    return master


def _get_visuals(self, obj):
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
    meta = self._meta_data  # shortform
    vis = None
    if self._config and "visuals" in self._config.keys():
        vis = self._config["visuals"]
    else:
        meta["visuals"] = None
        return

    meta["visuals"] = OrderedDict()
    if obj.name in vis.keys() and meta["class"] in vis[obj.name]:
        attrs = vis[obj.name]["regularsurface"]
        if self._content in attrs:
            meta["visuals"] = attrs[self._content]

        meta["visuals"]["name"] = vis[obj.name].get("name", obj.name)

    else:
        meta["visuals"] = None
