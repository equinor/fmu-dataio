"""Extract and process Ert observations."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, Final

import polars as pl
import pyarrow as pa

if TYPE_CHECKING:
    from ert.storage import Ensemble as ErtEnsemble


logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


class ObservationType(StrEnum):
    rft = "rft"
    summary = "summary"
    breakthrough = "breakthrough"
    seismic = "seismic"


def _convert_type_large_string_to_string(pa_type: pa.DataType) -> pa.DataType:
    """Ensures some large_string field types are changed to string."""
    if pa.types.is_large_string(pa_type):
        return pa.string()
    return pa_type


def _prepare_observations_dataframe(
    obs_df: pl.DataFrame,
    obs_type: ObservationType,
) -> pl.DataFrame:
    """Modify observations dataframe to comply with the standard result schema.

    Adds the derived ``property`` column, renames fields to schema names,
    and drops columns that are not part of the schema.
    """
    if obs_type == ObservationType.rft and "property" not in obs_df.columns:
        obs_df = obs_df.with_columns(
            pl.col("response_key").str.split(":").list.last().alias("property")
        )

    columns_to_drop = ["observation_key", "radius", "boundary_id"]
    rename_map = {
        "observations": "observation_value",
        "std": "observation_error",
    }

    return obs_df.drop(columns_to_drop, strict=False).rename(rename_map, strict=False)


def get_ert_observations_table(
    ensemble: ErtEnsemble,
    obs_type: ObservationType,
) -> pa.Table | None:
    """Extract observations from ert storage and process it into an arrow table."""
    logger.info(f"Observation type: {obs_type}")
    obs_df = ensemble.experiment.observations.get(obs_type)

    if obs_df is None or obs_df.is_empty():
        logger.warning(f"No {obs_type} observations found in ensemble")
        return None

    obs_df = _prepare_observations_dataframe(obs_df, obs_type)
    arrow_table = obs_df.to_arrow()

    schema = pa.schema(
        [
            f.with_type(_convert_type_large_string_to_string(f.type))
            for f in arrow_table.schema
        ]
    )
    return arrow_table.cast(schema)
