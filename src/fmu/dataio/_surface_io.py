"""Private module for Surface IO in DataIO class."""
import logging
from collections import OrderedDict

from . import _utils

VALID_FORMATS = {"hdf": ".hdf", "irap_binary": ".gri"}


logger = logging.getLogger(__name__)


def surface_to_file(self, obj, fformat):
    """Saving a RegularSurface to file with rich metadata for SUMO and similar.

    Args:
        self: DataIO instance.
        obj: XTGeo RegularSurface instance.
        fformat: File format spesifier string.
    """
    attr = obj._roxmeta.folder

    fname, fpath = _utils.construct_filename(
        obj.name, obj.generate_hash(), descr=attr, loc="surface"
    )

    if fformat not in VALID_FORMATS.keys():
        raise ValueError(f"The fformat {fformat} is not supported.")

    ext = VALID_FORMATS.get(fformat, ".hdf")
    outfile = _utils.verify_path(self._createfolder, fpath, fname, ext)

    obj.metadata.freeform = process_surf_data_metadata(self, obj)

    if fformat == "irap_binary":
        logging.info(f"Exported file is {outfile}")
        obj.to_file(outfile, fformat=fformat, metadata=True)
    else:
        obj.to_hdf(outfile)


def process_surf_data_metadata(self, obj):
    """Process data metadata for actual object."""

    self._meta_data = OrderedDict()

    # shortform
    meta = self._meta_data
    meta["class"] = "regularsurface"
    meta["content"] = self._content

    # define spec record
    meta["spec"] = obj.metadata.required
    meta["spec"]["undef"] = 1.0e30  # irap binary undef
    meta["spec"]["xmin"] = float(obj.xmin)
    meta["spec"]["xmax"] = float(obj.xmax)
    meta["spec"]["ymin"] = float(obj.ymin)
    meta["spec"]["ymax"] = float(obj.ymax)

    name = obj.name
    strat = self._config["stratigraphy"]
    if name in strat:
        is_stratigraphic = strat[name].get("stratigrapic", False)
        meta["stratigraphic"] = is_stratigraphic

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
