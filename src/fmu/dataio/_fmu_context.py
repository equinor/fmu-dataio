"""
Module for resolving and validating FMU context configuration.
"""

from dataclasses import dataclass, field
from typing import Final

from fmu.datamodels.fmu_results.enums import FMUContext

from ._logging import null_logger

logger: Final = null_logger(__name__)


@dataclass(frozen=True)
class FMUContextResolution:
    """Result of resovling FMU context from inputs and environment."""

    context: FMUContext | None
    preprocessed: bool
    warnings: list[tuple[str, type[Warning]]] = field(default_factory=list)


class FMUContextError(ValueError):
    """Raised when FMU context configuration is invalid."""


def resolve_fmu_context(
    fmu_context_input: str | None,
    preprocessed_input: bool,
    env_context: FMUContext | None,
) -> FMUContextResolution:
    """Resolves the effective FMU context from explicit input and environment.

    Returns the resolved context, preprocessed flag, and any warnings to emit.

    Args:
        fmu_context_input: Explicit fmu_context from user (e.g. "realization", "case").
        preprocessed_input: Whether the preprocessed flag was set by user.
        env_context: The FMU context detected from environment variables.

    Returns:
        FMUContextResolution with the resolved context, preprocessed flag, and any
          warnings that should be emitted.

    Raises:
        FMUContextError: If the configuration is invalid (e.g., removed options,
          incompatible combinations, etc.).
    """
    warnings_to_emit: list[tuple[str, type[Warning]]] = []
    preprocessed = preprocessed_input

    _check_removed_options(fmu_context_input)

    fmu_context_input, preprocessed, deprecation_warnings = _handle_deprecations(
        fmu_context_input, preprocessed_input
    )
    warnings_to_emit.extend(deprecation_warnings)

    effective_context, context_warnings = _determine_effective_context(
        fmu_context_input, env_context
    )
    warnings_to_emit.extend(context_warnings)

    _validate_context_combination(effective_context, preprocessed)

    return FMUContextResolution(
        context=effective_context,
        preprocessed=preprocessed,
        warnings=warnings_to_emit,
    )


def _check_removed_options(fmu_context_input: str | None) -> None:
    if fmu_context_input and fmu_context_input.lower() == "case_symlink_realization":
        raise FMUContextError(
            "fmu_context is set to 'case_symlink_realization', which is no longer a "
            "supported option. Recommended workflow is to export your data as "
            "preprocessed ouside of FMU, and re-export the data with "
            "fmu_context='case' using a PRE_SIMULATION ERT workflow. If needed, "
            "forward_models in ERT can be set-up to create symlinks out into the "
            "individual realizations.",
        )


def _handle_deprecations(
    fmu_context_input: str | None,
    preprocessed_input: bool,
) -> tuple[str | None, bool, list[tuple[str, type[Warning]]]]:
    """
    Handle deprecated input patterns.

    Returns: tuple of (fmu_context, preprocessed, warnings).
    """
    warnings_to_emit: list[tuple[str, type[Warning]]] = []

    if fmu_context_input == "preprocessed":
        warnings_to_emit.append(
            (
                "Using the 'fmu_context' argument with value 'preprocessed' is "
                "deprecated and will be removed in the future. Use the more explicit "
                "'preprocessed' argument instead: ExportData(preprocessed=True)",
                FutureWarning,
            )
        )
        return None, True, warnings_to_emit

    if fmu_context_input and fmu_context_input.lower() == "iteration":
        return "ensemble", preprocessed_input, warnings_to_emit

    return fmu_context_input, preprocessed_input, warnings_to_emit


def _determine_effective_context(
    explicit_context: str | None,
    env_context: FMUContext | None,
) -> tuple[FMUContext | None, list[tuple[str, type[Warning]]]]:
    """
    Determine the effective FMU context from explicit input and environment.

    Returns:
        Tuple of (effective_context, warnings)
    """
    warnings_to_emit: list[tuple[str, type[Warning]]] = []

    if explicit_context is None:
        logger.info(f"fmu_context from environment: {env_context}")

        if env_context == FMUContext.iteration:
            return FMUContext.ensemble, warnings_to_emit

        return env_context, warnings_to_emit

    if env_context is None:
        # Explicit context requested, but we're not in an FMU env
        logger.warning(
            f"Requested fmu_context={explicit_context} but not running in FMU "
            "environment; context will be None."
        )
        return None, warnings_to_emit

    explicit_enum = FMUContext(explicit_context.lower())

    if explicit_enum == FMUContext.realization and env_context == FMUContext.case:
        warnings_to_emit.append(
            (
                "fmu_context is set to 'realization', but unable to detect ERT "
                "runpath from environment variable. Did you mean fmu_context='case'?",
                UserWarning,
            )
        )

    if explicit_enum == FMUContext.ensemble and env_context == FMUContext.realization:
        warnings_to_emit.append(
            (
                "fmu_context is set to 'ensemble', but a realization environment "
                "was detected. Did you mean fmu_context='realization'?",
                UserWarning,
            )
        )

    logger.info(f"fmu_context set explicitly to {explicit_enum}")
    return explicit_enum, warnings_to_emit


def _validate_context_combination(
    context: FMUContext | None, preprocessed: bool
) -> None:
    """Validate that the resolved context combination is allowed.

    Raises:
        FMUContextError: If the combination is invalid.
    """
    if preprocessed and context == FMUContext.realization:
        raise FMUContextError(
            "Can't export preprocessed data in a fmu_context='realization'. "
            "Preprocessed data should be exported with fmu_context='case' or "
            "outside of FMU entirely, and then re-exported using "
            "ExportPreprocessedData."
        )
