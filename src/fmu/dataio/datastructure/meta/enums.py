from __future__ import annotations

from enum import Enum, IntEnum


class ContentEnum(str, Enum):
    depth = "depth"
    facies_thickness = "facies_thickness"
    fault_lines = "fault_lines"
    field_outline = "field_outline"
    field_region = "field_region"
    fluid_contact = "fluid_contact"
    inplace_volumes = "inplace_volumes"
    khproduct = "khproduct"
    lift_curves = "lift_curves"
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
    volumetrics = "volumetrics"
    wellpicks = "wellpicks"


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
