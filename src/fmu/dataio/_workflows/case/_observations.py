"""Extract and process Ert observations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final, Literal

import pyarrow as pa

if TYPE_CHECKING:
    import ert


logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


def _convert_type_large_string_to_string(pa_type: pa.DataType) -> pa.DataType:
    """Ensures some large_string field types are changed to string."""
    if pa.types.is_large_string(pa_type):
        return pa.string()
    return pa_type


def get_ert_observations_table(
    ensemble: ert.Ensemble, obs_type: Literal["rft", "summary"]
) -> pa.Table | None:
    """Extract Ert observations as an arrow table file."""
    logger.info(f"Observation type: {obs_type}")
    obs_df = ensemble.experiment.observations.get(obs_type)

    if obs_df is None:
        logger.warning(f"No {obs_type} observations found in ensemble")
        return None

    arrow_table = obs_df.to_arrow()

    schema = pa.schema(
        [
            f.with_type(_convert_type_large_string_to_string(f.type))
            for f in arrow_table.schema
        ]
    )
    return arrow_table.cast(schema)
