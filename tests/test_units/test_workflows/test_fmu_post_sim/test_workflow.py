from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import polars as pl
import pytest
from ert.config import SummaryConfig
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from fmu.dataio._workflows.fmu_post_sim._config import PostSimulationConfig
from fmu.dataio._workflows.fmu_post_sim._observation import ObservationType
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
@pytest.mark.parametrize("ensemble_directory", [True, False])
def test_upload_ert_responses_generates_simulated_metadata(
    response_type: str,
    ensemble_directory: bool,
    workflow_config: PostSimulationConfig,
) -> None:
    ensemble = MagicMock()
    ensemble.iteration = 2
    ensemble.experiment.response_info = {response_type: {}}
    ensemble.experiment.observations = {}
    ensemble.get_realization_list_with_responses.return_value = [0, 2]
    response_table = pl.DataFrame(
        {
            "realization": [0, 2],
            "response_key": ["key", "key"],
            "well": ["A1", "A2"],
            "date": ["2020-01-01", "2020-01-01"],
            "property": ["PRESSURE", "PRESSURE"],
            "depth": [1500.0, 1600.0],
            "time": [datetime(2020, 1, 1), datetime(2020, 1, 1)],
            "response_value": [1.0, 2.0],
        }
    ).to_arrow()
    run_paths = MagicMock()
    runpath = workflow_config.casepath / "realization-0"
    if ensemble_directory:
        runpath /= "iter-2"
    run_paths.get_paths.return_value = [str(runpath)]
    uploader = MagicMock()

    tables = (
        [response_table, None] if response_type == "summary" else [None, response_table]
    )
    with patch(
        "fmu.dataio._workflows.fmu_post_sim.main.get_ert_responses_table",
        side_effect=tables,
    ) as get_tables:
        _upload_ert_observations_responses(
            ensemble, run_paths, workflow_config, uploader
        )

    assert uploader.queue_table.call_count == 2
    paths = []
    for queued, realization, value in zip(
        uploader.queue_table.call_args_list, (0, 2), (1.0, 2.0), strict=True
    ):
        table, metadata = queued.args
        assert table["realization"].to_pylist() == [realization]
        assert table["response_value"].to_pylist() == [value]
        assert metadata["data"]["name"] == f"responses_{response_type}"
        assert not metadata["data"]["is_observation"]
        assert (
            metadata["data"]["standard_result"]["name"] == f"responses_{response_type}"
        )
        assert metadata["fmu"]["context"]["stage"] == "ensemble"
        assert metadata["fmu"]["ensemble"]["name"] == (
            "iter-2" if ensemble_directory else "iter-0"
        )
        path = metadata["file"]["relative_path"]
        assert f"--realization-{realization}" in path
        paths.append(path)
    assert len(set(paths)) == 2
    uploader.upload.assert_called_once()
    assert get_tables.call_args_list == [
        call(ensemble, ObservationType.summary),
        call(ensemble, ObservationType.rft),
    ]


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


def test_post_simulation_queues_observations_and_linked_responses(
    workflow_config: PostSimulationConfig,
) -> None:
    ensemble = MagicMock()
    ensemble.experiment.response_info = {"summary": {}}
    ensemble.experiment.response_configuration = {
        "summary": SummaryConfig(keys=["FOPR"], has_finalized_keys=True)
    }
    ensemble.experiment.observations = {
        "summary": pl.DataFrame(
            {
                "response_key": ["FOPR"],
                "observation_key": ["FOPR_1"],
                "time": [datetime(2020, 1, 1)],
                "observations": [10.0],
                "std": [1.0],
            }
        )
    }
    ensemble.get_realization_list_with_responses.return_value = [0, 2]
    config = ensemble.experiment.response_configuration["summary"]
    ensemble.get_observations_and_responses.return_value = (
        ensemble.experiment.observations["summary"]
        .with_columns(config.index_column_expr().alias("index"))
        .select("response_key", "observation_key", "index")
        .with_columns(pl.lit(12.0).alias("0"), pl.lit(13.0).alias("2"))
    )
    run_paths = MagicMock()
    run_paths.get_paths.return_value = ["/tmp/realization-0/iter-0"]
    uploader = MagicMock()

    _upload_ert_observations_responses(ensemble, run_paths, workflow_config, uploader)

    observations, responses_0, responses_2 = uploader.queue_table.call_args_list
    assert observations.args[0]["observation_id"].to_pylist() == [0]
    for response, realization, value in (
        (responses_0, 0, 12.0),
        (responses_2, 2, 13.0),
    ):
        assert response.args[0]["observation_id"].to_pylist() == [0]
        assert response.args[0]["realization"].to_pylist() == [realization]
        assert response.args[0]["response_value"].to_pylist() == [value]
    for queued, name, is_observation in (
        (observations, "observations_summary", True),
        (responses_0, "responses_summary", False),
        (responses_2, "responses_summary", False),
    ):
        metadata = queued.args[1]
        assert metadata["data"]["standard_result"]["name"] == name
        assert metadata["data"]["is_observation"] is is_observation
    uploader.upload.assert_called_once()


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
    ensemble.experiment.observations = {}
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
