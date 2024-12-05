from __future__ import annotations

from typing import TYPE_CHECKING, Final, List, Literal, Optional, Union

from pydantic import BaseModel, Field, RootModel
from pydantic.json_schema import GenerateJsonSchema

if TYPE_CHECKING:
    from typing import Any, Mapping

# These are to be used when creating the 'product' key in metadata.
VERSION: Final[str] = "0.1.0"
SCHEMA: Final[str] = (
    "https://main-fmu-schemas-prod.radix.equinor.com/schemas"
    f"/products/volumes/{VERSION}/inplace_volumes.json"
)  # TODO: This URL is as-yet undecided.


class InplaceVolumesResultRow(BaseModel):
    """Represents a row in a static inplace volumes export.

    These fields are the current agreed upon standard result. Changes to this model
    should increase the version number in a way that corresponds to the schema
    versioning specification (i.e. they are a patch, minor, or major change)."""

    ZONE: Union[str]
    REGION: Union[str]
    FACIES: Optional[Union[str]] = Field(default=None)
    LICENSE: Optional[Union[str, int]] = Field(default=None)

    BULK_OIL: Optional[float] = Field(default=None, ge=0.0)
    NET_OIL: Optional[float] = Field(default=None, ge=0.0)
    PORV_OIL: Optional[float] = Field(default=None, ge=0.0)
    HCPV_OIL: Optional[float] = Field(default=None, ge=0.0)
    STOIIP_OIL: Optional[float] = Field(default=None, ge=0.0)
    ASSOCIATEDGAS_OIL: Optional[float] = Field(default=None, ge=0.0)

    BULK_GAS: Optional[float] = Field(default=None, ge=0.0)
    NET_GAS: Optional[float] = Field(default=None, ge=0.0)
    PORV_GAS: Optional[float] = Field(default=None, ge=0.0)
    HCPV_GAS: Optional[float] = Field(default=None, ge=0.0)
    GIIP_GAS: Optional[float] = Field(default=None, ge=0.0)
    ASSOCIATEDOIL_GAS: Optional[float] = Field(default=None, ge=0.0)

    BULK_TOTAL: float = Field(ge=0.0)
    NET_TOTAL: Optional[float] = Field(default=None, ge=0.0)
    PORV_TOTAL: float = Field(ge=0.0)


class InplaceVolumesResult(RootModel):
    """Represents the resultant static inplace volumes csv file, which is naturally a
    list of rows.

    Consumers who retrieve this csv file must reading it into a json-dictionary
    equivalent format to validate it against the schema."""

    root: List[InplaceVolumesResultRow]


class InplaceVolumesJsonSchema(GenerateJsonSchema):
    """Implements a schema generator so that some additional fields may be added."""

    def generate(
        self,
        schema: Mapping[str, Any],
        mode: Literal["validation", "serialization"] = "validation",
    ) -> dict[str, Any]:
        json_schema = super().generate(schema, mode=mode)
        json_schema["$schema"] = self.schema_dialect
        json_schema["$id"] = SCHEMA
        json_schema["version"] = VERSION

        return json_schema


def dump() -> dict[str, Any]:
    return InplaceVolumesResult.model_json_schema(
        schema_generator=InplaceVolumesJsonSchema
    )
