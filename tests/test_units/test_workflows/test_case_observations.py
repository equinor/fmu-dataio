"""Test that the observations dataframes created from ert are as expected

Running a full integration test with observations is tricky due to ERT config
validations. It requires the presence of a forward_model that can produce a
response i.e. a flow simulation. Hence we test the format of the dataframes
returned from create_observation_dataframes which is used internally in ERT instead.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import get_args
from unittest.mock import MagicMock, patch

import jsonschema
import polars as pl
import pyarrow as pa
import pytest
from ert.config import ErtConfig
from ert.config.ert_config import create_observation_dataframes
from fmu.datamodels import (
    ErtObservationsRftResult,
    ErtObservationsRftSchema,
    ErtObservationsSummaryResult,
    ErtObservationsSummarySchema,
)
from pytest import MonkeyPatch

from fmu.dataio._workflows.case._observations import (
    _convert_type_large_string_to_string,
    _prepare_observations_dataframe,
    get_ert_observations_table,
)
from tests.test_ert_integration.ert_config_utils import (
    add_rft_observations,
    add_summary_observations,
)


@pytest.fixture
def ert_config_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> str:
    monkeypatch.chdir(tmp_path)
    ert_config_path = tmp_path / "snakeoil.ert"

    base_ert_config = dedent(
        """
        NUM_REALIZATIONS 3
        RUNPATH  realization-<IENS>/iter-<ITER>/
        OBS_CONFIG observations
        ECLBASE ECLIPSE_%d
    """
    )

    ert_config_path.write_text(base_ert_config)
    return ert_config_path


def test_ert_observations_as_expected(ert_config_path: str) -> None:
    """Different observation types are returned together as expected from ert"""

    add_rft_observations(ert_config_path)
    add_summary_observations(ert_config_path)

    ert_config = ErtConfig.from_file(ert_config_path)
    observations = create_observation_dataframes(
        ert_config.observation_declarations, MagicMock()
    )

    assert len(observations) == 2
    assert observations.keys() == {"rft", "summary"}


def test_ert_observations_summary_dataframe_as_expected(ert_config_path: Path) -> None:
    """The summary dataframe is as expected from ert"""

    add_summary_observations(ert_config_path)

    ert_config = ErtConfig.from_file(ert_config_path)
    observations = create_observation_dataframes(
        ert_config.observation_declarations, MagicMock()
    )

    assert len(observations) == 1
    assert "summary" in observations

    df = observations["summary"]

    assert isinstance(df, pl.DataFrame)
    assert df.shape == (2, 8)

    assert set(df.columns) == {
        "response_key",
        "observation_key",
        "time",
        "observations",
        "std",
        "east",
        "north",
        "radius",
    }

    assert set(df.schema) == set(
        {
            "response_key": pl.String,
            "observation_key": pl.String,
            "time": pl.Datetime("ms"),
            "observations": pl.Float32,
            "std": pl.Float32,
            "east": pl.Float32,
            "north": pl.Float32,
            "radius": pl.Float32,
        }
    )

    assert df["response_key"].to_list() == ["FOPR", "FGPT"]
    assert df["observation_key"].to_list() == ["FOPR_1", "FGPT_1"]
    assert df["observations"].to_list() == pytest.approx([0.9, 100.5])
    assert df["std"].to_list() == pytest.approx([0.05, 10])
    assert df["time"].to_list() == [datetime(2020, 1, 1), datetime(2025, 1, 1)]
    assert df["east"].is_null().all()
    assert df["north"].is_null().all()
    assert df["radius"].is_null().all()


def test_ert_observations_summary_dataframe_validates_against_achema(
    ert_config_path: Path,
) -> None:
    """The summary dataframe validates against the file schema"""

    add_summary_observations(ert_config_path)

    ert_config = ErtConfig.from_file(ert_config_path)
    observations = create_observation_dataframes(
        ert_config.observation_declarations, MagicMock()
    )

    obs_df = observations["summary"]

    ensemble = MagicMock()
    ensemble.experiment.observations.get.return_value = obs_df

    table = get_ert_observations_table(ensemble, "summary")

    assert table is not None
    assert isinstance(table, pa.Table)

    # ensure 1-1 between table columns and model fields
    root_field = ErtObservationsSummaryResult.model_fields["root"]
    row_model = get_args(root_field.annotation)[0]
    assert set(table.column_names) == set(row_model.model_fields)

    rows = table.to_pylist()
    for row in rows:
        row["time"] = row["time"].isoformat()  # convert datetime objects for validation

    jsonschema.validate(
        instance=rows, schema=ErtObservationsSummarySchema.dump()
    )  # Throws if invalid


def test_ert_observations_rft_dataframe_as_expected(ert_config_path: Path) -> None:
    """The rft dataframe is as expected from ert"""

    add_rft_observations(ert_config_path)

    ert_config = ErtConfig.from_file(ert_config_path)
    observations = create_observation_dataframes(
        ert_config.observation_declarations, MagicMock()
    )

    assert len(observations) == 1
    assert "rft" in observations

    df = observations["rft"]

    assert isinstance(df, pl.DataFrame)
    assert df.shape == (1, 12)

    assert set(df.columns) == {
        "response_key",
        "observation_key",
        "well",
        "date",
        "tvd",
        "md",
        "zone",
        "observations",
        "std",
        "east",
        "north",
        "radius",
    }

    assert set(df.schema) == set(
        {
            "response_key": pl.String,
            "observation_key": pl.String,
            "well": pl.String,
            "date": pl.String,
            "tvd": pl.Float32,
            "md": pl.Float32,
            "zone": pl.String,
            "observations": pl.Float32,
            "std": pl.Float32,
            "east": pl.Float32,
            "north": pl.Float32,
            "radius": pl.Float32,
        }
    )

    assert df["response_key"].to_list() == ["R_A6:2018-01-01:PRESSURE"]
    assert df["observation_key"].to_list() == ["rft_obs"]
    assert df["well"].to_list() == ["R_A6"]
    assert df["date"].to_list() == ["2018-01-01"]
    assert df["tvd"].to_list() == pytest.approx([8400])
    assert df["md"].is_null().all()
    assert df["zone"].to_list() == ["ZONE1"]
    assert df["observations"].to_list() == pytest.approx([3800])
    assert df["std"].to_list() == pytest.approx([30.5])
    assert df["east"].to_list() == pytest.approx([9500])
    assert df["north"].to_list() == pytest.approx([10500.5])
    assert df["radius"].to_list() == pytest.approx([2000])


def test_ert_observations_rft_dataframe_validates_against_schema(
    ert_config_path: Path,
) -> None:
    """The rft dataframe validates against the file schema"""

    add_rft_observations(ert_config_path)

    ert_config = ErtConfig.from_file(ert_config_path)
    observations = create_observation_dataframes(
        ert_config.observation_declarations, MagicMock()
    )

    obs_df = observations["rft"]

    ensemble = MagicMock()
    ensemble.experiment.observations.get.return_value = obs_df

    table = get_ert_observations_table(ensemble, "rft")

    assert table is not None
    assert isinstance(table, pa.Table)

    # ensure 1-1 between table columns and model fields
    root_field = ErtObservationsRftResult.model_fields["root"]
    row_model = get_args(root_field.annotation)[0]
    assert set(table.column_names) == set(row_model.model_fields)

    jsonschema.validate(
        instance=table.to_pylist(), schema=ErtObservationsRftSchema.dump()
    )  # Throws if invalid


def test_get_ert_observations_table_converts_large_string() -> None:
    """large_string fields are converted to string."""
    arrow_table = pa.table(
        {"name": pa.array(["a", "b"], type=pa.large_string())},
    )

    obs_df = MagicMock()
    obs_df.is_empty.return_value = False
    obs_df.to_arrow.return_value = arrow_table

    ensemble = MagicMock()
    ensemble.experiment.observations.get.return_value = obs_df

    with patch(
        "fmu.dataio._workflows.case._observations._prepare_observations_dataframe",
        return_value=obs_df,
    ):
        table = get_ert_observations_table(ensemble, "rft")

    assert table is not None
    assert table.schema.field("name").type == pa.string()


def test_get_ert_observations_table_returns_none_when_missing() -> None:
    """Returns None when observation type is not present."""
    ensemble = MagicMock()
    ensemble.experiment.observations.get.return_value = None

    table = get_ert_observations_table(ensemble, "summary")
    assert table is None


@pytest.mark.parametrize(
    "pa_type, expected",
    [
        (pa.large_string(), pa.string()),
        (pa.string(), pa.string()),
        (pa.utf8(), pa.utf8()),
        (pa.float32(), pa.float32()),
    ],
)
def test_convert_type_large_string_to_string(
    pa_type: pa.DataType, expected: pa.DataType
) -> None:
    """Large string is converted to regular string, and other types are unchanged."""
    assert _convert_type_large_string_to_string(pa_type) == expected


def test_prepare_observations_dataframe_rft_as_expected() -> None:
    """RFT observations are transformed to the expected schema fields."""
    obs_df = pl.DataFrame(
        {
            "response_key": ["R_A6:2018-01-01:PRESSURE"],
            "observation_key": ["rft_obs"],
            "observations": [250.0],
            "std": [10.0],
            "radius": [2000.0],
        }
    )

    df = _prepare_observations_dataframe(obs_df, "rft")

    assert set(df.columns) == {
        "response_key",
        "observation_value",
        "observation_error",
        "property",
    }
    assert df["property"].to_list() == ["PRESSURE"]


def test_prepare_observations_dataframe_summary_does_not_add_property() -> None:
    """Summary observations do not derive a property column from response_key."""
    obs_df = pl.DataFrame(
        {
            "response_key": ["FOPR"],
            "observations": [3000.0],
            "std": [100.0],
            "radius": [2000.0],
        }
    )

    df = _prepare_observations_dataframe(obs_df, "summary")

    assert set(df.columns) == {"response_key", "observation_value", "observation_error"}


def test_prepare_observations_dataframe_keeps_existing_property() -> None:
    """Existing property values are preserved when already present."""
    obs_df = pl.DataFrame(
        {
            "response_key": ["R_A6:2018-01-01:SWAT"],
            "property": ["SWAT"],
            "observations": [3800.0],
            "std": [30.5],
        }
    )

    df = _prepare_observations_dataframe(obs_df, "rft")

    assert df["property"].to_list() == ["SWAT"]
