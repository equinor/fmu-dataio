from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, RootModel

from fmu.dataio._models._schema_base import FmuSchemas, SchemaBase

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from fmu.dataio.types import VersionStr


class FluidContactOutlineResultRow(BaseModel):
    """Represents the columns of a row in a fluid contact outline export.

    These fields are the current agreed upon standard result. Changes to the fields or
    their validation should cause the version defined in the standard result schema to
    increase the version number in a way that corresponds to the schema versioning
    specification (i.e. they are a patch, minor, or major change)."""

    X_UTME: float
    """The X coordinate this row represents. Required."""

    Y_UTMN: float
    """The Y coordinate this row represents. Required."""

    Z_TVDSS: float
    """The Z coordinate (depth) this row represents. Required."""

    POLY_ID: int = Field(ge=0)
    """Index column. The id of the polygon which this row represents. Required."""


class FluidContactOutlineResult(RootModel):
    """Represents the resultant fluid contact outline parquet file, which is
    naturally a list of rows.

    Consumers who retrieve this parquet file must read it into a json-dictionary
    equivalent format to validate it against the schema."""

    root: list[FluidContactOutlineResultRow]


class FluidContactOutlineSchema(SchemaBase):
    """This class represents the schema that is used to validate the fault lines
    table being exported. This means that the version, schema filename, and schema
    location corresponds directly with the values and their validation constraints,
    documented above."""

    VERSION: VersionStr = "0.1.0"
    """The version of this schema."""

    VERSION_CHANGELOG: str = """
    #### 0.1.0

    This is the initial schema version.
    """

    FILENAME: str = "fluid_contact_outline.json"
    """The filename this schema is written to."""

    PATH: Path = FmuSchemas.PATH / "file_formats" / VERSION / FILENAME
    """The local and URL path of this schema."""

    @classmethod
    def dump(cls) -> dict[str, Any]:
        return FluidContactOutlineResult.model_json_schema(
            schema_generator=cls.default_generator()
        )
