"""Tests for FMU context resolution."""

from pathlib import Path

import pytest
from fmu.datamodels.fmu_results.enums import FMUContext

from fmu.dataio._fmu_context import (
    FMUContextError,
    FMUContextResolution,
    resolve_fmu_context,
)
from fmu.dataio._runcontext import get_fmu_context_from_environment


def test_no_input_no_env_returns_none_context() -> None:
    """When no input and no environment, context should be None."""
    resolution = resolve_fmu_context(
        fmu_context_input=None,
        preprocessed_input=False,
        env_context=None,
    )

    assert resolution.context is None
    assert resolution.preprocessed is False
    assert resolution.warnings == []


@pytest.mark.parametrize("explicit_context", [str(c.value) for c in FMUContext])
def test_explicit_content_without_env_returns_none(explicit_context: str) -> None:
    """Explicit context is ignored when not in FMU environment."""
    resolution = resolve_fmu_context(
        fmu_context_input=explicit_context,
        preprocessed_input=False,
        env_context=None,
    )
    assert resolution.context is None


@pytest.mark.parametrize(
    ("env_context", "expected"),
    [(c, c if c != FMUContext.iteration else FMUContext.ensemble) for c in FMUContext],
)
def test_no_explicit_uses_env_context(
    env_context: FMUContext,
    expected: FMUContext,
) -> None:
    """When no explicit context, environment context is used."""
    resolution = resolve_fmu_context(
        fmu_context_input=None,
        preprocessed_input=False,
        env_context=env_context,
    )
    assert resolution.context == expected
    assert resolution.warnings == []


@pytest.mark.parametrize(
    ("explicit", "env", "expected"),
    [
        ("realization", FMUContext.realization, FMUContext.realization),
        ("case", FMUContext.case, FMUContext.case),
        ("case", FMUContext.realization, FMUContext.case),
    ],
)
def test_explicit_context_takes_precedence(
    explicit: str,
    env: FMUContext,
    expected: FMUContext,
) -> None:
    """Explicit content overrides environment when both present."""
    resolution = resolve_fmu_context(
        fmu_context_input=explicit,
        preprocessed_input=False,
        env_context=env,
    )
    assert resolution.context == expected


def test_realization_request_in_case_env_emits_warning() -> None:
    """Requesting realization when env is case emits a helpful warning."""
    resolution = resolve_fmu_context(
        fmu_context_input="realization",
        preprocessed_input=False,
        env_context=FMUContext.case,
    )

    assert resolution.context == FMUContext.realization
    assert len(resolution.warnings) == 1

    message, category = resolution.warnings[0]
    assert "Did you mean fmu_context='case'?" in message
    assert category is UserWarning


def test_fmu_context_preprocessed_emits_deprecation_warning() -> None:
    """Using fmu_context="preprocessed" triggers deprecation warning."""
    resolution = resolve_fmu_context(
        fmu_context_input="preprocessed",
        preprocessed_input=False,
        env_context=None,
    )

    assert resolution.preprocessed is True
    assert len(resolution.warnings) == 1

    message, category = resolution.warnings[0]
    assert "deprecated" in message.lower()
    assert "preprocessed=True" in message
    assert category is FutureWarning


def test_fmu_context_preprocessed_with_case_env() -> None:
    """Deprecated fmu_context="preprocessed" works with case environment."""
    resolution = resolve_fmu_context(
        fmu_context_input="preprocessed",
        preprocessed_input=False,
        env_context=FMUContext.case,
    )

    assert resolution.preprocessed is True
    assert resolution.context == FMUContext.case


@pytest.mark.parametrize("iteration_variant", ["iteration", "ITERATION", "Iteration"])
def test_iteration_converted_to_ensemble(iteration_variant: str) -> None:
    """Using "iteration" context is converted to "ensemble"."""
    resolution = resolve_fmu_context(
        fmu_context_input=iteration_variant,
        preprocessed_input=False,
        env_context=FMUContext.ensemble,
    )

    assert resolution.context == FMUContext.ensemble


def test_case_symlink_realization_raises_error() -> None:
    """Using removed "case_symlink_realization" raises FMUContextError."""
    with pytest.raises(FMUContextError, match="no longer a supported"):
        resolve_fmu_context(
            fmu_context_input="case_symlink_realization",
            preprocessed_input=False,
            env_context=None,
        )


def test_preprocessed_with_realization_raises_error() -> None:
    """Cannot export preprocessed data in realization context."""
    with pytest.raises(FMUContextError, match="[Pp]reprocessed.*realization"):
        resolve_fmu_context(
            fmu_context_input="realization",
            preprocessed_input=True,
            env_context=FMUContext.realization,
        )


def test_preprocessed_with_case_is_allowed() -> None:
    """Preprocessed data can be exported in case context."""
    resolution = resolve_fmu_context(
        fmu_context_input="case",
        preprocessed_input=True,
        env_context=FMUContext.case,
    )

    assert resolution.context == FMUContext.case
    assert resolution.preprocessed is True
    assert resolution.warnings == []


def test_preprocessed_outside_fmu_is_allowed() -> None:
    """Preprocessed export outside FMU context is valid."""
    resolution = resolve_fmu_context(
        fmu_context_input=None,
        preprocessed_input=True,
        env_context=None,
    )

    assert resolution.context is None
    assert resolution.preprocessed is True


def test_resolution_is_immutable() -> None:
    """FMUContextResolution should be frozen (immutable)."""
    resolution = FMUContextResolution(
        context=FMUContext.realization,
        preprocessed=False,
    )

    with pytest.raises(AttributeError):
        resolution.context = FMUContext.case  # type: ignore[misc]


def test_resolution_warnings_default_to_empty_list() -> None:
    """Warnings should default to empty list."""
    resolution = FMUContextResolution(context=None, preprocessed=False)
    assert resolution.warnings == []


def test_realization_context_from_env(
    fmurun_w_casemetadata: Path,
) -> None:
    """Test resolution with Ert environment variables."""
    env_context = get_fmu_context_from_environment()
    resolution = resolve_fmu_context(
        fmu_context_input=None,
        preprocessed_input=False,
        env_context=env_context,
    )
    assert resolution.context == FMUContext.realization


def test_case_context_from_env(fmurun_prehook: Path) -> None:
    """Test resolution when only case environment is set."""
    env_context = get_fmu_context_from_environment()
    resolution = resolve_fmu_context(
        fmu_context_input=None,
        preprocessed_input=False,
        env_context=env_context,
    )
    assert resolution.context == FMUContext.case


def test_ensemble_context_when_case_context_from_env(fmurun_prehook: Path) -> None:
    """Test resolution when case environment is set, but ensemble given."""
    env_context = get_fmu_context_from_environment()
    resolution = resolve_fmu_context(
        fmu_context_input="ensemble",
        preprocessed_input=False,
        env_context=env_context,
    )
    assert resolution.context == FMUContext.ensemble
