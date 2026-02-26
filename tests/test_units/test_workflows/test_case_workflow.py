from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from fmu.dataio._workflows.case.main import (
    CaseWorkflowConfig,
    _get_ensemble_name,
    _queue_ert_parameters,
)


@pytest.fixture
def mock_ensemble() -> Callable[[int], MagicMock]:
    """Mocks an ert.Ensemble object."""

    def _mock_ensemble(iteration: int = 0) -> MagicMock:
        """Creates the mocked object."""
        ensemble = MagicMock()
        ensemble.iteration = 0
        return ensemble

    return _mock_ensemble


@pytest.fixture
def mock_run_paths() -> Callable[[str], MagicMock]:
    """Mocks and ert.Runpaths object."""

    def _mock_run_paths(runpath: str = "/tmp/realization-0/iter-0") -> MagicMock:
        """Creates the mocked object."""
        run_paths = MagicMock()
        run_paths.get_paths.return_value = [runpath]
        return run_paths

    return _mock_run_paths


@pytest.fixture
def workflow_config(
    fmurun_prehook: Path,
    mock_global_config_validated: GlobalConfiguration,
) -> CaseWorkflowConfig:
    """Create a mock CaseWorkflowConfig."""
    return CaseWorkflowConfig(
        casepath=fmurun_prehook,
        ert_config_path=Path("../../ert/model/"),
        register_on_sumo=True,
        verbosity="WARNING",
        global_config=mock_global_config_validated,
        global_config_path=Path("../../fmuconfig/output/global_variables.yml"),
    )


def test_get_ensemble_name_returns_runpath_leaf_when_inside_casepath(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[str], MagicMock],
) -> None:
    """Runpath that is a subdirectory of casepath uses the dir name."""
    casepath = tmp_path / "scratch/user/snakeoil"
    runpath = casepath / "realization-0/iter-0"

    ensemble = mock_ensemble()
    run_paths = mock_run_paths(str(runpath))

    name = _get_ensemble_name(ensemble, run_paths, casepath)

    assert name == "iter-0"


def test_get_ensemble_name_returns_iter0_fallback_when_runpath_equals_casepath(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[str], MagicMock],
) -> None:
    """Runpath whose parent is the casepath falls back to iter-0."""
    casepath = tmp_path / "scratch/user/snakeoil"
    runpath = casepath / "realization-0"

    ensemble = mock_ensemble()
    run_paths = mock_run_paths(str(runpath))

    name = _get_ensemble_name(ensemble, run_paths, casepath)

    assert name == "iter-0"


def test_get_ensemble_name_pred_run(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[str], MagicMock],
) -> None:
    """A prediction run uses the actual directory name."""
    casepath = tmp_path / "scratch/user/snakeoil"
    runpath = casepath / "realization-0/pred-dg3"

    ensemble = mock_ensemble()
    run_paths = mock_run_paths(str(runpath))

    name = _get_ensemble_name(ensemble, run_paths, casepath)

    assert name == "pred-dg3"


def test_queue_ert_parameters_does_nothing_when_table_is_none(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[], MagicMock],
    workflow_config: CaseWorkflowConfig,
) -> None:
    """When get_ert_parameters_table returns None queue_table must not be called.

    This shouldn't happen (Ert should have parameters), but in theory is possible.
    """
    ensemble = mock_ensemble()
    run_paths = mock_run_paths()
    sumo_uploader = MagicMock()

    with patch(
        "fmu.dataio._workflows.case.main.get_ert_parameters_table",
        return_value=None,
    ):
        _queue_ert_parameters(ensemble, run_paths, workflow_config, sumo_uploader)

    sumo_uploader.queue_table.assert_not_called()


def test_queue_ert_parameters_queue_table_when_present(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[str], MagicMock],
    workflow_config: CaseWorkflowConfig,
) -> None:
    """When a table is returned it should be queued with generated metadata."""

    ensemble = mock_ensemble()
    run_paths = mock_run_paths(str(tmp_path / "realization-0/iter-0"))
    sumo_uploader = MagicMock()

    fake_table = pa.table({"REAL": [0]})
    fake_metadata = {"data": {"content": "parameters"}}

    with (
        patch(
            "fmu.dataio._workflows.case.main.get_ert_parameters_table",
            return_value=fake_table,
        ),
        patch(
            "fmu.dataio._workflows.case.main.generate_metadata",
            return_value=fake_metadata,
        ),
    ):
        _queue_ert_parameters(ensemble, run_paths, workflow_config, sumo_uploader)

    sumo_uploader.queue_table.assert_called_once_with(fake_table, fake_metadata)
