from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from fmu.dataio._workflows.fmu_post_sim._config import PostSimulationConfig
from fmu.dataio._workflows.fmu_post_sim.main import (
    WfFmuPostSimulation,
    _upload_ert_observations_responses,
)


@pytest.fixture
def workflow_config(
    runpath_prehook: Path,
    mock_global_config_validated: GlobalConfiguration,
) -> PostSimulationConfig:
    """Create a mock PostSimulationConfig."""
    return PostSimulationConfig(
        casepath=runpath_prehook,
        global_config=mock_global_config_validated,
    )


@pytest.mark.parametrize("response_type", ["summary", "rft"])
def test_upload_ert_responses_generates_simulated_metadata(
    response_type: str,
    workflow_config: PostSimulationConfig,
) -> None:
    ensemble = MagicMock()
    ensemble.iteration = 2
    ensemble.experiment.response_info = {response_type: {}}
    ensemble.get_realization_list_with_responses.return_value = [0, 2]
    ensemble.load_responses.return_value = pl.DataFrame(
        {
            "realization": [0, 2],
            "response_key": ["key", "key"],
            "well": ["A1", "A2"],
            "date": ["2020-01-01", "2020-01-01"],
            "property": ["PRESSURE", "PRESSURE"],
            "depth": [1500.0, 1600.0],
            "time": [datetime(2020, 1, 1), datetime(2020, 1, 1)],
            "values": [1.0, 2.0],
        }
    )
    run_paths = MagicMock()
    run_paths.get_paths.return_value = [
        str(workflow_config.casepath / "realization-0/iter-2")
    ]
    uploader = MagicMock()

    _upload_ert_observations_responses(
        ensemble,
        run_paths,
        workflow_config,
        uploader,
    )

    table, metadata = uploader.queue_table.call_args.args
    assert table["realization"].to_pylist() == [0, 2]
    assert metadata["data"]["name"] == f"responses_{response_type}"
    assert not metadata["data"]["is_observation"]
    assert metadata["data"]["standard_result"]["name"] == f"responses_{response_type}"
    assert metadata["fmu"]["context"]["stage"] == "ensemble"
    assert metadata["fmu"]["ensemble"]["name"] == "iter-2"
    uploader.queue_table.assert_called_once()
    uploader.upload.assert_called_once()
    ensemble.load_responses.assert_called_once_with(response_type, (0, 2))


def test_post_simulation_uploads_without_arguments(
    workflow_config: PostSimulationConfig,
) -> None:
    ensemble = MagicMock()
    run_paths = MagicMock()
    run_paths.substitutions = {
        "<SUMO_CASEPATH>": str(workflow_config.casepath),
    }
    with (
        patch(
            "fmu.dataio._workflows.fmu_post_sim.main.SumoUploaderInterface"
        ) as uploader,
        patch.object(
            PostSimulationConfig,
            "build_postsim_config",
            return_value=workflow_config,
        ) as build_config,
        patch(
            "fmu.dataio._workflows.fmu_post_sim.main._upload_ert_observations_responses"
        ) as upload,
    ):
        WfFmuPostSimulation().run(ensemble, run_paths)

    build_config.assert_called_once_with(run_paths, workflow_config.casepath)
    uploader.assert_called_once()
    upload.assert_called_once_with(
        ensemble=ensemble,
        run_paths=run_paths,
        workflow_config=workflow_config,
        sumo_uploader=uploader.return_value,
    )


@pytest.mark.parametrize("casepath", [None, "relative/path", "<UNDEFINED>"])
def test_post_simulation_requires_absolute_casepath(casepath: str | None) -> None:
    run_paths = MagicMock()
    run_paths.substitutions = {"<SUMO_CASEPATH>": casepath}
    with (
        patch(
            "fmu.dataio._workflows.fmu_post_sim.main.SumoUploaderInterface"
        ) as uploader,
        pytest.raises(ValueError),
    ):
        WfFmuPostSimulation().run(MagicMock(), run_paths)
    uploader.assert_not_called()


def test_post_simulation_requires_existing_case_metadata(tmp_path: Path) -> None:
    run_paths = MagicMock()
    run_paths.substitutions = {"<SUMO_CASEPATH>": str(tmp_path)}
    with (
        patch(
            "fmu.dataio._workflows.fmu_post_sim.main.SumoUploaderInterface"
        ) as uploader,
        pytest.raises(ValueError, match="Run WF_CREATE_CASE_METADATA"),
    ):
        WfFmuPostSimulation().run(MagicMock(), run_paths)
    uploader.assert_not_called()


def test_no_response_tables_still_calls_upload(
    workflow_config: PostSimulationConfig,
) -> None:
    ensemble = MagicMock()
    ensemble.experiment.response_info = {}
    run_paths = MagicMock()
    run_paths.get_paths.return_value = ["/tmp/realization-0/iter-0"]
    uploader = MagicMock()

    _upload_ert_observations_responses(
        ensemble,
        run_paths,
        workflow_config,
        uploader,
    )

    ensemble.load_responses.assert_not_called()
    uploader.queue_table.assert_not_called()
    # Sumo's uploader handles an empty batch; we always call upload.
    uploader.upload.assert_called_once()
