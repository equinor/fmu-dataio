"""Verify post-simulation exports with real Ert storage and hook execution."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import ert.__main__
import numpy as np
import polars as pl
import pytest
import yaml
from ert.config import RFTConfig, SummaryConfig
from ert.storage import open_storage
from fmu.datamodels import ErtResponsesRftResult, ErtResponsesSummaryResult

from fmu.dataio._workflows.fmu_post_sim import main
from fmu.dataio._workflows.fmu_post_sim._config import PostSimulationConfig
from fmu.dataio._workflows.fmu_post_sim._observation import (
    ObservationType,
    get_ert_observations_table,
)
from fmu.dataio._workflows.fmu_post_sim._responses import get_ert_responses_table

from .ert_config_utils import add_create_case_workflow

if TYPE_CHECKING:
    from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration


@pytest.mark.parametrize("obs_type", [ObservationType.summary, ObservationType.rft])
def test_queue_observations_with_standard_result_metadata(
    obs_type: ObservationType,
    runpath_prehook: Path,
    mock_global_config_validated: GlobalConfiguration,
) -> None:
    ensemble = MagicMock()
    ensemble.experiment.observations = {
        obs_type.value: pl.DataFrame(
            {
                "response_key": ["A:2020-01-01:PRESSURE"],
                "observations": [10.0],
                "std": [1.0],
                **(
                    {"time": [datetime(2020, 1, 1)]}
                    if obs_type == ObservationType.summary
                    else {
                        "well": ["A"],
                        "date": ["2020-01-01"],
                        "zone": ["ZONE1"],
                        "east": [10.0],
                        "north": [20.0],
                        "tvd": [1000.0],
                    }
                ),
            }
        )
    }
    config = PostSimulationConfig(
        casepath=runpath_prehook, global_config=mock_global_config_validated
    )
    uploader = MagicMock()

    main._queue_ert_observations(ensemble, "iter-0", config, uploader, obs_type)

    uploader.queue_table.assert_called_once()
    table, metadata = uploader.queue_table.call_args.args
    assert table["observation_id"].to_pylist() == [0]
    assert metadata["data"]["standard_result"]["name"] == f"observations_{obs_type}"
    assert metadata["data"]["is_observation"] is True
    assert metadata["fmu"]["ensemble"]["name"] == "iter-0"


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
            "realization",
            "response_key",
            "well",
            "date",
            "property",
        ]
    else:
        table = pl.DataFrame(response_data).to_arrow()
        queue_responses = main._queue_ert_obs_summary_responses
        expected_indexes = ["realization", "response_key", "time"]

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
    assert queued_table.equals(table)
    standard_result = metadata["data"]["standard_result"]
    assert standard_result["name"] == f"responses_{response_type.value}"
    assert standard_result["file_schema"]["version"] == "0.2.0"
    assert metadata["data"]["table_index"] == expected_indexes
    assert metadata["data"]["name"] == f"responses_{response_type.value}"


@pytest.mark.parametrize(
    "response_type", [ObservationType.summary, ObservationType.rft]
)
def test_no_observations_produce_no_responses(
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

    assert table is None


@pytest.mark.parametrize(
    "response_type, approximate",
    [
        (ObservationType.summary, False),
        (ObservationType.rft, False),
        (ObservationType.rft, True),
    ],
)
def test_response_ids_reproduce_ert_matching(
    tmp_path: Path, response_type: ObservationType, approximate: bool
) -> None:
    """Compare exported links with ERT's actual assimilation alignment."""
    is_summary = response_type == ObservationType.summary
    key = "FOPR" if is_summary else "A:2020-01-01:PRESSURE"
    base = datetime(2020, 1, 1)
    if is_summary:
        offsets = [-1, -1.001, 1, 0.2, 0.2, 50]
        observations = pl.DataFrame(
            {
                "time": [base + timedelta(seconds=t) for t in offsets],
                "east": [None] * len(offsets),
                "north": [None] * len(offsets),
            },
            schema_overrides={"east": pl.Float32, "north": pl.Float32},
        )
        response_config = SummaryConfig(keys=[key], has_finalized_keys=True)
    else:
        observations = pl.DataFrame(
            {
                "well": ["A"] * 5,
                "date": ["2020-01-01"] * 5,
                "east": [float(i) for i in range(5)],
                "north": [20.0] * 5,
                "tvd": [1000.0] * 5,
                "md": [None] * 5,
                "zone": ["A", "A", "WRONG", "A", "A"],
            }
        )
        response_config = RFTConfig(
            keys=[key],
            has_finalized_keys=True,
            approximate_missing_values=approximate,
        )
    observations = observations.with_columns(
        pl.lit(key).alias("response_key"),
        pl.Series("observation_key", [f"obs_{i}" for i in range(len(observations))]),
        pl.lit(100.0).alias("observations"),
        pl.lit(1.0).alias("std"),
        pl.lit(None, dtype=pl.Float32).alias("radius"),
    )
    storage_path = tmp_path / "storage"
    with open_storage(storage_path, "w") as storage:
        experiment = storage.create_experiment(
            experiment_config={
                "response_configuration": [response_config.model_dump(mode="json")]
            }
        )
        # Persist synthetic observations in ERT's native storage layout.
        observation_path = experiment.mount_point / "observations"
        observation_path.mkdir()
        observations.write_parquet(observation_path / f"{response_type}.parquet")
        ensemble = experiment.create_ensemble(ensemble_size=3, name="iter-0")
        ensemble_id = ensemble.id
        other_ensemble = experiment.create_ensemble(ensemble_size=3, name="iter-1")
        other_ensemble_id = other_ensemble.id
        for real in (0, 2):
            if is_summary:
                responses = pl.DataFrame(
                    {
                        "response_key": [key] * 4 + ["OTHER"],
                        "time": [base + timedelta(seconds=t) for t in (0, 2, 2, 10, 0)],
                        "values": [10.0 + real, 20.0, 24.0, 90.0, 999.0],
                    }
                )
            else:
                cells = [[real + 1, 1, 1], [real + 1, 2, 1], [9, 9, 9]]
                responses = pl.DataFrame(
                    {
                        "response_key": [key] * 3 + ["OTHER", "DROPPED"],
                        "well": ["A"] * 5,
                        "date": ["2020-01-01"] * 5,
                        "property": ["PRESSURE"] * 5,
                        "depth": [1000.0] * 5,
                        "values": [10.0 + real, 30.0 + real, 90.0, 999.0, float("nan")],
                        "well_connection_cell": [*cells, cells[0], [8, 8, 8]],
                        "cell_center": [
                            [0.0, 20.0, 1000.0],
                            [2.0, 20.0, 1000.0],
                            [9.0, 20.0, 1000.0],
                            [0.0, 20.0, 1000.0],
                            [8.0, 20.0, 1000.0],
                        ],
                        "cell_zones": [["A"]] * 5,
                    },
                    schema_overrides={
                        "well_connection_cell": pl.Array(pl.Int64, 3),
                        "cell_center": pl.Array(pl.Float32, 3),
                    },
                )
                metadata = observations.select("east", "north", "tvd").with_columns(
                    pl.Series(
                        "well_connection_cell",
                        [cells[0], cells[0], cells[1], None, [real + 1, 3, 1]],
                        dtype=pl.Array(pl.Int64, 3),
                    ),
                    pl.Series(
                        "well_connection_cell_center",
                        [
                            [0.0, 20.0, 1000.0],
                            [0.0, 20.0, 1000.0],
                            [2.0, 20.0, 1000.0],
                            None,
                            [1.0, 20.0, 1000.0],
                        ],
                        dtype=pl.Array(pl.Float32, 3),
                    ),
                    pl.Series("actual_zones", [["A"]] * 5),
                )
            ensemble.save_response(response_type.value, responses, real)
            if not is_summary:
                ensemble.save_observation_location_metadata(metadata, real)

    with open_storage(storage_path, "r") as storage:
        ensemble = storage.get_ensemble(ensemble_id)
        observation_table = get_ert_observations_table(ensemble, response_type)
        other_table = get_ert_observations_table(
            storage.get_ensemble(other_ensemble_id), response_type
        )
        assert observation_table is not None
        assert observation_table.equals(other_table)
        assert observation_table["observation_id"].to_pylist() == list(
            range(len(observations))
        )
        table = get_ert_responses_table(ensemble, response_type)
        assert table is not None
        result_model = (
            ErtResponsesSummaryResult if is_summary else ErtResponsesRftResult
        )
        result_model.model_validate(table.to_pylist())
        exported = pl.from_arrow(table)
        assert exported["observation_id"].null_count() == 0
        assert exported["response_value"].null_count() == 0
        assert exported["response_key"].unique().to_list() == [key]
        expected_height = 8 if is_summary else (6 if approximate else 4)
        assert exported.height == expected_height
        assert exported.filter(pl.col("response_value") == 90.0).is_empty()
        if is_summary:
            assert exported.filter(pl.col("observation_id") == 2)[
                "response_value"
            ].to_list() == [
                22.0,
                22.0,
            ]
            assert (
                exported.filter(pl.col("observation_id") == 3)["time"].to_list()
                == [base + timedelta(seconds=0.2)] * 2
            )
        aligned = ensemble.get_observations_and_responses(
            observations["observation_key"], np.array([0, 2])
        )
        for obs_id, observation_key in enumerate(observations["observation_key"]):
            oracle = aligned.filter(pl.col("observation_key") == observation_key)
            assert oracle.height == 1
            for real in (0, 2):
                actual = exported.filter(
                    (pl.col("observation_id") == obs_id)
                    & (pl.col("realization") == real)
                )["response_value"].to_list()
                expected = oracle[str(real)][0]
                assert actual == ([] if expected is None else [pytest.approx(expected)])
        if not is_summary:
            assert exported.filter(pl.col("observation_id") == 0)[
                "well_connection_cell"
            ].to_list() == [[1, 1, 1], [3, 1, 1]]
            approximated = exported.filter(pl.col("observation_id") == 4)
            assert approximated.height == (2 if approximate else 0)


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
