"""
Provides classes for managing and validating global configuration
settings in an application. These classes ensure essential settings
are defined and maintained consistently.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

from fmu.dataio.datastructure.meta import enums, meta
from pydantic import (
    BaseModel,
    Field,
    RootModel,
    ValidationError,
    field_validator,
    model_validator,
)


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


class Model(BaseModel):
    """
    Represents a basic model configuration with a name and revision.
    """

    name: str
    revision: str
    description: Optional[List[str]] = Field(default=None)


class Ssdl(BaseModel):
    """
    Defines the configuration for the SSDL.
    """

    access_level: Optional[enums.AccessLevel] = Field(default=None)
    rep_include: Optional[bool] = Field(
        default=False,
    )


class Asset(BaseModel):
    """
    Represents an asset configuration with a name.
    """

    name: str


class Access(BaseModel, use_enum_values=True):
    """
    Manages access configurations, combining asset and SSDL information.
    """

    asset: Asset
    ssdl: Optional[Ssdl] = Field(default=None)
    classification: Optional[enums.AccessLevel] = Field(default=None)

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
    stratigraphic: bool
    alias: Optional[List[str]] = Field(
        default=None,
    )
    stratigraphic_alias: Optional[List[str]] = Field(
        default=None,
    )

    @field_validator("alias", "stratigraphic_alias", mode="before")
    @classmethod
    def _prune_nones(cls, values: Any) -> Any:
        # For backwards compatibility.
        return None if values is None else [v for v in values if v is not None]


class Stratigraphy(RootModel[Dict[str, StratigraphyElement]]):
    """
    A collection of StratigraphyElement instances, accessible by keys.
    """


class GlobalConfiguration(BaseModel):
    """
    Validates and manages the global configuration for the application.
    """

    access: Access
    masterdata: meta.Masterdata
    model: Model
    stratigraphy: Optional[Stratigraphy] = Field(
        default=None,
    )


def is_valid(obj: object) -> bool:
    """
    Validates an object against the GlobalConfiguration schema.
    """

    try:
        GlobalConfiguration.model_validate(obj)
    except ValidationError as e:
        validation_error_warning(e)
        return False
    return True


def roundtrip(obj: Dict) -> Dict:
    """
    Performs a validation and serialization roundtrip of a given object.

    This function validates the given object with the GlobalConfiguration model,
    then serializes it back to a dictionary, excluding defaults, None values,
    and unset values. This is useful for cleaning and validating configuration data.
    """
    return GlobalConfiguration.model_validate(obj).model_dump(
        mode="json",
        exclude_none=True,
    )
