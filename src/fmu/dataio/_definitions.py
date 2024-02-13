"""Various definitions and hard settings used in fmu-dataio."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Final

SCHEMA: Final = (
    "https://main-fmu-schemas-prod.radix.equinor.com/schemas/0.8.0/fmu_results.json"
)
VERSION: Final = "0.8.0"
SOURCE: Final = "fmu"


class ValidationError(ValueError, KeyError):
    """Raise error while validating."""


@dataclass
class _ValidFormats:
    surface: dict[str, str] = field(
        default_factory=lambda: {
            "irap_binary": ".gri",
        }
    )
    grid: dict[str, str] = field(
        default_factory=lambda: {
            "hdf": ".hdf",
            "roff": ".roff",
        }
    )
    cube: dict[str, str] = field(
        default_factory=lambda: {
            "segy": ".segy",
        }
    )
    table: dict[str, str] = field(
        default_factory=lambda: {
            "hdf": ".hdf",
            "csv": ".csv",
            "arrow": ".arrow",
        }
    )
    polygons: dict[str, str] = field(
        default_factory=lambda: {
            "hdf": ".hdf",
            "csv": ".csv",  # columns will be X Y Z, ID
            "csv|xtgeo": ".csv",  # use default xtgeo columns: X_UTME, ... POLY_ID
            "irap_ascii": ".pol",
        }
    )
    points: dict[str, str] = field(
        default_factory=lambda: {
            "hdf": ".hdf",
            "csv": ".csv",  # columns will be X Y Z
            "csv|xtgeo": ".csv",  # use default xtgeo columns: X_UTME, Y_UTMN, Z_TVDSS
            "irap_ascii": ".poi",
        }
    )
    dictionary: dict[str, str] = field(
        default_factory=lambda: {
            "json": ".json",
        }
    )


ALLOWED_CONTENTS: Final = {
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

STANDARD_TABLE_INDEX_COLUMNS: Final = {
    "inplace_volumes": ["ZONE", "REGION", "FACIES", "LICENCE"],
    "timeseries": ["DATE"],  # summary
    "rft": ["measured_depth", "well", "time"],
    "wellpicks": ["WELL", "HORIZON"],
}

DEPRECATED_CONTENTS: Final = {
    "seismic": {
        "offset": {
            "replaced_by": "stacking_offset",
        }
    }
}

# This setting will set if subkeys is required or not. If not found in list then
# assume False.
CONTENTS_REQUIRED: Final = {
    "fluid_contact": {"contact": True},
    "field_outline": {"contact": False},
    "field_region": {"id": True},
}

# This setting sets the FMU context for the output. If detected as a non-fmu run,
# the code will internally set actual_context=None
ALLOWED_FMU_CONTEXTS: Final = {
    "realization": "To realization-N/iter_M/share",
    "case": "To casename/share, but will also work on project disk",
    "case_symlink_realization": "To case/share, with symlinks on realizations level",
    "preprocessed": "To share/preprocessed; from interactive runs but re-used later",
}


@unique
class FmuContext(Enum):
    """Use a Enum class for fmu_context entries."""

    REALIZATION = "To realization-N/iter_M/share"
    CASE = "To casename/share, but will also work on project disk"
    CASE_SYMLINK_REALIZATION = "To case/share, with symlinks on realizations level"
    PREPROCESSED = "To share/preprocessed; from interactive runs but re-used later"
    NON_FMU = "Not ran in a FMU setting, e.g. interactive RMS"

    @classmethod
    def has_key(cls, key: str) -> bool:
        return key.upper() in cls._member_names_

    @classmethod
    def list_valid(cls) -> dict:
        return {member.name: member.value for member in cls}

    @classmethod
    def get(cls, key: FmuContext | str) -> FmuContext:
        """Get the enum member with a case-insensitive key."""
        if isinstance(key, cls):
            key_upper = key.name
        elif isinstance(key, str):
            key_upper = key.upper()
        else:
            raise ValidationError("The input must be a str or FmuContext instance")

        if not cls.has_key(key_upper):
            raise ValidationError(
                f"Invalid key <{key_upper}>. Valid keys: {cls.list_valid().keys()}"
            )

        return cls[key_upper]
