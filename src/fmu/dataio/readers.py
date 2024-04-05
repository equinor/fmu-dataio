"""Module for reading data not supported by other tools"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


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
