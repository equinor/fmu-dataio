from pathlib import Path

import pytest
from fmu.datamodels.fmu_results.enums import FMUContext
from pytest import MonkeyPatch

from fmu.dataio._definitions import RMSExecutionMode
from fmu.dataio._runcontext import FMUEnvironment, RunContext


@pytest.mark.usefixtures("inside_rms_interactive")
def test_inside_rms_decorator() -> None:
    env = FMUEnvironment.from_env()
    assert env.rms_exec_mode is not None
    assert env.rms_exec_mode == RMSExecutionMode.interactive


def test_get_rms_exec_mode_batch(monkeypatch: MonkeyPatch) -> None:
    """Test the rms execution mode in RMS batch."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "batch")
    env = FMUEnvironment.from_env()
    assert env.rms_exec_mode == RMSExecutionMode.batch


def test_get_rms_exec_mode_interactive(monkeypatch: MonkeyPatch) -> None:
    """Test the rms execution mode in RMS interactive."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "interactive")
    env = FMUEnvironment.from_env()
    assert env.rms_exec_mode == RMSExecutionMode.interactive


def test_get_rms_exec_mode_outside(monkeypatch: MonkeyPatch) -> None:
    """Test that rms execution mode outside of RMS is None."""
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)
    env = FMUEnvironment.from_env()
    assert env.rms_exec_mode is None


def test_get_rms_exec_mode_unknown(monkeypatch: MonkeyPatch) -> None:
    """Test that an unknow rms execution mode fails."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "unknown")
    with pytest.raises(ValueError, match="not a valid"):
        FMUEnvironment.from_env()


def test_runcontext_rms_interactive(monkeypatch: MonkeyPatch) -> None:
    """Test the RunContext in RMS interactive."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "interactive")

    runcontext = RunContext()
    assert runcontext.inside_rms is True
    assert runcontext.inside_fmu is False
    assert runcontext.fmu_context is None
    assert runcontext.rms_context == RMSExecutionMode.interactive

    assert runcontext.runpath is None
    assert runcontext.casepath is None
    assert runcontext.case_metadata is None

    # exportroot should be up two folders from rms/model
    assert runcontext.exportroot == Path.cwd().parent.parent


def test_runcontext_rms_batch_inside_fmu(
    monkeypatch: MonkeyPatch, fmurun_w_casemetadata: Path
) -> None:
    """Test the RunContext inside FMU realization context with RMS in batch."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "batch")

    runcontext = RunContext()
    assert runcontext.inside_rms is True
    assert runcontext.inside_fmu is True
    assert runcontext.fmu_context == FMUContext.realization
    assert runcontext.rms_context == RMSExecutionMode.batch

    assert runcontext.runpath == fmurun_w_casemetadata
    assert runcontext.casepath == fmurun_w_casemetadata.parent.parent
    assert runcontext.case_metadata is not None
    assert runcontext.case_metadata.fmu.case.name == "somecasename"

    # exportroot should be the runpath
    assert runcontext.exportroot == runcontext.runpath


def test_runcontext_outside_rms_inside_fmu(
    monkeypatch: MonkeyPatch, fmurun_w_casemetadata: Path
) -> None:
    """Test the RunContext inside FMU in a realization context outside of RMS."""
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)

    runcontext = RunContext()
    assert runcontext.inside_rms is False
    assert runcontext.inside_fmu is True
    assert runcontext.fmu_context == FMUContext.realization
    assert runcontext.rms_context is None

    assert runcontext.runpath == fmurun_w_casemetadata
    assert runcontext.casepath == fmurun_w_casemetadata.parent.parent
    assert runcontext.case_metadata is not None
    assert runcontext.case_metadata.fmu.case.name == "somecasename"

    # exportroot should be the runpath
    assert runcontext.exportroot == runcontext.runpath


def test_runcontext_inside_fmu_prehook(
    monkeypatch: MonkeyPatch, fmurun_prehook: Path
) -> None:
    """Test the RunContext inside FMU in a case context, outside of RMS."""
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)

    # first test with casepath_proposed
    runcontext = RunContext(casepath_proposed=fmurun_prehook)

    assert runcontext.inside_rms is False
    assert runcontext.inside_fmu is True
    assert runcontext.fmu_context == FMUContext.case
    assert runcontext.rms_context is None

    assert runcontext.runpath is None
    assert runcontext.casepath == fmurun_prehook
    assert runcontext.case_metadata is not None
    assert runcontext.case_metadata.fmu.case.name == "somecasename"

    # exportroot should be the casepath
    assert runcontext.exportroot == runcontext.casepath


def test_runcontext_inside_fmu_prehook_no_casepath(
    monkeypatch: MonkeyPatch, fmurun_prehook: Path
) -> None:
    """
    Test the RunContext inside FMU in a case context, outside of RMS.
    Test without casepath provided which will give warning here, but will raise an
    error later in the FMUProvider(tested elsewhere).
    """
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)

    with pytest.warns(UserWarning, match="Could not detect"):
        runcontext = RunContext(casepath_proposed=None)

    assert runcontext.inside_rms is False
    assert runcontext.inside_fmu is True
    assert runcontext.fmu_context == FMUContext.case
    assert runcontext.rms_context is None

    assert runcontext.runpath is None
    assert runcontext.casepath is None
    assert runcontext.case_metadata is None

    # exportroot should be the casepath
    assert runcontext.exportroot == Path.cwd()


def test_runcontext_inside_fmu_prehook_invalid_casepath(
    monkeypatch: MonkeyPatch, fmurun_prehook: Path
) -> None:
    """
    Test the RunContext inside FMU in a case context, outside of RMS.
    Test with an invalid casepath provided which will give warning here, but will
    raise an error later in the FMUProvider(tested elsewhere).
    """
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)

    with pytest.warns(UserWarning, match="Could not detect"):
        runcontext = RunContext(casepath_proposed=Path("invalid/path/to/case"))

    assert runcontext.inside_rms is False
    assert runcontext.inside_fmu is True
    assert runcontext.fmu_context == FMUContext.case
    assert runcontext.rms_context is None

    assert runcontext.runpath is None
    assert runcontext.casepath is None
    assert runcontext.case_metadata is None

    # exportroot should be the casepath
    assert runcontext.exportroot == Path.cwd()


def test_runcontext_outside(monkeypatch: MonkeyPatch) -> None:
    """Test the RunContext outside RMS and outside FMU."""
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)

    runcontext = RunContext()
    assert runcontext.inside_rms is False
    assert runcontext.inside_fmu is False
    assert runcontext.fmu_context is None
    assert runcontext.rms_context is None

    assert runcontext.runpath is None
    assert runcontext.casepath is None
    assert runcontext.case_metadata is None

    # exportroot should be the current working directory
    assert runcontext.exportroot == Path.cwd()


@pytest.mark.parametrize(
    ("context_override", "export_root"),
    [
        (FMUContext.case, "casepath"),
        (FMUContext.realization, "runpath"),
        (FMUContext.ensemble, "ensemble_path"),
    ],
)
def test_runcontext_explicit_fmu_context_override(
    monkeypatch: MonkeyPatch,
    fmurun_w_casemetadata: Path,
    context_override: FMUContext,
    export_root: str,
) -> None:
    """Explicit fmu_context overrides env context."""
    runcontext = RunContext(fmu_context=context_override)

    assert runcontext.fmu_context == context_override
    # exportroot should follow the override, not the environment
    assert runcontext.exportroot == getattr(runcontext, export_root)


def test_runcontext_ensemble_name_standard(
    monkeypatch: MonkeyPatch, fmurun_w_casemetadata: Path
) -> None:
    """Ensemble name extraction for standard iter-N paths."""
    runcontext = RunContext()

    assert runcontext.paths.ensemble_name == "iter-0"
    assert runcontext.paths.realization_name == "realization-0"
    assert runcontext.ensemble_path == (
        runcontext.casepath / "share" / "ensemble" / "iter-0"
    )


def test_runcontext_ensemble_name_prediction(
    monkeypatch: MonkeyPatch, fmurun_w_casemetadata_pred: Path
) -> None:
    """Ensemble name extraction for prediction runs."""
    runcontext = RunContext()

    assert runcontext.paths.ensemble_name == "pred"
    assert runcontext.paths.realization_name == "realization-0"
    assert runcontext.ensemble_path == (
        runcontext.casepath / "share" / "ensemble" / "pred"
    )


def test_runcontext_ensemble_name_flat_structure(
    monkeypatch: MonkeyPatch, fmurun_no_iter_folder: Path
) -> None:
    """Ensemble name defaults to iter-0 when no ensemble folder exists."""
    runcontext = RunContext()

    assert runcontext.paths.ensemble_name == "iter-0"
    assert runcontext.paths.realization_name == "realization-1"


def test_extract_ensemble_and_realization_name_non_relative() -> None:
    """Non-relative casepath/runpath returns Nones."""
    runcontext = RunContext()
    assert runcontext._extract_ensemble_and_realization_name(
        Path("foo"), Path("bar")
    ) == (None, None)


def test_extract_ensemble_and_realization_name_no_parts() -> None:
    """Non-relative casepath/runpath returns Nones."""
    runcontext = RunContext()
    assert runcontext._extract_ensemble_and_realization_name(
        Path("foo"), Path("foo")
    ) == (None, None)


def test_runcontext_explicit_ensemble_name(
    monkeypatch: MonkeyPatch, fmurun_prehook: Path
) -> None:
    """Explicit ensemble_name sets paths when runpath is unavailable."""
    runcontext = RunContext(
        casepath_proposed=fmurun_prehook,
        ensemble_name="pred-dg3",
    )

    assert runcontext.paths.ensemble_name == "pred-dg3"
    assert (
        runcontext.ensemble_path == fmurun_prehook / "share" / "ensemble" / "pred-dg3"
    )


def test_runcontext_explicit_ensemble_name_overrides_derived(
    monkeypatch: MonkeyPatch, fmurun_w_casemetadata: Path
) -> None:
    """Explicit ensemble_name overrides the name derived from runpath."""
    runcontext = RunContext(ensemble_name="custom-ensemble")

    assert runcontext.paths.ensemble_name == "custom-ensemble"
    assert runcontext.ensemble_path == (
        runcontext.casepath / "share" / "ensemble" / "custom-ensemble"
    )
