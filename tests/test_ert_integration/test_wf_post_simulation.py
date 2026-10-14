"""Verify post-simulation exports with real Ert storage and hook execution."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import ert.__main__
import polars as pl
import pytest
import yaml
from ert.config import RFTConfig, SummaryConfig
from ert.storage import open_storage

from fmu.dataio._workflows.case._observations import ObservationType
from fmu.dataio._workflows.fmu_post_sim import main
from fmu.dataio._workflows.fmu_post_sim._config import PostSimulationConfig
from fmu.dataio._workflows.fmu_post_sim._responses import get_ert_responses_table

from .ert_config_utils import add_create_case_workflow

if TYPE_CHECKING:
    from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration


@pytest.mark.parametrize(
    "response_type", [ObservationType.summary, ObservationType.rft]
)
def test_queue_responses_with_standard_result_metadata(
    response_type: ObservationType,
    runpath_prehook: Path,
    mock_global_config_validated: GlobalConfiguration,
) -> None:
    response_data = {
        "response_key": ["FOPR"],
        "time": [datetime(2020, 1, 1)],
        "realization": [0],
        "response_value": [250.0],
    }
    if response_type == ObservationType.rft:
        table = (
            pl.DataFrame(response_data)
            .with_columns(
                pl.lit("R_A6:2020-01-01:PRESSURE").alias("response_key"),
                pl.lit("PRESSURE").alias("property"),
                pl.lit("R_A6").alias("well"),
                pl.lit("2020-01-01").alias("date"),
                pl.lit(1500.0).alias("depth"),
            )
            .to_arrow()
        )
        queue_responses = main._queue_ert_responses_rft
        expected_indexes = [
            "response_key",
            "property",
            "well",
            "date",
            "depth",
            "realization",
        ]
    else:
        table = pl.DataFrame(response_data).to_arrow()
        queue_responses = main._queue_ert_obs_summary_responses
        expected_indexes = ["response_key", "time", "realization"]

    config = PostSimulationConfig(
        casepath=runpath_prehook, global_config=mock_global_config_validated
    )
    uploader = MagicMock()
    ensemble = MagicMock()

    with patch.object(main, "get_ert_responses_table", return_value=table) as get_table:
        queue_responses(ensemble, "iter-0", config, uploader)

    get_table.assert_called_once_with(ensemble, response_type)
    uploader.queue_table.assert_called_once()
    queued_table, metadata = uploader.queue_table.call_args.args
    assert queued_table is table
    assert metadata["data"]["standard_result"] == {
        "name": f"responses_{response_type.value}"
    }
    assert metadata["data"]["table_index"] == expected_indexes
    assert metadata["data"]["name"] == f"responses_{response_type.value}"


@pytest.mark.parametrize(
    "response_type", [ObservationType.summary, ObservationType.rft]
)
def test_responses_from_read_only_storage(
    tmp_path: Path,
    response_type: ObservationType,
) -> None:
    is_summary = response_type == ObservationType.summary
    response_key = "FOPR" if is_summary else "R_A6:PRESSURE"
    config_class = SummaryConfig if is_summary else RFTConfig
    response_config = config_class(keys=[response_key], has_finalized_keys=True)
    response_data = {
        "response_key": [response_key],
        "values": [250.0],
        "time": [datetime(2020, 1, 1)],
    }
    with open_storage(tmp_path / "storage", "w") as storage:
        experiment = storage.create_experiment(
            experiment_config={
                "response_configuration": [response_config.model_dump(mode="json")]
            }
        )
        ensemble = experiment.create_ensemble(ensemble_size=3, name="iter-0")
        ensemble_id = ensemble.id
        for realization in (0, 2):
            ensemble.save_response(
                response_type.value, pl.DataFrame(response_data), realization
            )
        experiment.create_ensemble(ensemble_size=3, name="historical")

    with open_storage(tmp_path / "storage", "r") as storage:
        ensemble = storage.get_ensemble(ensemble_id)
        table = get_ert_responses_table(ensemble, response_type)

    assert table is not None
    assert table["realization"].to_pylist() == [0, 2]
    assert table["response_value"].to_pylist() == [250.0, 250.0]
    assert table["response_key"].to_pylist() == [response_key, response_key]


def test_ert_runs_post_simulation_hook(
    fmu_snakeoil_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(model_path)
    monkeypatch.setenv("SUMO_ENV", "dev")
    config_path = model_path / "snakeoil.ert"
    add_create_case_workflow(config_path)
    with config_path.open("a", encoding="utf-8") as config:
        config.write(
            "HOOK_WORKFLOW_JOB post_simulation WF_FMU_POST_SIMULATION POST_SIMULATION\n"
        )

    uploader = MagicMock()
    with (
        patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]),
        patch.object(main, "SumoUploaderInterface", return_value=uploader) as factory,
        patch.object(
            main,
            "_upload_ert_observations_responses",
            wraps=main._upload_ert_observations_responses,
        ) as upload,
    ):
        ert.__main__.main()

    upload.assert_called_once()
    call = upload.call_args.kwargs
    assert call["ensemble"].iteration == 0
    casepath = call["workflow_config"].casepath
    assert casepath == fmu_snakeoil_project / "scratch/user/snakeoil"
    assert call["sumo_uploader"] is uploader
    factory.assert_called_once()
    assert factory.call_args.kwargs["env"] == "dev"
    with (casepath / "share/metadata/fmu_case.yml").open(encoding="utf-8") as metadata:
        case_metadata = yaml.safe_load(metadata)
    assert factory.call_args.kwargs["case_uuid"] == case_metadata["fmu"]["case"]["uuid"]
    # Snakeoil has no responses to stage, but the uploader is always called.
    uploader.upload.assert_called_once()
