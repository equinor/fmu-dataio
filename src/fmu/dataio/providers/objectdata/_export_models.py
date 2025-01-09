"""This module contains classes used when data is being exported from the object data
provider.

Mostly these classes are here to maintain backward compatibility while a deprecation
period is ongoing.
"""

from __future__ import annotations

import warnings
from textwrap import dedent
from typing import Final, Literal, Optional, Union

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results import data, enums

logger: Final = null_logger(__name__)


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


class UnsetData(data.Data):
    content: Literal["unset"]  # type: ignore

    @model_validator(mode="after")
    def _deprecation_warning(self) -> UnsetData:
        valid_contents = [m.value for m in enums.Content]
        warnings.warn(
            "The <content> is not provided which will produce invalid metadata. "
            "In the future 'content' will be required explicitly! "
            f"\n\nValid contents are: {', '.join(valid_contents)} "
            "\n\nThis list can be extended upon request and need.",
            FutureWarning,
        )
        return self
