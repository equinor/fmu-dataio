"""Tests for FMU context resolution."""

from pathlib import Path

import pytest
from fmu.datamodels.fmu_results.enums import FMUContext

from fmu.dataio._export_config_resolver import (
    _check_removed_fmu_context_options,
    _determine_effective_fmu_context,
    _handle_fmu_context_deprecations,
    _resolve_fmu_context,
    _validate_fmu_context_combination,
)
from fmu.dataio._runcontext import FMUEnvironment


def test_no_input_no_env_returns_none_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no input and no environment, context should be None."""
    for var in ["_ERT_EXPERIMENT_ID", "_ERT_RUNPATH", "_ERT_REALIZATION_NUMBER"]:
        monkeypatch.delenv(var, raising=False)

    context, preprocessed = _resolve_fmu_context(
        fmu_context_input=None,
        preprocessed_input=False,
    )

    assert context is None
    assert preprocessed is False


@pytest.mark.parametrize("explicit_context", [str(c.value) for c in FMUContext])
def test_explicit_context_without_env_returns_none(explicit_context: str) -> None:
    """Explicit context is ignored when not in FMU environment."""
    context = _determine_effective_fmu_context(
        explicit_context=explicit_context,
        env_context=None,
    )
    assert context is None


@pytest.mark.parametrize(
    ("env_context", "expected"),
    [(c, c if c != FMUContext.iteration else FMUContext.ensemble) for c in FMUContext],
)
def test_no_explicit_uses_env_context(
    env_context: FMUContext,
    expected: FMUContext,
) -> None:
    """When no explicit context, environment context is used."""
    context = _determine_effective_fmu_context(
        explicit_context=None,
        env_context=env_context,
    )
    assert context == expected


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
    """Explicit context overrides environment when both present."""
    context = _determine_effective_fmu_context(
        explicit_context=explicit,
        env_context=env,
    )
    assert context == expected


def test_realization_request_in_case_env_emits_warning() -> None:
    """Requesting realization when env is case emits a helpful warning."""
    with pytest.warns(UserWarning, match="Did you mean fmu_context='case'"):
        context = _determine_effective_fmu_context(
            explicit_context="realization",
            env_context=FMUContext.case,
        )

    assert context == FMUContext.realization


def test_ensemble_request_in_realization_env_emits_warning() -> None:
    """Requesting ensemble when env is realization emits a helpful warning."""
    with pytest.warns(UserWarning, match="Did you mean fmu_context='realization'"):
        context = _determine_effective_fmu_context(
            explicit_context="ensemble",
            env_context=FMUContext.realization,
        )

    assert context == FMUContext.ensemble


def test_fmu_context_preprocessed_emits_deprecation_warning() -> None:
    """Using fmu_context="preprocessed" triggers deprecation warning."""
    with pytest.warns(FutureWarning, match="deprecated"):
        fmu_context, preprocessed = _handle_fmu_context_deprecations(
            fmu_context_input="preprocessed",
            preprocessed_input=False,
        )

    assert preprocessed is True
    assert fmu_context is None


@pytest.mark.parametrize("iteration_variant", ["iteration", "ITERATION", "Iteration"])
def test_iteration_converted_to_ensemble(iteration_variant: str) -> None:
    """Using "iteration" context is converted to "ensemble"."""
    fmu_context, preprocessed = _handle_fmu_context_deprecations(
        fmu_context_input=iteration_variant,
        preprocessed_input=False,
    )

    assert fmu_context == "ensemble"


def test_case_symlink_realization_raises_error() -> None:
    """Using removed "case_symlink_realization" raises ValueError."""
    with pytest.raises(ValueError, match="no longer a supported"):
        _check_removed_fmu_context_options(
            fmu_context_input="case_symlink_realization",
        )


def test_preprocessed_with_realization_raises_error() -> None:
    """Cannot export preprocessed data in realization context."""
    with pytest.raises(ValueError, match="[Pp]reprocessed.*realization"):
        _validate_fmu_context_combination(
            context=FMUContext.realization,
            preprocessed=True,
        )


def test_preprocessed_with_case_is_allowed() -> None:
    """Preprocessed data can be exported in case context."""
    # Doesn't raise
    _validate_fmu_context_combination(
        context=FMUContext.case,
        preprocessed=True,
    )


def test_preprocessed_outside_fmu_is_allowed() -> None:
    """Preprocessed export outside FMU context is valid."""
    # Doesn't raise
    _validate_fmu_context_combination(
        context=None,
        preprocessed=True,
    )


def test_realization_context_from_env(
    fmurun_w_casemetadata: Path,
) -> None:
    """Test resolution with Ert environment variables."""
    env = FMUEnvironment.from_env()
    context = _determine_effective_fmu_context(
        explicit_context=None,
        env_context=env.fmu_context,
    )
    assert context == FMUContext.realization


def test_case_context_from_env(fmurun_prehook: Path) -> None:
    """Test resolution when only case environment is set."""
    env = FMUEnvironment.from_env()
    context = _determine_effective_fmu_context(
        explicit_context=None,
        env_context=env.fmu_context,
    )
    assert context == FMUContext.case


def test_ensemble_context_when_case_context_from_env(fmurun_prehook: Path) -> None:
    """Test resolution when case environment is set, but ensemble given."""
    env = FMUEnvironment.from_env()
    context = _determine_effective_fmu_context(
        explicit_context="ensemble",
        env_context=env.fmu_context,
    )
    assert context == FMUContext.ensemble


def test_resolve_fmu_context_integration_no_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_resolve_fmu_context outside FMU."""
    for var in ["_ERT_EXPERIMENT_ID", "_ERT_RUNPATH", "_ERT_REALIZATION_NUMBER"]:
        monkeypatch.delenv(var, raising=False)

    context, preprocessed = _resolve_fmu_context(
        fmu_context_input=None,
        preprocessed_input=False,
    )
    assert preprocessed is False


def test_resolve_fmu_context_integration_with_preprocessed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_resolve_fmu_context with preprocessed=True."""
    for var in ["_ERT_EXPERIMENT_ID", "_ERT_RUNPATH", "_ERT_REALIZATION_NUMBER"]:
        monkeypatch.delenv(var, raising=False)

    context, preprocessed = _resolve_fmu_context(
        fmu_context_input=None,
        preprocessed_input=True,
    )
    assert preprocessed is True
