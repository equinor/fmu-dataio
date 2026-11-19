"""Test observation extraction owned by the post-simulation workflow."""

from datetime import datetime
from unittest.mock import MagicMock

import polars as pl
import pyarrow as pa
import pytest
from fmu.datamodels import ErtObservationsRftResult, ErtObservationsSummaryResult

from fmu.dataio._workflows.fmu_post_sim._observation import (
    ObservationType,
    get_ert_observations_table,
)


@pytest.mark.parametrize(
    "obs_type, property_name",
    [
        (ObservationType.summary, None),
        (ObservationType.rft, None),
        (ObservationType.rft, "SWAT"),
    ],
)
def test_observations_have_ids_without_modifying_storage(
    obs_type: ObservationType, property_name: str | None
) -> None:
    is_summary = obs_type == ObservationType.summary
    data = {
        "response_key": ["FOPR" if is_summary else "A:2020-01-01:PRESSURE"] * 2,
        "observation_key": ["obs_0", "obs_1"],
        "observations": [10.0, 20.0],
        "std": [1.0, 2.0],
        "radius": [None, None],
        "boundary_id": [None, None],
    }
    if is_summary:
        data["time"] = [datetime(2020, 1, 1), datetime(2020, 1, 2)]
    else:
        data.update(
            well=["A", "A"],
            date=["2020-01-01"] * 2,
            east=[10.0, 20.0],
            north=[30.0, 40.0],
            tvd=[1000.0, 1001.0],
        )
        if property_name is not None:
            data["property"] = [property_name] * 2
    native_observations = pl.DataFrame(data)
    ensemble = MagicMock()
    ensemble.experiment.observations = {obs_type.value: native_observations}

    table = get_ert_observations_table(ensemble, obs_type)

    assert table is not None
    assert table["observation_id"].to_pylist() == [0, 1]
    assert table.schema.field("observation_id").type == pa.int64()
    assert table.schema.field("response_key").type == pa.string()
    assert table["observation_value"].to_pylist() == [10.0, 20.0]
    assert table["observation_error"].to_pylist() == [1.0, 2.0]
    assert not {"observation_key", "radius", "boundary_id"} & set(table.column_names)
    assert "observation_id" not in native_observations.columns
    assert "observations" in native_observations.columns
    if not is_summary:
        assert table["property"].to_pylist() == [property_name or "PRESSURE"] * 2
    result_model = (
        ErtObservationsSummaryResult if is_summary else ErtObservationsRftResult
    )
    result_model.model_validate(table.to_pylist())


@pytest.mark.parametrize("observations", [None, pl.DataFrame()])
def test_absent_observations_return_none(observations: pl.DataFrame | None) -> None:
    ensemble = MagicMock()
    ensemble.experiment.observations = {"summary": observations}

    assert get_ert_observations_table(ensemble, ObservationType.summary) is None
