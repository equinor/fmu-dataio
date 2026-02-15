from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import pyarrow as pa
import xtgeo

from fmu.dataio._export import export_with_metadata
from fmu.dataio._export_config import ExportConfig
from fmu.dataio._logging import null_logger
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._base import SimpleExportRMSBase
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.enums import (
    Content,
)
from fmu.datamodels.fmu_results.standard_result import (
    MappingsSimulatorFipregionsStandardResult,
)
from fmu.datamodels.standard_results.enums import StandardResultName

_logger: Final = null_logger(__name__)

FIPNAME: Final = "FIPNUM"


class _ExportFipZoneRegionMapping(SimpleExportRMSBase):
    def __init__(self, mapping_table: pa.Table) -> None:
        super().__init__()

        self._mapping_table = mapping_table

    @property
    def _standard_result(self) -> MappingsSimulatorFipregionsStandardResult:
        """Standard result type for the exported data."""
        return MappingsSimulatorFipregionsStandardResult(
            name=StandardResultName.mappings_simulator_fipregions
        )

    @property
    def _content(self) -> Content:
        """Get content for the exported data."""
        return Content.mappings

    @property
    def _classification(self) -> Classification:
        """Get default classification."""
        return Classification.internal

    @property
    def _rep_include(self) -> bool:
        """rep_include status"""
        return False

    def _export_data_as_standard_result(self) -> ExportResult:
        export_config = (
            ExportConfig.builder()
            .content(self._content)
            .file_config(
                name=StandardResultName.mappings_simulator_fipregions.value,
                subfolder=self._subfolder,
            )
            .access(self._classification, self._rep_include)
            .global_config(self._config)
            .standard_result(StandardResultName.mappings_simulator_fipregions)
            .build()
        )

        absolute_export_path = export_with_metadata(export_config, self._mapping_table)
        _logger.debug("Fip mapping table exported to: %s", absolute_export_path)

        return ExportResult(
            items=[ExportResultItem(absolute_path=Path(absolute_export_path))],
        )

    def _validate_data_pre_export(self) -> None:
        """Data validations before export."""


def _create_fipnum_from_region_and_zone(
    zone: xtgeo.GridProperty, region: xtgeo.GridProperty
) -> pa.Table:
    """
    Create a FIPNUM property with a unique value per region / zone combination.
    The mappings from FIPNUM value to corresponding zone and region names are
    collected and returned as a table.
    """

    fipnum = xtgeo.GridProperty(zone, discrete=True, values=0)

    mapping = []
    fipvalue = 1
    for zonecode, zonename in zone.codes.items():
        for regcode, regname in region.codes.items():
            cell_filter = (region.values == regcode) & (zone.values == zonecode)
            fipnum.values[cell_filter] = fipvalue

            fipnum.codes[fipvalue] = f"{regname}_{zonename}"

            mapping.append({FIPNAME: fipvalue, "REGION": regname, "ZONE": zonename})

            fipvalue += 1

    return fipnum, pa.Table.from_pylist(mapping)


def create_fip_property(
    project: Any, grid_name: str, region: str, zone: str
) -> ExportResult:
    """Simplified interface for creating a FIPNUM property in RMS and exporting
    the corresponding zone / region mappings.

    The FIPNUM property will have a unique value per region / zone combination
    and the mapping between a FIPNUM value and the corresponding region and zone
    names will be exported as a table to be uploaded by Sumo.

    Args:
        project: The 'magic' project variable in RMS.
        grid_name: Name of the grid in RMS.
        region: Name of the region property in RMS.
        zone: Name of the zone property in RMS.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import create_fip_property

            export_results = create_fip_property(project, "Simgrid", "Region", "Zone")

            for result in export_results.items:
                print(f"Fipnum mappings are exported to {result.absolute_path}")

    """

    region = xtgeo.gridproperty_from_roxar(project, grid_name, region)
    zone = xtgeo.gridproperty_from_roxar(project, grid_name, zone)

    fipnum, mapping_table = _create_fipnum_from_region_and_zone(zone, region)

    fipnum.to_roxar(project, grid_name, FIPNAME)

    return _ExportFipZoneRegionMapping(mapping_table).export()
