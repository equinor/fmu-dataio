from __future__ import annotations

from enum import Enum, IntEnum
from typing import Type


class ContentEnum(str, Enum):
    depth = "depth"
    facies_thickness = "facies_thickness"
    fault_lines = "fault_lines"
    fault_properties = "fault_properties"
    field_outline = "field_outline"
    field_region = "field_region"
    fluid_contact = "fluid_contact"
    khproduct = "khproduct"
    lift_curves = "lift_curves"
    named_area = "named_area"
    parameters = "parameters"
    pinchout = "pinchout"
    property = "property"
    pvt = "pvt"
    regions = "regions"
    relperm = "relperm"
    rft = "rft"
    seismic = "seismic"
    subcrop = "subcrop"
    thickness = "thickness"
    time = "time"
    timeseries = "timeseries"
    transmissibilities = "transmissibilities"
    velocity = "velocity"
    volumes = "volumes"
    wellpicks = "wellpicks"

    @classmethod
    def _missing_(cls: Type[ContentEnum], value: object) -> None:
        raise ValueError(
            f"Invalid 'content' {value=}. Valid entries are {[m.value for m in cls]}"
        )


class FMUClassEnum(str, Enum):
    case = "case"
    surface = "surface"
    table = "table"
    cpgrid = "cpgrid"
    cpgrid_property = "cpgrid_property"
    polygons = "polygons"
    cube = "cube"
    well = "well"
    points = "points"
    dictionary = "dictionary"


class AccessLevel(str, Enum):
    asset = "asset"
    internal = "internal"
    restricted = "restricted"


class AxisOrientation(IntEnum):
    normal = 1
    flipped = -1
