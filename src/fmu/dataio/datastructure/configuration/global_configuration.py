"""
Provides classes for managing and validating global configuration
settings in an application. These classes ensure essential settings
are defined and maintained consistently.
"""

from __future__ import annotations

import os
import warnings
from typing import Any, Dict, Final, List, Optional

from fmu.dataio._utils import some_config_from_env
from fmu.dataio.datastructure.meta import enums, meta
from pydantic import (
    BaseModel,
    Field,
    RootModel,
    ValidationError,
    field_validator,
    model_validator,
)

GLOBAL_ENVNAME: Final = "FMU_GLOBAL_CONFIG"
SETTINGS_ENVNAME: Final = (
    "FMU_DATAIO_CONFIG"  # Feature deprecated, still used for user warning.
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


class Ssdl(BaseModel):
    """
    Defines the configuration for the SSDL.
    """

    access_level: enums.AccessLevel = Field(
        default=enums.AccessLevel.internal,
    )
    rep_include: bool = Field(
        default=False,
    )

    @model_validator(mode="after")
    def _migrate_asset_to_restricted(self) -> Ssdl:
        if self.access_level == enums.AccessLevel.asset:
            warnings.warn(
                "The value 'asset' for access.ssdl.access_level is deprecated. "
                "Please use 'restricted' in input arguments or global variables "
                "to silence this warning.",
                FutureWarning,
            )
            self.access_level = enums.AccessLevel.restricted
        return self


class Asset(BaseModel):
    """
    Represents an asset configuration with a name.
    """

    name: str


class Access(BaseModel):
    """
    Manages access configurations, combining asset and SSDL information.
    """

    asset: Asset
    ssdl: Ssdl
    classification: Optional[enums.AccessLevel] = Field(default=None)

    @model_validator(mode="after")
    def _classification_mirrors_accesslevel(self) -> Access:
        # Ideally we want to only copy if the user has NOT
        # set the classification.
        # See: https://github.com/equinor/fmu-dataio/issues/540
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


def parse(input_config: object) -> dict:
    """
    Parses the raw config given as input, and sanitizes it.
    """

    # Trying to move the config parsing here to reduce complexity in dataio.py

    # global config which may be given as env variable
    # will only be used if not explicitly given as input
    if not input_config and GLOBAL_ENVNAME in os.environ:
        input_config = some_config_from_env(GLOBAL_ENVNAME) or {}

    # if config is provided as an ENV variable pointing to a YAML file; will override
    if SETTINGS_ENVNAME in os.environ:
        warnings.warn(
            "Providing input settings through environment variables is deprecated, "
            "use ExportData(**yaml_load(<your_file>)) instead. To "
            "disable this warning, remove the 'FMU_DATAIO_CONFIG' env.",
        )

    # verify that a dict was given
    if not isinstance(input_config, dict):
        # Perhaps not needed? We know that self.config is always a dict?
        # Want to avoid "config has no method '.get' type errors later
        raise ValueError("Unsupported format for config, expected Dictionary.")

    use_config = {}

    # populate the fields we actually use
    for key in ["access", "masterdata", "stratigraphy", "model"]:  # TODO
        if key in input_config:
            use_config[key] = input_config[key]

    # While deprecating the 'ssdl.access_level', if config has
    # both 'ssdl.access_level' AND classification defined, issue warning, and use
    # the classification value further.

    _conf_ssdl_access_level = (
        use_config.get("access", {}).get("ssdl", {}).get("access_level")
    )
    _conf_classification = use_config.get("access", {}).get("classification")

    if _conf_ssdl_access_level and _conf_classification:
        # warning triggers only when both are present, i.e. the user has actively
        # started using access.classification, but has not removed ssdl.access_level
        warnings.warn(
            "The config contains both 'access.ssdl.access_level (deprecated) and "
            "access.classification. The value from access.classification will be "
            "used. Remove 'access.ssdl.access_level' to silence this warning."
        )

        use_config["access"]["ssdl"]["access_level"] = use_config["access"][
            "classification"
        ]

    return use_config


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
