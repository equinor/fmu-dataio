"""Read simulated responses from Ert storage for the post-simulation workflow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

import pyarrow as pa

from ..case._observations import (
    ObservationType,
    _convert_type_large_string_to_string,
)

if TYPE_CHECKING:
    import polars as pl
    from ert.storage import Ensemble as ErtEnsemble


logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


def _rename_responses_columns(responses: pl.DataFrame) -> pl.DataFrame:
    """Rename columns in the responses dataframe to match the fmu-datamodel schema."""
    return responses.rename(
        {
            "values": "response_value",
        },
        strict=False,
    )


def _prepare_responses_dataframe(responses: pl.DataFrame) -> pl.DataFrame:
    """Rename response columns before exporting to Arrow."""
    return _rename_responses_columns(responses)


def get_available_observation_types(
    ensemble: ErtEnsemble,
) -> list[ObservationType]:
    """Return the observation types that actually exist in the given ensemble."""
    available_keys = ensemble.experiment.response_info
    return [obs for obs in ObservationType if obs.value in available_keys]


def get_ert_responses_table(
    ensemble: ErtEnsemble,
    response_type: ObservationType,
) -> pa.Table | None:
    """Read responses for one observation type from the ensemble's local storage.

    Ert stores each realization's responses as parquet files on disk; the
    ensemble object reads them from there. We do not open a new storage handle.
    """
    # Skip observation types that were never stored for this ensemble.
    if response_type not in ensemble.experiment.response_info:
        return None

    # Only realizations that finished with responses can be read.
    realizations = tuple(ensemble.get_realization_list_with_responses())
    if not realizations:
        logger.info("No realizations with responses in ensemble %s", ensemble.name)
        return None

    # Load the values for all those realizations into a single polars frame.
    responses = ensemble.load_responses(response_type.value, realizations)
    if responses.is_empty():
        return None

    # Rename the columns so the frame can be exported to Sumo.
    responses = _prepare_responses_dataframe(responses)

    table = responses.to_arrow()

    schema = pa.schema(
        [
            field.with_type(_convert_type_large_string_to_string(field.type))
            for field in table.schema
        ]
    )
    return table.cast(schema)
