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

from fmu.dataio._definitions import SCHEMA, SOURCE, VERSION
from fmu.dataio.datastructure.configuration.global_configuration import (
    Model as GlobalConfigurationModel,
)
from fmu.dataio.datastructure.meta.meta import Access, Masterdata, TracklogEvent, User
from pydantic import AnyHttpUrl, BaseModel, Field, TypeAdapter, model_validator


def seismic_warn() -> None:
    warnings.warn(
        dedent(
            """
            When using content "seismic", please use a dictionary form, as
            more information is required. Example:
                content={"seismic": {"attribute": "amplitude"}}

            The use of "seismic" will be disallowed in future versions."
            """
        ),
        FutureWarning,
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


class AllowedContentSeismic(BaseModel):
    attribute: Optional[str] = Field(default=None)  # e.g. amplitude
    calculation: Optional[str] = Field(default=None)  # e.g. mean
    zrange: Optional[float] = Field(default=None)
    filter_size: Optional[float] = Field(default=None)
    scaling_factor: Optional[float] = Field(default=None)
    stacking_offset: Optional[str] = Field(default=None)

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
    attribute: Optional[str] = Field(default=None)
    is_discrete: Optional[bool] = Field(default=None)


class AllowedContentFluidContact(BaseModel):
    contact: Optional[str] = Field(default=None)
    truncated: Optional[bool] = Field(default=None)


class AllowedContentFieldOutline(BaseModel):
    contact: Optional[str] = Field(default=None)


class AllowedContentFieldRegion(BaseModel):
    id: Optional[int] = Field(default=None)


class AllowedContent(BaseModel):
    depth: None = Field(default=None)
    time: None = Field(default=None)
    thickness: None = Field(default=None)
    property: Optional[Union[AllowedContentProperty, str]] = Field(default=None)
    seismic: Optional[Union[AllowedContentSeismic, str]] = Field(default=None)
    fluid_contact: Optional[AllowedContentFluidContact] = Field(default=None)
    field_outline: Optional[AllowedContentFieldOutline] = Field(default=None)
    field_region: Optional[AllowedContentFieldRegion] = Field(default=None)
    regions: None = Field(default=None)
    pinchout: None = Field(default=None)
    subcrop: None = Field(default=None)
    fault_lines: None = Field(default=None)
    velocity: None = Field(default=None)
    volumes: None = Field(default=None)
    khproduct: None = Field(default=None)
    timeseries: None = Field(default=None)
    wellpicks: None = Field(default=None)
    parameters: None = Field(default=None)
    rft: None = Field(default=None)
    pvt: None = Field(default=None)
    relperm: None = Field(default=None)
    lift_curves: None = Field(default=None)
    transmissibilities: None = Field(default=None)

    @staticmethod
    def requires_additional_input(field: str) -> bool:
        # Ideally 'property' and 'seismic' should have been part of the below
        # filds that requires additional input, but due to backwards compatibility
        # they have to be excluted (for now).
        if field == "property":
            property_warn()
        if field == "seismic":
            seismic_warn()
        return field in (
            # "property",
            # "seismic",
            "fluid_contact",
            "field_outline",
            "field_region",
        )

    @model_validator(mode="after")
    def _future_warning_property_seismic(self) -> AllowedContent:
        if isinstance(self.property, str):
            property_warn()
        if isinstance(self.seismic, str):
            seismic_warn()
        return self


class JsonSchemaMetadata(BaseModel, populate_by_name=True):
    schema_: AnyHttpUrl = Field(
        alias="$schema",
        default=TypeAdapter(AnyHttpUrl).validate_python(SCHEMA),
    )
    version: str = Field(default=VERSION)
    source: str = Field(default=SOURCE)


class CaseMetadata(BaseModel):
    name: str
    uuid: str
    user: User


class FMUModel(BaseModel):
    model: GlobalConfigurationModel
    case: CaseMetadata


class CaseSchema(JsonSchemaMetadata):
    class_: Literal["case"] = Field(alias="class", default="case")
    masterdata: Masterdata
    access: Access
    fmu: FMUModel
    description: Optional[List[str]]
    tracklog: List[TracklogEvent]
