"""
This module, `datastructure._internal`, contains internal data structures that
are designed to depend on external modules, but not the other way around.
This design ensures modularity and flexibility, allowing external modules
to be potentially separated into their own repositories without dependencies
on the internals.
"""

from __future__ import annotations

import warnings
from textwrap import dedent
from typing import List, Literal, Optional, Union

from fmu.dataio._definitions import SCHEMA, SOURCE, VERSION, FmuContext
from fmu.dataio.datastructure.configuration.global_configuration import (
    Model as GlobalConfigurationModel,
)
from fmu.dataio.datastructure.meta import meta
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    TypeAdapter,
    model_validator,
)


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


class AllowedContentSeismic(meta.content.Seismic):
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
    field_outline: Optional[meta.content.FieldOutline] = Field(default=None)
    field_region: Optional[meta.content.FieldRegion] = Field(default=None)
    fluid_contact: Optional[meta.content.FluidContact] = Field(default=None)
    property: Optional[AllowedContentProperty] = Field(default=None)
    seismic: Optional[AllowedContentSeismic] = Field(default=None)


class AllowedContent(BaseModel):
    content: Union[meta.enums.ContentEnum, Literal["unset"]]
    content_incl_specific: Optional[ContentRequireSpecific] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def _validate_input(cls, values: dict) -> dict:
        content = values.get("content")
        content_specific = values.get("content_incl_specific", {}).get(content)

        if content in ContentRequireSpecific.model_fields and not content_specific:
            # 'property' should be included below after a deprecation period
            if content == meta.enums.ContentEnum.property:
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


class FMUModel(BaseModel):
    model: GlobalConfigurationModel
    case: meta.FMUCase


class Context(BaseModel, use_enum_values=True):
    stage: FmuContext


# Remove the two models below when content is required as input.
class UnsetContent(meta.content.Content):
    content: Literal["unset"]  # type: ignore

    @model_validator(mode="after")
    def _deprecation_warning(self) -> UnsetContent:
        valid_contents = [m.value for m in meta.enums.ContentEnum]
        warnings.warn(
            "The <content> is not provided which will produce invalid metadata. "
            "It is strongly recommended that content is given explicitly! "
            f"\n\nValid contents are: {', '.join(valid_contents)} "
            "\n\nThis list can be extended upon request and need.",
            UserWarning,
        )
        return self


class UnsetAnyContent(meta.content.AnyContent):
    root: UnsetContent  # type: ignore


class FMUClassMetaData(meta.FMUClassMetaData):
    # This class is identical to the one used in the schema
    # exept for more fmu context values beeing allowed internally
    context: Context  # type: ignore


class DataClassMeta(JsonSchemaMetadata):
    # TODO: aim to use meta.FMUDataClassMeta as base
    # class and disallow creating invalid metadata.
    class_: Literal[
        meta.enums.FMUClassEnum.surface,
        meta.enums.FMUClassEnum.table,
        meta.enums.FMUClassEnum.cpgrid,
        meta.enums.FMUClassEnum.cpgrid_property,
        meta.enums.FMUClassEnum.polygons,
        meta.enums.FMUClassEnum.cube,
        meta.enums.FMUClassEnum.well,
        meta.enums.FMUClassEnum.points,
        meta.enums.FMUClassEnum.dictionary,
    ] = Field(alias="class")
    fmu: Optional[FMUClassMetaData]
    masterdata: Optional[meta.Masterdata]
    access: Optional[meta.SsdlAccess]
    data: Union[meta.content.AnyContent, UnsetAnyContent]
    file: meta.File
    display: meta.Display
    tracklog: List[meta.TracklogEvent]
    preprocessed: Optional[bool] = Field(alias="_preprocessed", default=None)


class CaseSchema(JsonSchemaMetadata):
    class_: Literal["case"] = Field(alias="class", default="case")
    masterdata: meta.Masterdata
    access: meta.Access
    fmu: FMUModel
    description: Optional[List[str]] = Field(default=None)
    tracklog: List[meta.TracklogEvent]
