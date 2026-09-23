from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import pyarrow as pa
import xtgeo

from fmu.dataio._export import ExportConfig, export_with_metadata
from fmu.dataio._logging import null_logger
from fmu.dataio.export._base import SimpleExportBase
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.datamodels import SimulatorLayerMappingResult
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.enums import Content
from fmu.datamodels.standard_results.enums import (
    SimulatorLayerMapping,
    StandardResultName,
)

_logger: Final = null_logger(__name__)


class _ExportLayerZoneMapping(SimpleExportBase):
    def __init__(self, mapping_table: pa.Table) -> None:
        super().__init__()

        self._mapping_table = mapping_table

    def _get_export_config(self) -> ExportConfig:
        """Export config for the standard result."""

        return (
            ExportConfig.builder()
            .content(Content.mapping)
            .file_config(
                name=StandardResultName.simulator_layer_mapping.value,
                subfolder=StandardResultName.simulator_layer_mapping.value,
            )
            .access(Classification.internal, rep_include=False)
            .global_config(self._config)
            .standard_result(StandardResultName.simulator_layer_mapping)
            .table_config(table_index=SimulatorLayerMapping.index_columns())
            .build()
        )

    def _export_data_as_standard_result(self) -> ExportResult:
        export_config = self._get_export_config()

        absolute_export_path = export_with_metadata(export_config, self._mapping_table)
        _logger.debug("Fip mapping table exported to: %s", absolute_export_path)

        return ExportResult(
            items=[ExportResultItem(absolute_path=Path(absolute_export_path))],
        )

    def _validate_data_pre_export(self) -> None:
        """Data validations before export."""
        SimulatorLayerMappingResult.model_validate(self._mapping_table.to_pylist())


def _create_layer_mapping_table(grid: xtgeo.Grid) -> pa.Table:
    """Create a layer / zone mapping table from an xtgeo.Grid."""

    mapping = []
    for zonename, layers in grid.subgrids.items():
        for layer in layers:
            mapping.append({"LAYER": layer, "ZONE": zonename})

    return pa.Table.from_pylist(mapping)


def _extract_layer_mapping_from_grid(project: Any, grid_name: str) -> pa.Table:
    """Create a layer / zone mapping table from a grid in RMS."""

    grid = xtgeo.grid_from_roxar(project, grid_name)
    return _create_layer_mapping_table(grid)


def export_simulator_layer_mapping(project: Any, grid_name: str) -> ExportResult:
    """Simplified interface for extracting a zonation from a simulation grid
    in RMS and exporting the corresponding layer / zone mappings as a
    standard result 'simulator_layer_mapping'.

    Args:
        project: The 'magic' project variable in RMS.
        grid_name: Name of the simulation grid in RMS.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_simulator_layer_mapping

            export_results = export_simulator_layer_mapping(
                project, grid_name="Simgrid"
            )

            for result in export_results.items:
                print(f"Layer mappings are exported to {result.absolute_path}")

    """

    mapping_table = _extract_layer_mapping_from_grid(project, grid_name)

    return _ExportLayerZoneMapping(mapping_table).export()
