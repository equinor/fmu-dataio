from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, Field, RootModel

from fmu.dataio._models._schema_base import FmuSchemas, SchemaBase
from fmu.dataio.export._enums import InplaceVolumes
from fmu.dataio.types import VersionStr

if TYPE_CHECKING:
    from typing import Any


class InplaceVolumesResultRow(BaseModel):
    """Represents the columns of a row in a static inplace volumes export.

    These fields are the current agreed upon standard result. Changes to the fields or
    their validation should cause the version defined in the prodct schema to
    increase the version number in a way that corresponds to the schema versioning
    specification (i.e. they are a patch, minor, or major change)."""

    FLUID: InplaceVolumes.Fluid
    """Index column. The kind of fluid this row represents. Typically GAS, OIL, or
    WATER. Required.
    """

    ZONE: str
    """Index column. The zone from which this volume is coming from. Required."""

    REGION: str
    """Index column. The region from which this volume is coming from. Required."""

    FACIES: Optional[str] = Field(default=None)
    """Index column. The facies from which is volume is coming from. Optional."""

    LICENSE: Optional[str] = Field(default=None)
    """Index column. The license under which these volumes related to. Optional."""

    BULK: float = Field(ge=0.0)
    """The bulk volume of the fluid-type given in ``FLUID``. Required."""

    NET: float = Field(ge=0.0)
    """The net volume of the fluid-type given in ``FLUID``. Required."""

    PORV: float = Field(ge=0.0)
    """The pore volume of the fluid-type given in ``FLUID``. Required."""

    HCPV: Optional[float] = Field(default=None, ge=0.0)
    """The pore volume of the fluid-type given in ``FLUID``. Optional."""

    STOIIP: Optional[float] = Field(default=None, ge=0.0)
    """The STOIIP volume of the fluid-type given in ``FLUID``. Optional."""

    GIIP: Optional[float] = Field(default=None, ge=0.0)
    """The GIIP volume of the fluid-type given in ``FLUID``. Optional."""

    ASSOCIATEDGAS: Optional[float] = Field(default=None, ge=0.0)
    """The associated gas volume of the fluid-type given in ``FLUID``. Optional."""

    ASSOCIATEDOIL: Optional[float] = Field(default=None, ge=0.0)
    """The associated oil volume of the fluid-type given in ``FLUID``. Optional."""


class InplaceVolumesResult(RootModel):
    """Represents the resultant static inplace volumes csv file, which is naturally a
    list of rows.

    Consumers who retrieve this csv file must reading it into a json-dictionary
    equivalent format to validate it against the schema."""

    root: List[InplaceVolumesResultRow]


class InplaceVolumesSchema(SchemaBase):
    """This class represents the schema that is used to validate the inplace volumes
    table being exported. This means that the version, schema filename, and schema
    locaiton corresponds directly with the values and their validation constraints,
    documented above."""

    VERSION: VersionStr = "0.1.0"
    """The version of this schema."""

    FILENAME: str = "inplace_volumes.json"
    """The filename this schema is written to."""

    PATH: Path = FmuSchemas.PATH / "file_formats" / VERSION / FILENAME
    """The local and URL path of this schema."""

    @classmethod
    def dump(cls) -> dict[str, Any]:
        return InplaceVolumesResult.model_json_schema(
            schema_generator=cls.default_generator()
        )
