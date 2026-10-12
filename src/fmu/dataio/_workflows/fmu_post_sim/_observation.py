"""Extract observations and assign IDs for post-simulation exports."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, Final

import polars as pl
import pyarrow as pa

if TYPE_CHECKING:
    from ert.storage import Ensemble as ErtEnsemble


logger: Final = logging.getLogger(__name__)


class ObservationType(StrEnum):
    rft = "rft"
    summary = "summary"
    breakthrough = "breakthrough"
    seismic = "seismic"


def _convert_type_large_string_to_string(pa_type: pa.DataType) -> pa.DataType:
    """Convert Arrow large strings to standard strings for Sumo."""
    return pa.string() if pa.types.is_large_string(pa_type) else pa_type


def _add_observation_ids(obs_df: pl.DataFrame) -> pl.DataFrame:
    """Assign experiment/type-local IDs before filtering or realization joins."""
    return obs_df.with_row_index("observation_id").with_columns(
        pl.col("observation_id").cast(pl.Int64)
    )


def _to_arrow_table(dataframe: pl.DataFrame) -> pa.Table:
    """Convert a result frame to Arrow with standard string columns."""
    table = dataframe.to_arrow()
    schema = pa.schema(
        [
            field.with_type(_convert_type_large_string_to_string(field.type))
            for field in table.schema
        ]
    )
    return table.cast(schema)


def get_ert_observations_table(
    ensemble: ErtEnsemble,
    obs_type: ObservationType,
) -> pa.Table | None:
    """Read observations with IDs shared by the post-simulation response export."""
    obs_df = ensemble.experiment.observations.get(obs_type.value)
    if obs_df is None or obs_df.is_empty():
        logger.info("No %s observations found in ensemble %s", obs_type, ensemble.name)
        return None

    obs_df = _add_observation_ids(obs_df)
    if obs_type == ObservationType.rft and "property" not in obs_df.columns:
        obs_df = obs_df.with_columns(
            pl.col("response_key").str.split(":").list.last().alias("property")
        )
    obs_df = obs_df.drop(
        ["observation_key", "radius", "boundary_id"], strict=False
    ).rename(
        {"observations": "observation_value", "std": "observation_error"},
        strict=False,
    )
    return _to_arrow_table(obs_df)
