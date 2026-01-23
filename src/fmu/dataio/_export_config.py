"""
Module for ExportConfig which contains the fully resolved export configuration.

This is the interface used internally which has already processed user input and
undergone input validation and transformations.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal, Self

from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.enums import (
    Content,
    DomainReference,
    FMUContext,
    VerticalDomain,
)
from fmu.datamodels.fmu_results.fields import Display, Workflow
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._fmu_context import resolve_fmu_context
from ._logging import null_logger
from ._runcontext import RunContext, get_fmu_context_from_environment

logger: Final = null_logger(__name__)


if TYPE_CHECKING:
    from .dataio import ExportData


@dataclass(frozen=True)
class ExportConfig:
    """Immutable configuration for export operations.

    All values are resolved and validated at creation time.
    """

    # Content
    content: Content | Literal["unset"]
    content_metadata: dict[str, Any] | None

    # File/path configuration
    name: str
    tagname: str
    forcefolder: str
    subfolder: str
    parent: str
    filename_timedata_reverse: bool
    geometry: str | None

    # Domain configuration
    vertical_domain: VerticalDomain
    domain_reference: DomainReference

    # FMU context
    fmu_context: FMUContext | None
    display: Display
    workflow: Workflow | None
    description: list[str] | None

    # Classification/access
    classification: Classification
    rep_include: bool

    # Table configuration
    table_index: list[str] | None
    table_fformat: str
    polygons_fformat: str
    points_fformat: str

    # Time configuration
    timedata: list[str] | list[list[str]] | None

    # Other
    preprocessed: bool
    is_prediction: bool
    is_observation: bool
    unit: str
    undef_is_zero: bool

    # Casepath
    casepath: Path | None

    # Global configuration
    config: GlobalConfiguration | None
    runcontext: RunContext

    @classmethod
    def from_export_data(cls, dataio: ExportData) -> Self:
        """Create an ExportConfig from an ExportData instance.

        Args:
            dataio: The ExportData instance to create config from.

        Returns:
            An immutable ExportConfig with all resolved values.
        """

        vertical_domain, domain_reference = _resolve_vertical_domain(
            dataio.vertical_domain, dataio.domain_reference
        )
        fmu_context, preprocessed = _resolve_fmu_context(
            dataio.fmu_context, dataio.preprocessed
        )
        config = (
            dataio.config if isinstance(dataio.config, GlobalConfiguration) else None
        )
        casepath = Path(dataio.casepath) if dataio.casepath else None

        return cls(
            # Content
            content=_resolve_content_enum(dataio.content) or "unset",
            content_metadata=_resolve_content_metadata(
                dataio.content_metadata, dataio.content
            ),
            # File/path
            name=dataio.name,
            tagname=dataio.tagname,
            forcefolder=dataio.forcefolder,
            subfolder=dataio.subfolder,
            parent=dataio.parent,
            filename_timedata_reverse=dataio.filename_timedata_reverse,
            geometry=dataio.geometry,
            # Domain
            vertical_domain=vertical_domain,
            domain_reference=domain_reference,
            # FMU context
            fmu_context=fmu_context,
            preprocessed=preprocessed,
            display=Display(name=dataio.display_name),
            workflow=_resolve_workflow(dataio.workflow),
            # Classification/access
            classification=_resolve_classification(
                dataio.classification, dataio.access_ssdl, config
            ),
            rep_include=_resolve_rep_include(
                dataio.rep_include, dataio.access_ssdl, config
            ),
            is_prediction=dataio.is_prediction,
            is_observation=dataio.is_observation,
            # Table
            table_index=dataio.table_index,
            table_fformat=dataio.table_fformat,
            polygons_fformat=dataio.polygons_fformat,
            points_fformat=dataio.points_fformat,
            # Time
            timedata=dataio.timedata,
            # Other
            unit=dataio.unit or "",
            undef_is_zero=dataio.undef_is_zero,
            description=_resolve_description(dataio.description),
            # Casepath
            casepath=casepath,
            # Config
            config=config,
            runcontext=RunContext(casepath, fmu_context),
        )


def _resolve_content_enum(content: str | dict[str, Any] | None) -> Content | None:
    """Resolve the content from raw input.

    Args:
        content: User-provided string, None, or (deprecated) dictionary.

    Returns:
        Resolved enum value or None.
    """
    if content is None:
        logger.debug("content not set from input, returning None'")
        return None

    if isinstance(content, str):
        logger.debug("content is set from string input")
        return Content(content)

    if isinstance(content, dict):
        logger.debug("content is set from dict input")
        return Content(next(iter(content)))

    raise ValueError(
        f"'{content}' is not a valid value for 'content'. Use one "
        f"of: {', '.join([m.value for m in Content])}."
    )


def _resolve_vertical_domain(
    vertical_domain: str | dict[str, Any], domain_reference: str
) -> tuple[VerticalDomain, DomainReference]:
    """Resolve vertical_domain and domain_reference from raw input.

    Handles the deprecated dict format for vertical_domain by extracting the domain and
    reference values.

    Args:
        vertical_domain: User-provided vertical_domain (string or deprecated dict).
        domain_reference: User-provided domain_reference.

    Returns:
        Tuple of (vertical_domain, domain_reference) in resolved enum values.
    """
    if isinstance(vertical_domain, dict):
        vert_domain_str, domain_ref_str = next(iter(vertical_domain.items()))
    else:
        vert_domain_str = vertical_domain
        domain_ref_str = domain_reference

    try:
        vert_domain_enum = VerticalDomain(vert_domain_str)
    except ValueError as e:
        raise ValueError(
            f"'{vert_domain_str}' is not a valid value for 'vertical_domain'. Use one "
            f"of: {', '.join([m.value for m in VerticalDomain])}."
        ) from e

    try:
        domain_ref_enum = DomainReference(domain_ref_str)
    except ValueError as e:
        raise ValueError(
            f"'{domain_ref_str}' is not a valid value for 'domain_reference'. Use one "
            f"of: {', '.join([m.value for m in DomainReference])}."
        ) from e

    return vert_domain_enum, domain_ref_enum


def _resolve_content_metadata(
    content_metadata: dict | None, content: str | dict | None
) -> dict | None:
    """
    Get the content metadata if provided by as input, else return None.
    Validation takes place in the objectdata provider.
    """
    if content_metadata:
        logger.debug("content_metadata is set from content_metadata argument")
        return content_metadata

    if isinstance(content, dict):
        logger.debug("content_metadata is set from content argument")
        content_enum = _resolve_content_enum(content)
        return content[content_enum]

    logger.debug("Found no content_metadata, returning None")
    return None


def _resolve_fmu_context(
    fmu_context_input: str | None, preprocessed_input: bool
) -> tuple[FMUContext | None, bool]:
    """Resolve FMU context from user input and environment.

    Args:
        fmu_context_input: User-provided fmu_context value.
        preprocessed_input: User-provided preprocessed flag.

    Returns:
        Tuple of (resolved_fmu_context, resolved_preprocessed).
    """
    env_context = get_fmu_context_from_environment()
    resolution = resolve_fmu_context(
        fmu_context_input=fmu_context_input,
        preprocessed_input=preprocessed_input,
        env_context=env_context,
    )

    for message, category in resolution.warnings:
        warnings.warn(message, category)

    return resolution.context, resolution.preprocessed


def _resolve_classification(
    classification_input: str | None,
    access_ssdl: dict[str, Any] | None,
    config: GlobalConfiguration | None,
) -> Classification:
    """Resolve classification from multiple sources.

    Resolution order:
    1. from classification argument if present
    2. from access_ssdl argument (deprecated) if present
    3. from access.classification in config

    Args:
        classification_input: User-provided classification value.
        access_ssdl: Deprecated access_ssdl dict.
        config: Global configuration.

    Returns:
        Resolved Classification enum value.
    """
    if classification_input is not None:
        logger.info("Classification is set from input")
        classification = classification_input

    elif access_ssdl and access_ssdl.get("access_level"):
        logger.info("Classification is set from access_ssdl input")
        classification = access_ssdl["access_level"]

    elif isinstance(config, GlobalConfiguration):
        logger.info("Classification is set from config")
        assert config.access.classification
        classification = config.access.classification
    else:
        # Default when config is invalid (no metadata will be produced anyway)
        logger.info("Using default classification 'internal'")
        classification = Classification.internal

    # Handle deprecated 'asset' value
    if Classification(classification) == Classification.asset:
        warnings.warn(
            "The value 'asset' for access.ssdl.access_level is deprecated. "
            "Please use 'restricted' in input arguments or global variables "
            "to silence this warning.",
            FutureWarning,
        )
        return Classification.restricted

    return Classification(classification)


def _resolve_rep_include(
    rep_include_input: bool | None,
    access_ssdl: dict[str, Any] | None,
    config: GlobalConfiguration | None,
) -> bool:
    """Resolve rep_include from multiple sources.

    Resolution order:
    1. from rep_include argument if present
    2. from access_ssdl argument (deprecated) if present
    3. from access.ssdl.rep_include in config
    4. default to False if not found

    Args:
        rep_include_input: User-provided rep_include value.
        access_ssdl: Deprecated access_ssdl dict.
        config: Global configuration.

    Returns:
        Resolved rep_include boolean value.
    """
    if rep_include_input is not None:
        logger.debug("rep_include is set from input")
        return rep_include_input

    if access_ssdl and access_ssdl.get("rep_include"):
        logger.debug("rep_include is set from access_ssdl input")
        return access_ssdl["rep_include"]

    if (
        isinstance(config, GlobalConfiguration)
        and (ssdl := config.access.ssdl)
        and ssdl.rep_include is not None
    ):
        warnings.warn(
            "Setting 'rep_include' from the config is deprecated. Use the "
            "'rep_include' argument instead (default value is False). To silence "
            "this warning remove the 'access.ssdl.rep_include' from the config.",
            FutureWarning,
        )
        logger.debug("rep_include is set from config")
        return ssdl.rep_include

    logger.debug("Using default 'rep_include'=False")
    return False


def _resolve_workflow(workflow: str | dict[str, str] | None) -> Workflow | None:
    if workflow is None:
        return None
    if isinstance(workflow, dict):
        return Workflow.model_validate(workflow)
    return Workflow(reference=workflow)


def _resolve_description(
    description: str | list[str] | None = None,
) -> list[str] | None:
    """Resolve desciption input."""
    if not description:
        return None
    if isinstance(description, str):
        return [description]
    if isinstance(description, list) and all(isinstance(s, str) for s in description):
        return description

    raise ValueError(
        f"'{description}' is not a valid value for 'description'. Use one of: "
        "string or list of strings."
    )
