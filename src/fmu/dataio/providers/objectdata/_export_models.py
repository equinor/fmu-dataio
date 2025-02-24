"""This module contains classes used when data is being exported from the object data
provider.

Mostly these classes are here to maintain backward compatibility while a deprecation
period is ongoing.
"""

from __future__ import annotations

import warnings
from textwrap import dedent
from typing import Final, Literal, Optional, Type

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
            When using content "property", please use the 'content_metadata' argument
            to provide more required information.
            . Example:
                content="property",
                content_metadata={"attribute": "porosity", "is_discrete": False},

            The use of "property" without content_metadata will be disallowed in
            future versions."
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


def content_metadata_factory(content: enums.Content) -> Type[BaseModel]:
    """Return the correct content_metadata model based on provided content."""
    if content == enums.Content.field_outline:
        return data.FieldOutline
    if content == enums.Content.field_region:
        return data.FieldRegion
    if content == enums.Content.fluid_contact:
        return data.FluidContact
    if content == enums.Content.property:
        return AllowedContentProperty
    if content == enums.Content.seismic:
        return AllowedContentSeismic
    raise ValueError(f"No content_metadata model exist for content {str(content)}")


def content_requires_metadata(content: enums.Content) -> bool:
    """Flag if given content requires content_metadata"""
    try:
        content_metadata_factory(content)
        return True
    except ValueError:
        return False
