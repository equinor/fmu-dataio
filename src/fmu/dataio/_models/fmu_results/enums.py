from __future__ import annotations

from enum import Enum, IntEnum, StrEnum


class StandardResultName(StrEnum):
    """The standard result name of a given data object."""

    field_outline = "field_outline"
    inplace_volumes = "inplace_volumes"
    structure_depth_surface = "structure_depth_surface"
    structure_time_surface = "structure_time_surface"
    structure_depth_isochore = "structure_depth_isochore"
    structure_depth_fault_lines = "structure_depth_fault_lines"
    structure_depth_fault_surface = "structure_depth_fault_surface"
    fluid_contact_surface = "fluid_contact_surface"
    fluid_contact_outline = "fluid_contact_outline"


class Classification(StrEnum):
    """The security classification for a given data object."""

    asset = "asset"
    internal = "internal"
    restricted = "restricted"


class AxisOrientation(IntEnum):
    """The axis orientation for a given data object."""

    normal = 1
    flipped = -1


class Content(StrEnum):
    """The content type of a given data object."""

    depth = "depth"
    facies_thickness = "facies_thickness"
    fault_triangulated_surface = "fault_triangulated_surface"
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
    simulationtimeseries = "simulationtimeseries"
    subcrop = "subcrop"
    thickness = "thickness"
    time = "time"
    timeseries = "timeseries"
    transmissibilities = "transmissibilities"
    velocity = "velocity"
    volumes = "volumes"
    wellpicks = "wellpicks"

    @classmethod
    def _missing_(cls: type[Content], value: object) -> None:
        raise ValueError(
            f"Invalid 'content' {value=}. Valid entries are {[m.value for m in cls]}"
        )


class ErtSimulationMode(str, Enum):
    """The simulation mode ert was run in. These definitions come from
    `ert.mode_definitions`."""

    ensemble_experiment = "ensemble_experiment"
    ensemble_information_filter = "ensemble_information_filter"
    ensemble_smoother = "ensemble_smoother"
    es_mda = "es_mda"
    evaluate_ensemble = "evaluate_ensemble"
    manual_update = "manual_update"
    test_run = "test_run"
    workflow = "workflow"


class MetadataClass(StrEnum):
    """Base class for objects by FMU convention or standards."""


class ObjectMetadataClass(MetadataClass):
    """The class of a data object (typically originating from an RMS model)."""

    surface = "surface"
    triangulated_surface = "triangulated_surface"
    table = "table"
    cpgrid = "cpgrid"
    cpgrid_property = "cpgrid_property"
    polygons = "polygons"
    cube = "cube"
    well = "well"
    points = "points"
    dictionary = "dictionary"


class FMUResultsMetadataClass(MetadataClass):
    """The class of an FMU results object."""

    case = "case"
    realization = "realization"
    iteration = "iteration"
    ensemble = "ensemble"


class Layout(StrEnum):
    """The layout of a given data object."""

    regular = "regular"
    unset = "unset"
    cornerpoint = "cornerpoint"
    table = "table"
    dictionary = "dictionary"
    faultroom_triangulated = "faultroom_triangulated"
    triangulated_surface = "triangulated_surface"


class FMUContext(str, Enum):
    """The context in which FMU was being run when data were generated."""

    case = "case"
    iteration = "iteration"
    ensemble = "ensemble"
    realization = "realization"


class VerticalDomain(StrEnum):
    depth = "depth"
    time = "time"


class DomainReference(StrEnum):
    msl = "msl"
    sb = "sb"
    rkb = "rkb"


class TrackLogEventType(StrEnum):
    """The type of event being logged"""

    created = "created"
    updated = "updated"
    merged = "merged"


class FluidContactType(StrEnum):
    """The type of fluid contact."""

    fgl = "fgl"
    """Free gas level."""

    fwl = "fwl"
    """Free water level."""

    goc = "goc"
    """Gas-oil contact."""

    gwc = "gwc"
    """Gas-water contact."""

    owc = "owc"
    """Oil-water contact."""


class FileFormat(StrEnum):
    """The format of a given data object."""

    parquet = "parquet"
    json = "json"
    csv = "csv"
    csv_xtgeo = "csv|xtgeo"
    irap_ascii = "irap_ascii"
    irap_binary = "irap_binary"
    roff = "roff"
    segy = "segy"
    openvds = "openvds"
    tsurf = "tsurf"
