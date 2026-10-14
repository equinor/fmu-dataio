"""Test extraction of simulated responses from Ert storage."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pyarrow as pa
import pytest

from fmu.dataio._workflows.case._observations import ObservationType
from fmu.dataio._workflows.fmu_post_sim._responses import (
    get_available_observation_types,
    get_ert_responses_table,
)


def test_get_available_observation_types_discovers_present_types() -> None:
    """Return supported types found in storage and ignore unknown types."""
    ensemble = MagicMock()
    ensemble.experiment.response_info = {"summary": {}, "rft": {}, "unknown": {}}

    assert get_available_observation_types(ensemble) == [
        ObservationType.rft,
        ObservationType.summary,
    ]


def test_get_available_observation_types_empty_when_nothing_stored() -> None:
    """Return an empty list when storage has no response types."""
    ensemble = MagicMock()
    ensemble.experiment.response_info = {}

    assert get_available_observation_types(ensemble) == []


@pytest.mark.parametrize("response_type", list(ObservationType))
def test_get_ert_responses_table(response_type: ObservationType) -> None:
    """Load completed realizations and return their responses as an Arrow table.

    Dry run: realizations 0 and 2 have values 1.0 and 2.0. The helper loads
    those rows, renames ``values`` to ``response_value``, and returns both rows.
    This test runs once for each supported response type.
    """
    ensemble = MagicMock()
    ensemble.experiment.response_info = {response_type.value: {}}
    ensemble.get_realization_list_with_responses.return_value = [0, 2]
    ensemble.load_responses.return_value = pl.DataFrame(
        {
            "realization": [0, 2],
            "response_key": ["key", "key"],
            "values": [1.0, 2.0],
        }
    )

    table = get_ert_responses_table(ensemble, response_type)

    ensemble.load_responses.assert_called_once_with(response_type.value, (0, 2))
    assert table is not None
    assert table.to_pydict() == {
        "realization": [0, 2],
        "response_key": ["key", "key"],
        "response_value": [1.0, 2.0],
    }
    assert table.schema.field("response_key").type == pa.string()


def test_missing_response_type_is_not_loaded() -> None:
    """Return None without reading storage when the requested type is absent."""
    ensemble = MagicMock()
    ensemble.experiment.response_info = {"summary": {}}

    assert get_ert_responses_table(ensemble, ObservationType.rft) is None
    ensemble.load_responses.assert_not_called()


def test_no_successful_realizations_is_not_loaded() -> None:
    """Return None without reading storage when no realization has responses."""
    ensemble = MagicMock()
    ensemble.experiment.response_info = {"summary": {}}
    ensemble.get_realization_list_with_responses.return_value = []

    assert get_ert_responses_table(ensemble, ObservationType.summary) is None
    ensemble.load_responses.assert_not_called()


def test_empty_responses_returns_none() -> None:
    """Return None when storage returns an empty response table."""
    ensemble = MagicMock()
    ensemble.experiment.response_info = {"rft": {}}
    ensemble.get_realization_list_with_responses.return_value = [0]
    ensemble.load_responses.return_value = pl.DataFrame()

    assert get_ert_responses_table(ensemble, ObservationType.rft) is None


def test_storage_errors_propagate() -> None:
    """Let storage read errors reach the caller instead of hiding them."""
    ensemble = MagicMock()
    ensemble.experiment.response_info = {"rft": {}}
    ensemble.get_realization_list_with_responses.return_value = [0]
    ensemble.load_responses.side_effect = RuntimeError("Cannot read response data")

    with pytest.raises(RuntimeError, match="Cannot read response data"):
        get_ert_responses_table(ensemble, ObservationType.rft)
