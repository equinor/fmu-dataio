from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, Field, RootModel

from fmu.dataio._models._schema_base import FmuSchemas, SchemaBase
from fmu.dataio.export._enums import InplaceVolumes

if TYPE_CHECKING:
    from typing import Any


class InplaceVolumesResultRow(BaseModel):
    """Represents a row in a static inplace volumes export.

    These fields are the current agreed upon standard result. Changes to this model
    should increase the version number in a way that corresponds to the schema
    versioning specification (i.e. they are a patch, minor, or major change)."""

    FLUID: InplaceVolumes.Fluid
    ZONE: str
    REGION: str
    FACIES: Optional[str] = Field(default=None)
    LICENSE: Optional[str] = Field(default=None)

    BULK: float = Field(ge=0.0)
    NET: float = Field(ge=0.0)
    PORV: float = Field(ge=0.0)
    HCPV: Optional[float] = Field(default=None, ge=0.0)
    STOIIP: Optional[float] = Field(default=None, ge=0.0)
    GIIP: Optional[float] = Field(default=None, ge=0.0)
    ASSOCIATEDGAS: Optional[float] = Field(default=None, ge=0.0)
    ASSOCIATEDOIL: Optional[float] = Field(default=None, ge=0.0)


class InplaceVolumesResult(RootModel):
    """Represents the resultant static inplace volumes csv file, which is naturally a
    list of rows.

    Consumers who retrieve this csv file must reading it into a json-dictionary
    equivalent format to validate it against the schema."""

    root: List[InplaceVolumesResultRow]


class InplaceVolumesSchema(SchemaBase):
    VERSION: str = "0.1.0"
    FILENAME: str = "inplace_volumes.json"
    PATH: Path = FmuSchemas.PATH / "file_formats" / VERSION / FILENAME

    @classmethod
    def dump(cls) -> dict[str, Any]:
        return InplaceVolumesResult.model_json_schema(
            schema_generator=cls.default_generator()
        )
