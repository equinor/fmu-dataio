from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    RootModel,
)

from fmu.dataio._models.standard_results import (
    FieldOutlineSchema,
    FluidContactOutlineSchema,
    InplaceVolumesSchema,
    StructureDepthFaultLinesSchema,
)
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

    file_schema: FileSchema | None = Field(default=None)
    """The schema identifying the format of the standard result."""


class InplaceVolumesStandardResult(StandardResult):
    """
    The ``standard_result`` field contains information about which standard results this
    data object represents.

    This class contains metadata for the 'inplace_volumes' standard result.
    """

    name: Literal[enums.StandardResultName.inplace_volumes]
    """The identifying name for the 'inplace_volumes' standard result."""

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
    """The identifying name for the 'structure_depth_surface' standard result."""


class StructureTimeSurfaceStandardResult(StandardResult):
    """
    The ``standard_result`` field contains information about which standard results this
    data object represent.
    This class contains metadata for the 'structure_time_surface' standard result.
    """

    name: Literal[enums.StandardResultName.structure_time_surface]
    """The identifying name for the 'structure_time_surface' standard result."""


class StructureDepthIsochoreStandardResult(StandardResult):
    """
    The ``standard_result`` field contains information about which standard results this
    data object represent.
    This class contains metadata for the 'structure_depth_isochore' standard result.
    """

    name: Literal[enums.StandardResultName.structure_depth_isochore]
    """The identifying name for the 'structure_depth_isochore' standard result."""


class StructureDepthFaultLinesStandardResult(StandardResult):
    """
    The ``standard_result`` field contains information about which standard results this
    data object represent.
    This class contains metadata for the 'structure_depth_fault_lines' standard result.
    """

    name: Literal[enums.StandardResultName.structure_depth_fault_lines]
    """The identifying name for the 'structure_depth_fault_lines' standard result."""

    file_schema: FileSchema = FileSchema(
        version=StructureDepthFaultLinesSchema.VERSION,
        url=AnyHttpUrl(StructureDepthFaultLinesSchema.url()),
    )
    """
    The schema identifying the format of the 'structure_depth_fault_lines'
    standard result.
    """


class FieldOutlineStandardResult(StandardResult):
    """
    The ``standard_result`` field contains information about which standard results this
    data object represent.
    This class contains metadata for the 'field_outline' standard result.
    """

    name: Literal[enums.StandardResultName.field_outline]
    """The identifying name for the 'field_outline' standard result."""

    file_schema: FileSchema = FileSchema(
        version=FieldOutlineSchema.VERSION,
        url=AnyHttpUrl(FieldOutlineSchema.url()),
    )
    """
    The schema identifying the format of the 'field_outline' standard result.
    """


class FluidContactSurfaceStandardResult(StandardResult):
    """
    The ``standard_result`` field contains information about which standard results this
    data object represent.
    This class contains metadata for the 'fluid_contact_surface' standard result.
    """

    name: Literal[enums.StandardResultName.fluid_contact_surface]
    """The identifying name for the 'fluid_contact_surface' standard result."""


class FluidContactOutlineStandardResult(StandardResult):
    """
    The ``standard_result`` field contains information about which standard results this
    data object represent.
    This class contains metadata for the 'fluid_contact_outline' standard result.
    """

    name: Literal[enums.StandardResultName.fluid_contact_outline]
    """The identifying name for the 'fluid_contact_outline' standard result."""

    file_schema: FileSchema = FileSchema(
        version=FluidContactOutlineSchema.VERSION,
        url=AnyHttpUrl(FluidContactOutlineSchema.url()),
    )
    """
    The schema identifying the format of the 'fluid_contact_outline' standard result.
    """


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
        FieldOutlineStandardResult
        | InplaceVolumesStandardResult
        | StructureDepthSurfaceStandardResult
        | StructureTimeSurfaceStandardResult
        | StructureDepthIsochoreStandardResult
        | StructureDepthFaultLinesStandardResult
        | FluidContactSurfaceStandardResult
        | FluidContactOutlineStandardResult,
        Field(discriminator="name"),
    ]
