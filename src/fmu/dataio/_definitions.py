"""Various definitions and hard settings used in fmu-dataio."""
from dataclasses import dataclass, field

SCHEMA = (
    "https://main-fmu-schemas-prod.radix.equinor.com/schemas/0.8.0/fmu_results.json"
)
VERSION = "0.8.0"
SOURCE = "fmu"


@dataclass
class _ValidFormats:
    surface: dict = field(default_factory=dict)
    grid: dict = field(default_factory=dict)
    cube: dict = field(default_factory=dict)
    table: dict = field(default_factory=dict)
    polygons: dict = field(default_factory=dict)
    points: dict = field(default_factory=dict)
    dictionary: dict = field(default_factory=dict)

    def __post_init__(self):
        self.surface = {"irap_binary": ".gri"}
        self.grid = {"hdf": ".hdf", "roff": ".roff"}
        self.cube = {"segy": ".segy"}
        self.table = {"hdf": ".hdf", "csv": ".csv", "arrow": ".arrow"}
        self.polygons = {
            "hdf": ".hdf",
            "csv": ".csv",  # columns will be X Y Z, ID
            "csv|xtgeo": ".csv",  # use default xtgeo columns: X_UTME, ... POLY_ID
            "irap_ascii": ".pol",
        }
        self.points = {
            "hdf": ".hdf",
            "csv": ".csv",  # columns will be X Y Z
            "csv|xtgeo": ".csv",  # use default xtgeo columns: X_UTME, Y_UTMN, Z_TVDSS
            "irap_ascii": ".poi",
        }
        self.dictionary = {"json": ".json"}


ALLOWED_CONTENTS = {
    "depth": None,
    "time": None,
    "thickness": None,
    "property": {"attribute": str, "is_discrete": bool},
    "seismic": {
        "attribute": str,  # e.g. amplitude
        "calculation": str,  # e.g. mean
        "zrange": float,
        "filter_size": float,
        "scaling_factor": float,
        "stacking_offset": str,
    },
    "fluid_contact": {"contact": str, "truncated": bool},
    "field_outline": {"contact": str},
    "field_region": {"id": int},
    "regions": None,
    "pinchout": None,
    "subcrop": None,
    "fault_lines": None,
    "velocity": None,
    "volumes": None,
    "volumetrics": None,  # or?
    "inplace_volumes": None,  # or?
    "khproduct": None,
    "timeseries": None,
    "wellpicks": None,
    "parameters": None,
    "rft": None,
    "pvt": None,
    "relperm": None,
    "lift_curves": None,
    "transmissibilities": None,
}

STANDARD_TABLE_INDEX_COLUMNS = {
    "inplace_volumes": ["ZONE", "REGION", "FACIES", "LICENCE"],
    "timeseries": ["DATE"],  # summary
    "rft": ["measured_depth", "well", "time"],
    "wellpicks": ["WELL", "HORIZON"],
}

DEPRECATED_CONTENTS = {
    "seismic": {
        "offset": {
            "replaced_by": "stacking_offset",
        }
    }
}

# This setting will set if subkeys is required or not. If not found in list then
# assume False.
CONTENTS_REQUIRED = {
    "fluid_contact": {"contact": True},
    "field_outline": {"contact": False},
    "field_region": {"id": True},
}

# This setting sets the FMU context for the output. If detected as a non-fmu run,
# the code will internally set actual_context=None
ALLOWED_FMU_CONTEXTS = {
    "realization": "To realization-N/iter_M/share",
    "case": "To casename/share, but will also work on project disk",
    "case_symlink_realization": "To case/share, with symlinks on realizations level",
    "preprocessed": "To share/preprocessed; from interactive runs but re-used later",
}
