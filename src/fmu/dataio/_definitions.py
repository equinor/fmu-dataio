"""Various definitions and hard settings used in fmu-dataio."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Final

SOURCE: Final = "fmu"


class ValidationError(ValueError, KeyError):
    """Raise error while validating."""


class ConfigurationError(ValueError):
    pass


class FmuSchemas:
    """These URLs can be constructed programmatically from radixconfig.yaml if need be:

        {cfg.components[].name}-{cfg.metadata.name}-{spec.environments[].name}

    As they are unlikely to change they are hardcoded here.
    """

    DEV_URL: Final[str] = "https://main-fmu-schemas-dev.radix.equinor.com"
    PROD_URL: Final[str] = "https://main-fmu-schemas-prod.radix.equinor.com"
    PATH: Final[Path] = Path("schemas")


class SchemaBase(ABC):
    VERSION: str
    """The current version of the schema."""

    FILENAME: str
    """The filename, i.e. schema.json."""

    PATH: Path
    """The on-disk _and_ URL path following the domain, i.e:

        schemas/0.1.0/schema.json

    This path should _always_ have `FmuSchemas.PATH` as its first parent.
    This determines the on-disk and URL location of this schema file. A
    trivial example is:

        PATH: Path = FmuSchemas.PATH / VERSION / FILENAME

    """

    @classmethod
    def __init_subclass__(cls, **kwargs: dict[str, Any]) -> None:
        super().__init_subclass__(**kwargs)
        for attr in ("VERSION", "FILENAME", "PATH"):
            if not hasattr(cls, attr):
                raise TypeError(f"Subclass {cls.__name__} must define '{attr}'")

        if not cls.PATH.parts[0].startswith(str(FmuSchemas.PATH)):
            raise ValueError(
                f"PATH must start with `FmuSchemas.PATH`: {FmuSchemas.PATH}. "
                f"Got {cls.PATH}"
            )

    @classmethod
    def url(cls) -> str:
        """Returns the URL this file will reside at, based upon class variables set here
        and in FmuSchemas."""
        DEV_URL = f"{FmuSchemas.DEV_URL}/{cls.PATH}"
        PROD_URL = f"{FmuSchemas.PROD_URL}/{cls.PATH}"

        if os.environ.get("SCHEMA_RELEASE", False):
            return PROD_URL
        return DEV_URL

    @staticmethod
    @abstractmethod
    def dump() -> dict[str, Any]:
        """
        Dumps the export root model to JSON format for schema validation and
        usage in FMU data structures.

        To update the schema:
            1. Run the following CLI command to dump the updated schema:
                `./tools/update_schema`.
            2. Check the diff for changes. Adding fields usually indicates non-breaking
                changes and is generally safe. However, if fields are removed, it could
                indicate breaking changes that may affect dependent systems. Perform a
                quality control (QC) check to ensure these changes do not break existing
                implementations.
                If changes are satisfactory and do not introduce issues, commit
                them to maintain schema consistency.
        """
        raise NotImplementedError


class ValidFormats(Enum):
    surface = {
        "irap_binary": ".gri",
    }

    grid = {
        "hdf": ".hdf",
        "roff": ".roff",
    }

    cube = {
        "segy": ".segy",
    }

    table = {
        "hdf": ".hdf",
        "csv": ".csv",
        "parquet": ".parquet",
    }

    polygons = {
        "hdf": ".hdf",
        "csv": ".csv",  # columns will be X Y Z, ID
        "csv|xtgeo": ".csv",  # use default xtgeo columns: X_UTME, ... POLY_ID
        "irap_ascii": ".pol",
    }

    points = {
        "hdf": ".hdf",
        "csv": ".csv",  # columns will be X Y Z
        "csv|xtgeo": ".csv",  # use default xtgeo columns: X_UTME, Y_UTMN, Z_TVDSS
        "irap_ascii": ".poi",
    }

    dictionary = {
        "json": ".json",
    }


class ExportFolder(str, Enum):
    cubes = "cubes"
    dictionaries = "dictionaries"
    grids = "grids"
    maps = "maps"
    points = "points"
    polygons = "polygons"
    tables = "tables"


STANDARD_TABLE_INDEX_COLUMNS: Final[dict[str, list[str]]] = {
    "volumes": ["ZONE", "REGION", "FACIES", "LICENCE"],
    "rft": ["measured_depth", "well", "time"],
    "timeseries": ["DATE"],
    "simulationtimeseries": ["DATE"],
    "wellpicks": ["WELL", "HORIZON"],
}
