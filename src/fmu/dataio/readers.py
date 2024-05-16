"""Module for reading data not supported by other tools"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import yaml

from . import _design_kw, types
from ._logging import null_logger
from ._utils import check_if_number

logger: Final = null_logger(__name__)


def read_metadata_from_file(filename: str | Path) -> dict:
    """Read the metadata as a dictionary given a filename.

    If the filename is e.g. /some/path/mymap.gri, the assosiated metafile
    will be /some/path/.mymap.gri.yml (or json?)

    Args:
        filename: The full path filename to the data-object.

    Returns:
        A dictionary with metadata read from the assiated metadata file.
    """
    fname = Path(filename)
    if fname.stem.startswith("."):
        raise OSError(f"The input is a hidden file, cannot continue: {fname.stem}")

    metafile = str(fname.parent) + "/." + fname.stem + fname.suffix + ".yml"
    metafilepath = Path(metafile)
    if not metafilepath.exists():
        raise OSError(f"Cannot find requested metafile: {metafile}")
    with open(metafilepath) as stream:
        return yaml.safe_load(stream)


def read_parameters_txt(pfile: Path | str) -> types.Parameters:
    """Read the parameters.txt file and convert to a dict.
    The parameters.txt file has this structure::
      SENSNAME rms_seed
      SENSCASE p10_p90
      RMS_SEED 1000
      KVKH_CHANNEL 0.6
      KVKH_CREVASSE 0.3
      GLOBVAR:VOLON_FLOODPLAIN_VOLFRAC 0.256355
      GLOBVAR:VOLON_PERMH_CHANNEL 1100
      GLOBVAR:VOLON_PORO_CHANNEL 0.2
      LOG10_GLOBVAR:FAULT_SEAL_SCALING 0.685516
      LOG10_MULTREGT:MULT_THERYS_VOLON -3.21365
      LOG10_MULTREGT:MULT_VALYSAR_THERYS -3.2582
    ...but may also appear on a justified format, with leading
    whitespace and tab-justified columns, legacy from earlier
    versions but kept alive by some users::
                            SENSNAME     rms_seed
                            SENSCASE     p10_p90
                            RMS_SEED     1000
                        KVKH_CHANNEL     0.6
          GLOBVAR:VOLON_PERMH_CHANNEL    1100
      LOG10_GLOBVAR:FAULT_SEAL_SCALING   0.685516
      LOG10_MULTREGT:MULT_THERYS_VOLON   -3.21365
    This should be parsed as::
        {
        "SENSNAME": "rms_seed"
        "SENSCASE": "p10_p90"
        "RMS_SEED": 1000
        "KVKH_CHANNEL": 0.6
        "KVKH_CREVASSE": 0.3
        "GLOBVAR": {"VOLON_FLOODPLAIN_VOLFRAC": 0.256355, ...etc}
        }
    """

    logger.debug("Reading parameters.txt from %s", pfile)

    parameterlines = Path(pfile).read_text().splitlines()

    dict_str_to_str = _design_kw.extract_key_value(parameterlines)
    return {key: check_if_number(value) for key, value in dict_str_to_str.items()}


def read_faultroom_file(filename: str | Path) -> FaultRoomSurface:
    """Faultroom surface data are (geo)JSON file or dicts; needs separate handling.

    Faultroom data are quite propriatary data and is not supported by e.g. xtgeo
    currently. Hence it is read locally. As input, both a dict and a file with
    extension .json og .geojson can be applied
    """
    filename = Path(filename)
    if "json" in filename.suffix.lower():
        # try read the (geo)json file
        with open(filename, encoding="utf-8") as stream:
            dict_obj = json.load(stream)

        if (
            "metadata" in dict_obj
            and "source" in dict_obj["metadata"]
            and "FaultRoom" in dict_obj["metadata"]["source"]
        ):
            return FaultRoomSurface(dict_obj)

    raise ValueError(
        f"Cannot read faultroom file. Check if file <{filename}> really is "
        "on FaultRoom format, and has extension 'json' or 'geojson'"
    )


@dataclass
class FaultRoomSurface:
    """Parse the requested props from FaultRoom plugin output format."""

    storage: dict

    horizons: list = field(default_factory=list, init=False)
    faults: list = field(default_factory=list, init=False)
    juxtaposition_fw: list = field(default_factory=list, init=False)
    juxtaposition_hw: list = field(default_factory=list, init=False)
    properties: list = field(default_factory=list, init=False)
    bbox: dict = field(default_factory=dict, init=False)
    name: str = field(default="", init=False)
    tagname: str = field(default="faultroom", init=False)

    def __post_init__(self) -> None:
        self._set_horizons()
        self._set_faults()
        self._set_juxtaposition()
        self._set_properties()
        self._set_bbox()
        self._derive_names()

    def _set_horizons(self) -> None:
        self.horizons = self.storage["metadata"].get("horizons")

    def _set_faults(self) -> None:
        self.faults = self.storage["metadata"]["faults"].get("default")

    def _set_juxtaposition(self) -> None:
        self.juxtaposition_fw = self.storage["metadata"]["juxtaposition"].get("fw")
        self.juxtaposition_hw = self.storage["metadata"]["juxtaposition"].get("hw")

    def _set_properties(self) -> None:
        self.properties = self.storage["metadata"].get("properties")

    def _set_bbox(self) -> None:
        """To get the bounding box, need to scan data."""
        xmin = ymin = zmin = float("inf")
        xmax = ymax = zmax = float("-inf")
        for feature in self.storage["features"]:
            for triangle in feature["geometry"]["coordinates"]:
                for coords in triangle:
                    xcoord, ycoord, zcoord = coords
                    xmin = min(xcoord, xmin)
                    ymin = min(ycoord, ymin)
                    zmin = min(zcoord, zmin)
                    xmax = max(xcoord, xmax)
                    ymax = max(ycoord, ymax)
                    zmax = max(zcoord, zmax)

        self.bbox = {
            "xmin": xmin,
            "xmax": xmax,
            "ymin": ymin,
            "ymax": ymax,
            "zmin": zmin,
            "zmax": zmax,
        }

    def _derive_names(self) -> None:
        """A descriptive name based on metadata for faultroom data.

        The name also includes as short ID based on hash, since there may possible ways
        to make a horizon with multiple (complex) juxtapositions.
        """
        self.name = "_".join(self.horizons)

        file_name = "_".join(self.horizons).lower()
        hash_input = (
            file_name
            + "_".join(self.juxtaposition_fw)
            + "_".join(self.juxtaposition_hw)
        )
        short_hash = hashlib.sha1(hash_input.encode("utf-8")).hexdigest()[:7]
        self.tagname = "faultroom" + "_" + short_hash
