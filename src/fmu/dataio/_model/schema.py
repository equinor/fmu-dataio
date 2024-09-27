"""
This module, `_model.schema`, contains internal data structures that
are designed to depend on external modules, but not the other way around.
This design ensures modularity and flexibility, allowing external modules
to be potentially separated into their own repositories without dependencies
on the internals.
"""

from __future__ import annotations

import warnings
from textwrap import dedent
from typing import List, Literal, Optional, Union

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    TypeAdapter,
    model_validator,
)

from fmu.dataio._definitions import SCHEMA, SOURCE, VERSION

from . import data, enums, fields


def property_warn() -> None:
    warnings.warn(
        dedent(
            """
            When using content "property", please use a dictionary form, as
            more information is required. Example:
                content={"property": {"is_discrete": False}}

            The use of "property" will be disallowed in future versions."
            """
        ),
        FutureWarning,
    )


class AllowedContentSeismic(data.Seismic):
    # Deprecated
    offset: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def _check_depreciated(self) -> AllowedContentSeismic:
        if self.offset is not None:
            warnings.warn(
                "Content seismic.offset is deprecated. "
                "Please use seismic.stacking_offset insted.",
                DeprecationWarning,
            )
            self.stacking_offset, self.offset = self.offset, None
        return self


class AllowedContentProperty(BaseModel):
    # needs to be here for now, as it is not defined in the schema
    attribute: Optional[str] = Field(default=None)
    is_discrete: Optional[bool] = Field(default=None)


class ContentRequireSpecific(BaseModel):
    field_outline: Optional[data.FieldOutline] = Field(default=None)
    field_region: Optional[data.FieldRegion] = Field(default=None)
    fluid_contact: Optional[data.FluidContact] = Field(default=None)
    property: Optional[AllowedContentProperty] = Field(default=None)
    seismic: Optional[AllowedContentSeismic] = Field(default=None)


class AllowedContent(BaseModel):
    content: Union[enums.Content, Literal["unset"]]
    content_incl_specific: Optional[ContentRequireSpecific] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def _validate_input(cls, values: dict) -> dict:
        content = values.get("content")
        content_specific = values.get("content_incl_specific", {}).get(content)

        if content in ContentRequireSpecific.model_fields and not content_specific:
            # 'property' should be included below after a deprecation period
            if content == enums.Content.property:
                property_warn()
            else:
                raise ValueError(f"Content {content} requires additional input")

        if content_specific and not isinstance(content_specific, dict):
            raise ValueError(
                "Content is incorrectly formatted. When giving content as a dict, "
                "it must be formatted as: "
                "{'mycontent': {extra_key: extra_value}} where mycontent is a string "
                "and in the list of valid contents, and extra keys in associated "
                "dictionary must be valid keys for this content."
            )

        return values


class JsonSchemaMetadata(BaseModel, populate_by_name=True):
    schema_: AnyHttpUrl = Field(
        alias="$schema",
        default=TypeAdapter(AnyHttpUrl).validate_python(SCHEMA),
    )
    version: str = Field(default=VERSION)
    source: str = Field(default=SOURCE)


class Context(BaseModel, use_enum_values=True):
    stage: enums.FMUContext


# Remove the two models below when content is required as input.
class InternalUnsetData(data.Data):
    content: Literal["unset"]  # type: ignore

    @model_validator(mode="after")
    def _deprecation_warning(self) -> InternalUnsetData:
        valid_contents = [m.value for m in enums.Content]
        warnings.warn(
            "The <content> is not provided which will produce invalid metadata. "
            "In the future 'content' will be required explicitly! "
            f"\n\nValid contents are: {', '.join(valid_contents)} "
            "\n\nThis list can be extended upon request and need.",
            FutureWarning,
        )
        return self


class InternalFMU(fields.FMU):
    # This class is identical to the one used in the schema
    # exept for more fmu context values beeing allowed internally
    context: Context  # type: ignore


class InternalObjectMetadata(JsonSchemaMetadata):
    # TODO: aim to use root.ObjectMetadata as base
    # class and disallow creating invalid metadata.
    class_: Literal[
        enums.FMUClass.surface,
        enums.FMUClass.table,
        enums.FMUClass.cpgrid,
        enums.FMUClass.cpgrid_property,
        enums.FMUClass.polygons,
        enums.FMUClass.cube,
        enums.FMUClass.well,
        enums.FMUClass.points,
        enums.FMUClass.dictionary,
    ] = Field(alias="class")
    fmu: Optional[InternalFMU]
    masterdata: Optional[fields.Masterdata]
    access: Optional[fields.SsdlAccess]
    data: Union[InternalUnsetData, data.AnyData]  # keep InternalUnsetData first here
    file: fields.File
    display: fields.Display
    tracklog: fields.Tracklog
    preprocessed: Optional[bool] = Field(alias="_preprocessed", default=None)


class InternalCaseMetadata(JsonSchemaMetadata):
    class_: Literal["case"] = Field(alias="class", default="case")
    masterdata: fields.Masterdata
    access: fields.Access
    fmu: fields.FMUBase
    description: Optional[List[str]] = Field(default=None)
    tracklog: fields.Tracklog
