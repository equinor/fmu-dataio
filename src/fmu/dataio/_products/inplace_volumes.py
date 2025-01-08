from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Literal, Optional, TypeVar

from pydantic import BaseModel, Field, RootModel
from pydantic.json_schema import GenerateJsonSchema

from fmu.dataio._definitions import FmuSchemas, SchemaBase
from fmu.dataio.export._enums import InplaceVolumes

if TYPE_CHECKING:
    from typing import Any, Mapping

T = TypeVar("T", Dict, List, object)


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

    class InplaceVolumesGenerateJsonSchema(GenerateJsonSchema):
        """Implements a schema generator so that some additional fields may be added."""

        def _remove_format_path(self, obj: T) -> T:
            """
            Removes entries with key "format" and value "path" from dictionaries. This
            adjustment is necessary because JSON Schema does not recognize the "format":
            "path", while OpenAPI does. This function is used in contexts where OpenAPI
            specifications are not applicable.
            """

            if isinstance(obj, dict):
                return {
                    k: self._remove_format_path(v)
                    for k, v in obj.items()
                    if not (k == "format" and v == "path")
                }

            if isinstance(obj, list):
                return [self._remove_format_path(element) for element in obj]

            return obj

        def generate(
            self,
            schema: Mapping[str, Any],
            mode: Literal["validation", "serialization"] = "validation",
        ) -> dict[str, Any]:
            json_schema = super().generate(schema, mode=mode)
            json_schema["$schema"] = self.schema_dialect
            json_schema["$id"] = InplaceVolumesSchema.url()
            json_schema["version"] = InplaceVolumesSchema.VERSION

            return json_schema

    @staticmethod
    def dump() -> dict[str, Any]:
        return InplaceVolumesResult.model_json_schema(
            schema_generator=InplaceVolumesSchema.InplaceVolumesGenerateJsonSchema
        )
