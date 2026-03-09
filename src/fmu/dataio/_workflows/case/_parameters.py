"""Extract and process Ert parameters."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

import ert
import pyarrow as pa
from pydantic import TypeAdapter

from fmu.datamodels import ErtParameterMetadata

from ._config import CaseWorkflowConfig

if TYPE_CHECKING:
    import polars as pl


logger: Final = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

ErtParameterMetadataAdapter: TypeAdapter[ErtParameterMetadata] = TypeAdapter(
    ErtParameterMetadata
)


def _genkw_to_metadata(config: ert.config.GenKwConfig) -> ErtParameterMetadata:
    """Convert GenKwConfig to parameter metadata."""
    distribution_dict = config.distribution.model_dump(exclude={"name"})
    return ErtParameterMetadataAdapter.validate_python(
        {
            "group": config.group or "DEFAULT",
            "input_source": config.input_source,
            "distribution": config.distribution.name.lower(),
            **distribution_dict,
        }
    )


def _resolve_pa_field_type(name: str, pa_type: pa.DataType) -> pa.DataType:
    """Ensures some PyArrow field types are changed to smaller ones.

    In particular, APS produces some columns that have simple text fields with one
    word. These come by default as large_string()."""
    if name == "REAL" and pa.types.is_int64(pa_type):
        return pa.int32()
    if pa.types.is_large_unicode(pa_type):
        return pa.utf8()
    if pa.types.is_large_string(pa_type):
        return pa.string()
    return pa_type


def _process_parameters(
    scalars_df: pl.DataFrame, ensemble: ert.Ensemble
) -> tuple[pa.Table, list[int]]:
    """Process parameters into an Arrow table with metadata."""
    import pyarrow as pa

    param_configs = ensemble.experiment.parameter_configuration
    realizations = scalars_df.get_column("realization").to_list()

    columns_to_drop: list[str] = []
    metadata_map: dict[str, dict[bytes, bytes]] = {}
    rename_map: dict[str, str] = {
        "realization": "REAL",
    }

    for col_name in scalars_df.columns:
        if col_name == "realization":
            continue

        param_name: str = col_name.split(":", 1)[-1] if ":" in col_name else col_name
        config = param_configs.get(param_name)

        if isinstance(config, ert.config.GenKwConfig):
            metadata = _genkw_to_metadata(config)
            metadata_map[param_name] = metadata.to_pa_metadata()
            rename_map[col_name] = param_name
        else:
            columns_to_drop.append(col_name)
            logger.info(f"Skipping '{col_name}': no valid GenKwConfig found")

    scalars_df = scalars_df.drop(columns_to_drop).rename(rename_map)
    arrow_table = scalars_df.to_arrow()

    fields = [
        pa.field(
            f.name,
            _resolve_pa_field_type(f.name, f.type),
            metadata=metadata_map.get(f.name),
        )
        for f in arrow_table.schema
    ]
    table = arrow_table.cast(pa.schema(fields))

    return table, realizations


def get_ert_parameters_table(
    ensemble: ert.Ensemble,
    run_paths: ert.Runpaths,
    workflow_config: CaseWorkflowConfig,
) -> pa.Table | None:
    """Exports Ert parameters as a Parquet file as the ensemble level."""

    scalars_df = ensemble.load_scalars()
    if scalars_df.is_empty():
        logger.warning("No scalar parameters found in ensemble")
        return None

    table, _ = _process_parameters(scalars_df, ensemble)
    return table
