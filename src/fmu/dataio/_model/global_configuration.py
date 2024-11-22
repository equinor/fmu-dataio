"""
Provides classes for managing and validating global configuration
settings in an application. These classes ensure essential settings
are defined and maintained consistently.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    Field,
    RootModel,
    ValidationError,
    field_validator,
    model_validator,
)

from . import data, enums, fields


def validation_error_warning(err: ValidationError) -> None:
    """
    Emits a warning when a ValidationError is encountered in global configuration.
    """

    warnings.warn(
        f"""The global configuration has one or more errors that makes it
impossible to create valid metadata. The data will still be exported but no
metadata will be made. You are strongly encouraged to correct your
configuration. Invalid configuration may be disallowed in future versions.

Detailed information:
{str(err)}
""",
        stacklevel=2,
    )


class Ssdl(BaseModel):
    """
    Defines the configuration for the SSDL.
    """

    access_level: Optional[enums.Classification] = Field(default=None)
    rep_include: Optional[bool] = Field(default=None)


class Access(BaseModel, use_enum_values=True):
    """
    Manages access configurations, combining asset and SSDL information.
    """

    asset: fields.Asset
    ssdl: Optional[Ssdl] = Field(default=None)
    classification: Optional[enums.Classification] = Field(default=None)

    @model_validator(mode="after")
    def _validate_classification_ssdl_access_level(self) -> Access:
        if self.classification and self.ssdl and self.ssdl.access_level:
            warnings.warn(
                "The config contains both 'access.ssdl.access_level (deprecated) and "
                "access.classification. The value from access.classification will be "
                "used as the default classification. Remove 'access.ssdl.access_level' "
                "to silence this warning."
            )
        if not self.classification:
            if not (self.ssdl and self.ssdl.access_level):
                raise ValueError(
                    "The config doesn't contain any default security classification. "
                    "Please provide access.classification."
                )
            # classification mirrors ssdl.access_level if not present
            self.classification = self.ssdl.access_level

        return self


class StratigraphyElement(BaseModel):
    """
    Represents a single element in a stratigraphy configuration.
    """

    name: str
    stratigraphic: bool = Field(default=False)
    alias: Optional[List[str]] = Field(default_factory=list)
    stratigraphic_alias: Optional[List[str]] = Field(default=None)
    offset: float = Field(default=0.0, allow_inf_nan=False)
    top: Optional[data.Layer] = Field(default=None)
    base: Optional[data.Layer] = Field(default=None)

    @field_validator("alias", "stratigraphic_alias", mode="before")
    @classmethod
    def _prune_nones_and_adjust_input(cls, values: Any) -> Any:
        # For backwards compatibility, remove after a deprecation period
        if isinstance(values, list) and not all(values):
            warnings.warn(
                "The global config contains an empty list element in one of the "
                "'alias' fields in the 'stratigraphy' section. Please remove the empty "
                "element, and be aware that this will not be supported in the future.",
                FutureWarning,
            )
            return [v for v in values if v is not None]

        if isinstance(values, str):
            warnings.warn(
                "The global config contains string input for one of the 'alias' fields "
                "in the 'stratigraphy' section. Please convert to a list instead as "
                "this will not be supported in the future.",
                FutureWarning,
            )
            return [values]
        return values

    @field_validator("top", "base", mode="before")
    @classmethod
    def _set_name_attribute_if_string_input(
        cls, value: Dict | str | None
    ) -> Dict | None:
        if isinstance(value, str):
            return {"name": value}
        return value


class Stratigraphy(RootModel[Dict[str, StratigraphyElement]]):
    """
    A collection of StratigraphyElement instances, accessible by keys.
    """

    def __iter__(self) -> Any:
        # Using ´Any´ as return type here as mypy is having issues
        # resolving the correct type
        return iter(self.root)

    def __getitem__(self, item: str) -> StratigraphyElement:
        return self.root[item]


class GlobalConfiguration(BaseModel):
    """
    Validates and manages the global configuration for the application.
    """

    access: Access
    masterdata: fields.Masterdata
    model: fields.Model
    stratigraphy: Optional[Stratigraphy] = Field(default=None)
