"""Test reshaping ERT's aligned responses without matching simulation data."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import polars as pl
import pyarrow as pa
import pytest
from ert.config import SummaryConfig

from fmu.dataio._workflows.fmu_post_sim._observation import (
    ObservationType,
    get_ert_observations_table,
)
from fmu.dataio._workflows.fmu_post_sim._responses import (
    get_available_observation_types,
    get_ert_responses_table,
)


@pytest.fixture
def summary_ensemble() -> MagicMock:
    ensemble = MagicMock()
    config = SummaryConfig(keys=["FOPR"], has_finalized_keys=True)
    observations = pl.DataFrame(
        {
            "response_key": ["FOPR"] * 4,
            "observation_key": ["late", "duplicate", "duplicate", "missing"],
            "time": [datetime(2020, 1, 1) + timedelta(days=d) for d in (2, 0, 0, 1)],
            "observations": [20.0, 10.0, 11.0, 15.0],
            "std": [1.0] * 4,
        }
    )
    ensemble.experiment.response_info = {"summary": {}}
    ensemble.experiment.response_configuration = {"summary": config}
    ensemble.experiment.observations = {"summary": observations}
    ensemble.get_realization_list_with_responses.return_value = [0, 2]
    ensemble.get_observations_and_responses.return_value = (
        observations.with_columns(config.index_column_expr().alias("index"))
        .select("response_key", "observation_key", "index")
        .with_columns(
            pl.Series("0", [20.0, 10.0, 10.0, None]),
            pl.Series("2", [22.0, 12.0, 12.0, None]),
        )
        .sort("index")
    )
    return ensemble


def test_get_available_observation_types_discovers_present_types() -> None:
    """Return supported types found in storage and ignore unknown types."""
    ensemble = MagicMock()
    ensemble.experiment.response_info = {
        "summary": {},
        "rft": {},
        "breakthrough": {},
        "unknown": {},
    }

    assert get_available_observation_types(ensemble) == [
        ObservationType.rft,
        ObservationType.summary,
    ]


def test_get_available_observation_types_empty_when_nothing_stored() -> None:
    """Return an empty list when storage has no response types."""
    ensemble = MagicMock()
    ensemble.experiment.response_info = {}

    assert get_available_observation_types(ensemble) == []


def test_ert_aligned_values_keep_observation_ids(summary_ensemble: MagicMock) -> None:
    """Keep row IDs across ERT sorting and duplicate observation identities."""
    table = get_ert_responses_table(summary_ensemble, ObservationType.summary)

    assert table is not None
    actual = pl.from_arrow(table).sort("realization", "observation_id")
    assert actual.select("observation_id", "realization", "response_value").to_dict(
        as_series=False
    ) == {
        "observation_id": [0, 1, 2, 0, 1, 2],
        "realization": [0, 0, 0, 2, 2, 2],
        "response_value": [20.0, 10.0, 10.0, 22.0, 12.0, 12.0],
    }
    assert table.schema.field("response_key").type == pa.string()
    call = summary_ensemble.get_observations_and_responses
    call.assert_called_once()
    keys, realizations = call.call_args.args
    assert set(keys) == {"late", "duplicate", "missing"}
    assert realizations.tolist() == [0, 2]
    summary_ensemble.load_responses.assert_not_called()
    observations = get_ert_observations_table(summary_ensemble, ObservationType.summary)
    assert observations is not None
    assert observations["observation_id"].to_pylist() == [0, 1, 2, 3]
    assert observations["observation_value"].to_pylist() == [20.0, 10.0, 11.0, 15.0]


def test_missing_response_type_is_not_loaded() -> None:
    """Return None without reading storage when the requested type is absent."""
    ensemble = MagicMock()
    ensemble.experiment.response_info = {"summary": {}}

    assert get_ert_responses_table(ensemble, ObservationType.rft) is None
    ensemble.get_observations_and_responses.assert_not_called()


def test_no_successful_realizations_is_not_loaded(summary_ensemble: MagicMock) -> None:
    """Return None without reading storage when no realization has responses."""
    summary_ensemble.get_realization_list_with_responses.return_value = []

    assert get_ert_responses_table(summary_ensemble, ObservationType.summary) is None
    summary_ensemble.get_observations_and_responses.assert_not_called()


@pytest.mark.parametrize("observations", [None, pl.DataFrame()])
def test_no_observations_is_not_loaded(
    summary_ensemble: MagicMock, observations: pl.DataFrame | None
) -> None:
    summary_ensemble.experiment.observations = {"summary": observations}

    assert get_ert_responses_table(summary_ensemble, ObservationType.summary) is None
    summary_ensemble.get_observations_and_responses.assert_not_called()


def test_no_usable_aligned_values_returns_none(summary_ensemble: MagicMock) -> None:
    summary_ensemble.get_observations_and_responses.return_value = (
        summary_ensemble.get_observations_and_responses.return_value.with_columns(
            pl.lit(None, dtype=pl.Float32).alias("0"),
            pl.lit(None, dtype=pl.Float32).alias("2"),
        )
    )

    assert get_ert_responses_table(summary_ensemble, ObservationType.summary) is None


def test_storage_errors_propagate(summary_ensemble: MagicMock) -> None:
    """Let storage read errors reach the caller instead of hiding them."""
    summary_ensemble.get_observations_and_responses.side_effect = RuntimeError(
        "Cannot read response data"
    )

    with pytest.raises(RuntimeError, match="Cannot read response data"):
        get_ert_responses_table(summary_ensemble, ObservationType.summary)
