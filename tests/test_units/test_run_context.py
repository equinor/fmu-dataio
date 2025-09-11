from pathlib import Path

import pytest
from fmu.datamodels.fmu_results.enums import FMUContext

from fmu.dataio._definitions import RMSExecutionMode
from fmu.dataio._runcontext import RunContext, get_rms_exec_mode


@pytest.mark.usefixtures("inside_rms_interactive")
def test_inside_rms_decorator():
    assert get_rms_exec_mode() is not None
    assert get_rms_exec_mode() == RMSExecutionMode.interactive


def test_get_rms_exec_mode_batch(monkeypatch):
    """Test the rms execution mode in RMS batch."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "batch")
    assert get_rms_exec_mode() == RMSExecutionMode.batch


def test_get_rms_exec_mode_interactive(monkeypatch):
    """Test the rms execution mode in RMS interactive."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "interactive")
    assert get_rms_exec_mode() == RMSExecutionMode.interactive


def test_get_rms_exec_mode_outside(monkeypatch):
    """Test that rms execution mode outside of RMS is None."""
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)
    assert get_rms_exec_mode() is None


def test_get_rms_exec_mode_unknown(monkeypatch):
    """Test that an unknow rms execution mode fails."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "unknown")
    with pytest.raises(ValueError, match="not a valid"):
        get_rms_exec_mode()


def test_runcontext_rms_interactive(monkeypatch):
    """Test the RunContext in RMS interactive."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "interactive")

    runcontext = RunContext()
    assert runcontext.inside_rms is True
    assert runcontext.inside_fmu is False
    assert runcontext.fmu_context_from_env is None
    assert runcontext.rms_context == RMSExecutionMode.interactive

    assert runcontext.runpath is None
    assert runcontext.casepath is None
    assert runcontext.case_metadata is None

    # exportroot should be up two folders from rms/model
    assert runcontext.exportroot == Path.cwd().parent.parent


def test_runcontext_rms_batch_inside_fmu(monkeypatch, fmurun_w_casemetadata):
    """Test the RunContext inside FMU realization context with RMS in batch."""
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "batch")

    runcontext = RunContext()
    assert runcontext.inside_rms is True
    assert runcontext.inside_fmu is True
    assert runcontext.fmu_context_from_env == FMUContext.realization
    assert runcontext.rms_context == RMSExecutionMode.batch

    assert runcontext.runpath == fmurun_w_casemetadata
    assert runcontext.casepath == fmurun_w_casemetadata.parent.parent
    assert runcontext.case_metadata.fmu.case.name == "somecasename"

    # exportroot should be the runpath
    assert runcontext.exportroot == runcontext.runpath


def test_runcontext_outside_rms_inside_fmu(monkeypatch, fmurun_w_casemetadata):
    """Test the RunContext inside FMU in a realization context outside of RMS."""
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)

    runcontext = RunContext()
    assert runcontext.inside_rms is False
    assert runcontext.inside_fmu is True
    assert runcontext.fmu_context_from_env == FMUContext.realization
    assert runcontext.rms_context is None

    assert runcontext.runpath == fmurun_w_casemetadata
    assert runcontext.casepath == fmurun_w_casemetadata.parent.parent
    assert runcontext.case_metadata.fmu.case.name == "somecasename"

    # exportroot should be the runpath
    assert runcontext.exportroot == runcontext.runpath


def test_runcontext_inside_fmu_prehook(monkeypatch, fmurun_prehook):
    """Test the RunContext inside FMU in a case context, outside of RMS."""
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)

    # first test with casepath_proposed
    runcontext = RunContext(casepath_proposed=fmurun_prehook)

    assert runcontext.inside_rms is False
    assert runcontext.inside_fmu is True
    assert runcontext.fmu_context_from_env == FMUContext.case
    assert runcontext.rms_context is None

    assert runcontext.runpath is None
    assert runcontext.casepath == fmurun_prehook
    assert runcontext.case_metadata.fmu.case.name == "somecasename"

    # exportroot should be the casepath
    assert runcontext.exportroot == runcontext.casepath


def test_runcontext_inside_fmu_prehook_no_casepath(monkeypatch, fmurun_prehook):
    """
    Test the RunContext inside FMU in a case context, outside of RMS.
    Test without casepath provided which will give warning here, but will raise an
    error later in the FMUProvider(tested elsewhere).
    """
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)

    with pytest.warns(UserWarning, match="Could not auto detect"):
        runcontext = RunContext(casepath_proposed=None)

    assert runcontext.inside_rms is False
    assert runcontext.inside_fmu is True
    assert runcontext.fmu_context_from_env == FMUContext.case
    assert runcontext.rms_context is None

    assert runcontext.runpath is None
    assert runcontext.casepath is None
    assert runcontext.case_metadata is None

    # exportroot should be the casepath
    assert runcontext.exportroot == Path.cwd()


def test_runcontext_inside_fmu_prehook_invalid_casepath(monkeypatch, fmurun_prehook):
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
    assert runcontext.fmu_context_from_env == FMUContext.case
    assert runcontext.rms_context is None

    assert runcontext.runpath is None
    assert runcontext.casepath is None
    assert runcontext.case_metadata is None

    # exportroot should be the casepath
    assert runcontext.exportroot == Path.cwd()


def test_runcontext_outside(monkeypatch):
    """Test the RunContext outside RMS and outside FMU."""
    monkeypatch.delenv("RUNRMS_EXEC_MODE", raising=False)

    runcontext = RunContext()
    assert runcontext.inside_rms is False
    assert runcontext.inside_fmu is False
    assert runcontext.fmu_context_from_env is None
    assert runcontext.rms_context is None

    assert runcontext.runpath is None
    assert runcontext.casepath is None
    assert runcontext.case_metadata is None

    # exportroot should be the current working directory
    assert runcontext.exportroot == Path.cwd()
