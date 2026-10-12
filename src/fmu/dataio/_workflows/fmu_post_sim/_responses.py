"""Reshape ERT's observation-aligned responses into standard-result tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import polars as pl

from ._observation import (
    ObservationType,
    _add_observation_ids,
    _to_arrow_table,
)

if TYPE_CHECKING:
    import pyarrow as pa
    from ert.storage import Ensemble as ErtEnsemble


def get_available_observation_types(
    ensemble: ErtEnsemble,
) -> list[ObservationType]:
    """Return the observation types that actually exist in the given ensemble."""
    available_keys = ensemble.experiment.response_info
    return [
        obs
        for obs in (ObservationType.rft, ObservationType.summary)
        if obs.value in available_keys
    ]


def get_ert_responses_table(
    ensemble: ErtEnsemble,
    response_type: ObservationType,
) -> pa.Table | None:
    """Export usable aligned values, leaving all matching and QC to ERT.

    Observation metadata supplies the schema columns and experiment-local IDs.
    Summary times represent observation times, not the original response times.
    """
    if response_type not in (ObservationType.summary, ObservationType.rft):
        raise ValueError(f"Unsupported post-simulation response type: {response_type}")
    if response_type not in ensemble.experiment.response_info:
        return None

    observations = ensemble.experiment.observations.get(response_type.value)
    if observations is None or observations.is_empty():
        return None
    realizations = ensemble.get_realization_list_with_responses()
    if not realizations:
        return None

    aligned = ensemble.get_observations_and_responses(
        observations["observation_key"].unique().to_list(),
        np.asarray(realizations, dtype=int),
    )
    config = ensemble.experiment.response_configuration[response_type.value]
    observations = _add_observation_ids(observations).with_columns(
        config.index_column_expr().alias("index")
    )
    identity = ["response_key", "observation_key", "index"]
    # Preserve separate IDs even when observation identities are repeated.
    occurrence = pl.int_range(pl.len()).over(identity).alias("_occurrence")
    value_columns = [str(real) for real in realizations]
    observations = observations.with_columns(occurrence).join(
        aligned.select(*identity, *value_columns).with_columns(occurrence),
        on=[*identity, "_occurrence"],
        how="left",
        validate="1:1",
        nulls_equal=True,
    )
    dimensions = ["time"]
    if response_type == ObservationType.rft:
        if "property" not in observations.columns:
            observations = observations.with_columns(
                pl.col("response_key").str.split(":").list.last().alias("property")
            )
        dimensions = ["well", "date", "property", "east", "north", "tvd"]
    responses = (
        observations.unpivot(
            on=value_columns,
            index=["observation_id", "response_key", *dimensions],
            variable_name="realization",
            value_name="response_value",
        )
        .with_columns(pl.col("realization").cast(pl.Int64))
        .filter(pl.col("response_value").is_not_null())
    )
    if responses.is_empty():
        return None

    if response_type == ObservationType.rft:
        coordinates = ["east", "north", "tvd"]
        frames = []
        for frame in responses.partition_by("realization", maintain_order=True):
            metadata = ensemble.load_observation_location_metadata(
                frame["realization"][0]
            ).select(*coordinates, "well_connection_cell")
            frames.append(
                frame.join(metadata, on=coordinates, how="left", validate="m:1")
            )
        responses = pl.concat(frames)
        if responses["well_connection_cell"].null_count():
            raise ValueError("ERT returned usable RFT values without connection cells")
        dimensions = ["well", "date", "property", "well_connection_cell"]
    return _to_arrow_table(
        responses.select(
            "observation_id",
            "realization",
            "response_key",
            *dimensions,
            "response_value",
        )
    )
