"""Module for handling deprecated arguments."""

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from ._logging import null_logger
from .types import WarningTuple

logger: Final = null_logger(__name__)


@dataclass(frozen=True)
class DeprecationResolution:
    """Result of resolving deprecated arguments."""

    warnings: list[WarningTuple] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DeprecationError(ValueError):
    """Raised when deprecated argument usage is invalid."""


def resolve_deprecations(
    *,
    # Arguments that have replacements (FutureWarning)
    access_ssdl: dict[str, Any] | None,
    classification: str | None,
    rep_include: bool | None,
    content: str | dict[str, Any] | None,
    vertical_domain: str | dict[str, Any],
    workflow: str | dict[str, Any] | None,
    # Arguments with no effect (UserWarning)
    runpath: str | Path | None,
    grid_model: str | None,
    legacy_time_format: bool,
    createfolder: bool,
    verifyfolder: bool,
    reuse_metadata_rule: str | None,
    realization: int | None,
    aggregation: bool,
    table_include_index: bool,
    verbosity: str,
    allow_forcefolder_absolute: bool,
    include_ertjobs: bool,
    depth_reference: str | None,
    meta_format: str | None,
    # Format options (deprecated, no effect)
    arrow_fformat: str | None,
    cube_fformat: str | None,
    grid_fformat: str | None,
    surface_fformat: str | None,
    dict_fformat: str | None,
) -> DeprecationResolution:
    """Resolve all deprecated arguments and return warnings.

    This function checks all deprecated arguments and generates appropriate warnings.

    Returns:
        DeprecationResolution with warnings to emit.

    Raises:
        DeprecationError: If invalid argument combinations are detected.
    """
    warnings_to_emit: list[WarningTuple] = []
    errors: list[str] = []

    access_warnings, access_error = _check_access_ssdl(
        access_ssdl, classification, rep_include
    )
    warnings_to_emit.extend(access_warnings)
    if access_error:
        errors.append(access_error)

    content_warnings = _check_content_dict(content)
    warnings_to_emit.extend(content_warnings)

    vertical_domain_warnings = _check_vertical_domain_dict(vertical_domain)
    warnings_to_emit.extend(vertical_domain_warnings)

    workflow_warnings = _check_workflow_dict(workflow)
    warnings_to_emit.extend(workflow_warnings)

    no_effect_warnings = _check_no_effect_arguments(
        runpath=runpath,
        grid_model=grid_model,
        legacy_time_format=legacy_time_format,
        createfolder=createfolder,
        verifyfolder=verifyfolder,
        reuse_metadata_rule=reuse_metadata_rule,
        realization=realization,
        aggregation=aggregation,
        table_include_index=table_include_index,
        verbosity=verbosity,
        allow_forcefolder_absolute=allow_forcefolder_absolute,
        include_ertjobs=include_ertjobs,
        depth_reference=depth_reference,
        meta_format=meta_format,
    )
    warnings_to_emit.extend(no_effect_warnings)

    format_warnings = _check_format_options(
        arrow_fformat=arrow_fformat,
        cube_fformat=cube_fformat,
        grid_fformat=grid_fformat,
        surface_fformat=surface_fformat,
        dict_fformat=dict_fformat,
    )
    warnings_to_emit.extend(format_warnings)

    return DeprecationResolution(warnings=warnings_to_emit, errors=errors)


def _check_access_ssdl(
    access_ssdl: dict[str, Any] | None,
    classification: str | None,
    rep_include: bool | None,
) -> tuple[list[WarningTuple], str | None]:
    """Check deprecated access_ssdl argument.

    Returns:
        Tuple of (warnings, error_message). Error message is None if no error.
    """
    if not access_ssdl:
        return [], None

    warnings: list[WarningTuple] = [
        (
            "The 'access_ssdl' argument is deprecated and will be removed in the "
            "future. Use the more explicit 'classification' and 'rep_include' "
            "arguments instead.",
            FutureWarning,
        )
    ]

    error = None
    if classification is not None or rep_include is not None:
        error = (
            "Using the 'classification' and/or 'rep_include' arguments, "
            "in combination with the (legacy) 'access_ssdl' argument "
            "is not supported."
        )

    return warnings, error


def _check_content_dict(content: str | dict[str, Any] | None) -> list[WarningTuple]:
    """Check deprecated content as dict argument."""
    if isinstance(content, dict):
        return [
            (
                "Using the 'content' argument to set both the content and "
                "the content metadata will be deprecated. Set the 'content' "
                "argument to a valid content string, and provide the extra "
                "information through the 'content_metadata' argument instead.",
                FutureWarning,
            )
        ]
    return []


def _check_vertical_domain_dict(
    vertical_domain: str | dict[str, Any],
) -> list[WarningTuple]:
    """Check deprecated vertical_domain as dict usage."""
    if isinstance(vertical_domain, dict):
        return [
            (
                "Using the 'vertical_domain' argument to set both the vertical domain "
                "and the reference will be deprecated. Set the 'vertical_domain' "
                "argument to a string with value either 'time'/'depth', and provide "
                "the domain reference through the 'domain_reference' argument instead.",
                FutureWarning,
            )
        ]
    return []


def _check_workflow_dict(workflow: str | dict[str, Any] | None) -> list[WarningTuple]:
    """Check deprecated workflow as dict argument."""
    if isinstance(workflow, dict):
        return [
            (
                "The 'workflow' argument should be given as a string. "
                "Support for dictionary will be deprecated.",
                FutureWarning,
            )
        ]
    return []


def _check_no_effect_arguments(  # noqa: PLR0912 PLR0913
    *,
    runpath: str | Path | None,
    grid_model: str | None,
    legacy_time_format: bool,
    createfolder: bool,
    verifyfolder: bool,
    reuse_metadata_rule: str | None,
    realization: int | None,
    aggregation: bool,
    table_include_index: bool,
    verbosity: str,
    allow_forcefolder_absolute: bool,
    include_ertjobs: bool,
    depth_reference: str | None,
    meta_format: str | None,
) -> list[WarningTuple]:
    """Check arguments that are deprecated and have no effect."""
    warnings_to_emit: list[WarningTuple] = []

    if runpath:
        warnings_to_emit.append(
            (
                "The 'runpath' key has currently no function. It will be evaluated for "
                "removal in fmu-dataio version 2. Use 'casepath' instead!",
                UserWarning,
            )
        )

    if grid_model:
        warnings_to_emit.append(
            (
                "The 'grid_model' key has currently no function. It will be evaluated "
                "for removal in fmu-dataio version 2.",
                UserWarning,
            )
        )

    if legacy_time_format:
        warnings_to_emit.append(
            (
                "Using the 'legacy_time_format=True' option to create metadata files "
                "with the old format for time is now deprecated. This option has no "
                "longer an effect and will be removed in the near future.",
                UserWarning,
            )
        )

    if not createfolder:
        warnings_to_emit.append(
            (
                "Using the 'createfolder=False' option is now deprecated. "
                "This option has no longer an effect and can safely be removed.",
                UserWarning,
            )
        )

    if not verifyfolder:
        warnings_to_emit.append(
            (
                "Using the 'verifyfolder=False' option to create metadata files "
                "This option has no longer an effect and can safely be removed.",
                UserWarning,
            )
        )

    if reuse_metadata_rule:
        warnings_to_emit.append(
            (
                "The 'reuse_metadata_rule' key is deprecated and has no effect. "
                "Please remove it from the argument list.",
                UserWarning,
            )
        )

    if realization:
        warnings_to_emit.append(
            (
                "The 'realization' key is deprecated and has no effect. "
                "Please remove it from the argument list.",
                UserWarning,
            )
        )

    if aggregation:
        warnings_to_emit.append(
            (
                "The 'aggregation' key is deprecated and has no effect. "
                "Please remove it from the argument list.",
                UserWarning,
            )
        )

    if table_include_index:
        warnings_to_emit.append(
            (
                "The 'table_include_index' option is deprecated and has no effect. "
                "To get the index included in your dataframe, reset the index "
                "before exporting the dataframe with dataio i.e. df = df.reset_index()",
                UserWarning,
            )
        )

    if verbosity != "DEPRECATED":
        warnings_to_emit.append(
            (
                "Using the 'verbosity' key is now deprecated and will have no "
                "effect and will be removed in near future. Please remove it from the "
                "argument list. Set logging level from client script in the standard "
                "manner instead.",
                UserWarning,
            )
        )

    if allow_forcefolder_absolute:
        warnings_to_emit.append(
            (
                "Support for using an absolute path as 'forcefolder' is deprecated. "
                "Please remove it from the argument list.",
                UserWarning,
            )
        )

    if include_ertjobs:
        warnings_to_emit.append(
            (
                "The 'include_ertjobs' option is deprecated and should be removed.",
                UserWarning,
            )
        )

    if depth_reference:
        warnings_to_emit.append(
            (
                "The 'depth_reference' key has no function. Use the 'domain_reference' "
                "key instead to set the reference for the given 'vertical_domain'.",
                UserWarning,
            )
        )

    if meta_format:
        warnings_to_emit.append(
            (
                "The 'meta_format' option is deprecated and should be removed. "
                "Metadata will only be exported in yaml format.",
                UserWarning,
            )
        )

    return warnings_to_emit


def _check_format_options(
    *,
    arrow_fformat: str | None,
    cube_fformat: str | None,
    grid_fformat: str | None,
    surface_fformat: str | None,
    dict_fformat: str | None,
) -> list[WarningTuple]:
    """Check deprecated format options that have no effect."""
    if any((arrow_fformat, cube_fformat, grid_fformat, surface_fformat, dict_fformat)):
        return [
            (
                "The options 'arrow_fformat', 'cube_fformat', 'grid_fformat', "
                "'surface_fformat', and 'dict_fformat' are deprecated. These options "
                "no longer affect the exported file format and can safely be removed.",
                UserWarning,
            )
        ]
    return []


def future_warning_preprocessed() -> None:
    warnings.warn(
        "Using the ExportData class for re-exporting preprocessed data is no "
        "longer supported. Use the dedicated ExportPreprocessedData class "
        "instead. In a deprecation period the ExportPreprocessedData is used "
        "under the hood when a filepath is input to ExportData. "
        "Please update your script, as this will be discontinued in the future.",
        FutureWarning,
    )
