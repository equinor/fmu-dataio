from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    RootModel,
)
from typing_extensions import Annotated

from fmu.dataio._models.standard_results import InplaceVolumesSchema
from fmu.dataio.types import VersionStr

from . import enums


class FileSchema(BaseModel):
    """The schema identifying the format of a standard result."""

    version: VersionStr
    """The version of the standard result schema."""

    url: AnyHttpUrl
    """The url to the standard result schema."""


class StandardResult(BaseModel):
    """
    The ``standard_result`` field contains information about which standard result this
    data object represents.
    """

    name: enums.StandardResultName
    """The identifying standard result name for this data object."""

    file_schema: Optional[FileSchema] = Field(default=None)
    """The schema identifying the format of the standard result."""


class InplaceVolumesStandardResult(StandardResult):
    """
    The ``standard_result`` field contains information about which standard results this
    data object represents.

    This class contains metadata for the 'inplace_volumes' standard result.
    """

    name: Literal[enums.StandardResultName.inplace_volumes]
    """The identifying standard result name for the 'inplace_volumes' standard
    result."""

    file_schema: FileSchema = FileSchema(
        version=InplaceVolumesSchema.VERSION,
        url=AnyHttpUrl(InplaceVolumesSchema.url()),
    )
    """The schema identifying the format of the 'inplace_volumes' standard result."""


class StructureDepthSurfaceStandardResult(StandardResult):
    """
    The ``standard_result`` field contains information about which standard results this
    data object represent.
    This class contains metadata for the 'structure_depth_surface' standard result.
    """

    name: Literal[enums.StandardResultName.structure_depth_surface]
    """The identifying product name for the 'structure_depth_surface' product."""


class AnyStandardResult(RootModel):
    """
    The ``standard result`` field contains information about which standard result this
    data object represents. Data that is tagged as such is a standard result from FMU
    that conforms to a specified standard.

    This class, ``AnyStandardResult``, acts as a container for different standard
    results, with the exact standard result being identified by the
    ``standard_result.name`` field.
    """

    root: Annotated[
        Union[
            InplaceVolumesStandardResult,
            StructureDepthSurfaceStandardResult,
        ],
        Field(discriminator="name"),
    ]
