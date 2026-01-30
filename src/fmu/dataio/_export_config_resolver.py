"""Resolves user input to ExportData into an ExportConfig."""

from __future__ import annotations

import warnings
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Final, TypeAlias

from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results import global_configuration
from fmu.datamodels.fmu_results.data import (
    FieldOutline,
    FieldRegion,
    FluidContact,
    Property,
)
from fmu.datamodels.fmu_results.enums import (
    Content,
    DomainReference,
    FMUContext,
    VerticalDomain,
)
from fmu.datamodels.fmu_results.fields import Display, Workflow
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._logging import null_logger
from ._runcontext import FMUEnvironment, RunContext
from .providers.objectdata._export_models import AllowedContentSeismic

logger: Final = null_logger(__name__)


if TYPE_CHECKING:
    from ._export_config import ExportConfig
    from .dataio import ExportData

AnyContentMetadata: TypeAlias = (
    AllowedContentSeismic | FieldOutline | FieldRegion | FluidContact | Property
)


def build_from_export_data(
    export_config: type[ExportConfig], dataio: ExportData
) -> ExportConfig:
    """Create an ExportConfig from an ExportData instance.

    This is effectively an adapter to user input.

    Args:
        dataio: The ExportData instance to create config from.

    Returns:
        An immutable ExportConfig with all resolved values.
    """
    from ._export_config import ExportConfig  # Avoid circular import

    vertical_domain, domain_reference = _resolve_vertical_domain(
        dataio.vertical_domain, dataio.domain_reference
    )
    config = _resolve_global_config(dataio.config)
    casepath_input = Path(dataio.casepath) if dataio.casepath else None

    fmu_context, preprocessed = _resolve_fmu_context(
        dataio.fmu_context, dataio.preprocessed
    )

    runcontext = RunContext(
        casepath_proposed=casepath_input,
        fmu_context=fmu_context,
    )

    return ExportConfig(
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
        # Config
        config=config,
        runcontext=runcontext,
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


def _content_metadata_factory(content: Content) -> type[AnyContentMetadata]:
    """Return the correct content_metadata model based on provided content."""
    if content == Content.field_outline:
        return FieldOutline
    if content == Content.field_region:
        return FieldRegion
    if content == Content.fluid_contact:
        return FluidContact
    if content == Content.property:
        return Property
    if content == Content.seismic:
        return AllowedContentSeismic
    raise ValueError(f"No content_metadata model exists for content '{str(content)}'")


def _content_requires_metadata(content: Content) -> bool:
    """Flag if given content requires content_metadata"""
    try:
        _content_metadata_factory(content)
        return True
    except ValueError:
        return False


def _resolve_content_metadata(
    content_metadata: dict | None, content: str | dict | None
) -> AnyContentMetadata | None:
    """
    Get the content metadata if provided by as input, else return None.
    Validation takes place in the objectdata provider.
    """
    content_enum = _resolve_content_enum(content)

    metadata_dict = content_metadata
    if metadata_dict is None and isinstance(content, dict):
        metadata_dict = content.get(str(content_enum))

    if content_enum is None:
        if metadata_dict:
            warnings.warn(
                "Content 'unset' does not require 'content_metadata', ignoring input.",
                UserWarning,
            )
        return None

    if not _content_requires_metadata(content_enum):
        if metadata_dict:
            warnings.warn(
                f"Content '{content_enum.value}' does not require 'content_metadata', "
                "ignoring input.",
                UserWarning,
            )
        return None

    if not metadata_dict:
        if content == Content.property:
            warnings.warn(
                dedent(
                    """
        When using content "property", please use the 'content_metadata' argument
        to provide more required information.

        Example:

            content="property",
            content_metadata={"attribute": "porosity", "is_discrete": False},

        The use of "property" without content_metadata will be disallowed in
        future versions."
        """
                ),
                FutureWarning,
            )
            return None
        raise ValueError(
            f"Content '{content_enum.value}' requires additional input in the form "
            "of 'content_metadata'. Please see the documentation for custom "
            "exports at :"
            "https://fmu-dataio.readthedocs.io/en/latest/custom_exports/usage.html"
        )

    if not isinstance(metadata_dict, dict):
        content_model = _content_metadata_factory(content_enum)
        raise ValueError(
            "'content_metadata' must be a dictionary. Valid keys for content "
            f"'{content_enum.value}': {', '.join(list(content_model.model_fields))}"
        )

    return _content_metadata_factory(content_enum).model_validate(metadata_dict)


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


def _resolve_fmu_context(
    fmu_context_input: str | None,
    preprocessed_input: bool,
) -> tuple[FMUContext | None, bool]:
    """Resolve FMU context from user input and environment.

    Args:
        fmu_context_input: User-provided fmu_context value.
        preprocessed_input: User-provided preprocessed flag.

    Returns:
        Tuple of (resolved_fmu_context, resolved_preprocessed).

    Raises:
        ValueError: If the configuration is invalid.
    """
    env = FMUEnvironment.from_env()
    env_context = env.fmu_context

    _check_removed_fmu_context_options(fmu_context_input)

    fmu_context_input, preprocessed = _handle_fmu_context_deprecations(
        fmu_context_input, preprocessed_input
    )

    effective_context = _determine_effective_fmu_context(fmu_context_input, env_context)
    _validate_fmu_context_combination(effective_context, preprocessed)

    return effective_context, preprocessed


def _check_removed_fmu_context_options(fmu_context_input: str | None) -> None:
    """Check for removed fmu_context options and raise error if found."""
    if fmu_context_input and fmu_context_input.lower() == "case_symlink_realization":
        raise ValueError(
            "fmu_context is set to 'case_symlink_realization', which is no longer a "
            "supported option. Recommended workflow is to export your data as "
            "preprocessed outside of FMU, and re-export the data with "
            "fmu_context='case' using a PRE_SIMULATION ERT workflow. If needed, "
            "forward_models in ERT can be set-up to create symlinks out into the "
            "individual realizations.",
        )


def _handle_fmu_context_deprecations(
    fmu_context_input: str | None,
    preprocessed_input: bool,
) -> tuple[str | None, bool]:
    """Handle deprecated fmu_context input patterns.

    Args:
        fmu_context_input: User-provided fmu_context value.
        preprocessed_input: User-provided preprocessed flag.

    Returns:
        Tuple of (transformed_fmu_context, transformed_preprocessed).
    """
    if fmu_context_input == "preprocessed":
        warnings.warn(
            "Using the 'fmu_context' argument with value 'preprocessed' is "
            "deprecated and will be removed in the future. Use the more explicit "
            "'preprocessed' argument instead: ExportData(preprocessed=True)",
            FutureWarning,
        )
        return None, True

    if fmu_context_input and fmu_context_input.lower() == "iteration":
        return "ensemble", preprocessed_input

    return fmu_context_input, preprocessed_input


def _determine_effective_fmu_context(
    explicit_context: str | None,
    env_context: FMUContext | None,
) -> FMUContext | None:
    """Determine the effective FMU context from explicit input and environment.

    Args:
        explicit_context: User-provided fmu_context (after deprecation handling).
        env_context: FMU context detected from environment variables.

    Returns:
        The effective FMU context to use.
    """
    if explicit_context is None:
        logger.info("fmu_context from environment: %s", env_context)

        if env_context == FMUContext.iteration:
            return FMUContext.ensemble

        return env_context

    if env_context is None:
        logger.warning(
            "Requested fmu_context=%s but not running in FMU environment; "
            "context will be None.",
            explicit_context,
        )
        return None

    explicit_enum = FMUContext(explicit_context.lower())
    if explicit_enum == FMUContext.realization and env_context == FMUContext.case:
        warnings.warn(
            "fmu_context is set to 'realization', but unable to detect ERT "
            "runpath from environment variable. Did you mean fmu_context='case'?",
            UserWarning,
        )

    if explicit_enum == FMUContext.ensemble and env_context == FMUContext.realization:
        warnings.warn(
            "fmu_context is set to 'ensemble', but a realization environment "
            "was detected. Did you mean fmu_context='realization'?",
            UserWarning,
        )

    logger.info("fmu_context set explicitly to %s", explicit_enum)
    return explicit_enum


def _validate_fmu_context_combination(
    context: FMUContext | None,
    preprocessed: bool,
) -> None:
    """Validate that the resolved context/preprocessed combination is allowed.

    Args:
        context: The resolved FMU context.
        preprocessed: The resolved preprocessed flag.

    Raises:
        ValueError: If the combination is invalid.
    """
    if preprocessed and context == FMUContext.realization:
        raise ValueError(
            "Can't export preprocessed data in a fmu_context='realization'. "
            "Preprocessed data should be exported with fmu_context='case' or "
            "outside of FMU entirely, and then re-exported using "
            "ExportPreprocessedData."
        )


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


def _resolve_global_config(
    config: dict[str, Any] | GlobalConfiguration,
) -> GlobalConfiguration | None:
    """Resolve user-provided config to GlobalConfiguration.

    Args:
        config: User-provided config dict or already-validated GlobalConfiguration.

    Returns:
        GlobalConfiguration if valid, None otherwise.
    """
    if isinstance(config, GlobalConfiguration):
        return config

    try:
        return GlobalConfiguration.model_validate(config)
    except global_configuration.ValidationError as e:
        if "masterdata" not in config:
            warnings.warn(
                "The global config file is lacking masterdata definitions, hence "
                "no metadata will be exported. Follow the simple 'Getting started' "
                "steps to do necessary preparations and enable metadata export: "
                "https://fmu-dataio.readthedocs.io/en/latest/getting_started.html ",
                UserWarning,
            )
        else:
            global_configuration.validation_error_warning(e)
        return None
