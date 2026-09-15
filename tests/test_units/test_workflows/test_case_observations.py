"""Test observation conversion helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import polars as pl
import pyarrow as pa
import pytest

from fmu.dataio._workflows.case._observations import (
    _convert_type_large_string_to_string,
    _prepare_observations_dataframe,
    get_ert_observations_table,
)


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


def test_prepare_observations_dataframe_breakthrough_does_not_add_property() -> None:
    """Breakthrough observations do not derive a property column from response_key."""
    obs_df = pl.DataFrame(
        {
            "response_key": ["FOPR"],
            "observations": [3000.0],
            "std": [100.0],
            "radius": [2000.0],
        }
    )

    df = _prepare_observations_dataframe(obs_df, "breakthrough")

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
