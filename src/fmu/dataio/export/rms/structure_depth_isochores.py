from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from fmu.dataio._export import export_with_metadata
from fmu.dataio._export_config import ExportConfig
from fmu.dataio._logging import null_logger
from fmu.dataio.exceptions import ValidationError
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._base import SimpleExportRMSBase
from fmu.dataio.export.rms._utils import (
    get_rms_project_units,
    get_zones_in_folder,
    validate_name_in_stratigraphy,
)
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.enums import (
    Content,
    DomainReference,
    VerticalDomain,
)
from fmu.datamodels.standard_results.enums import StandardResultName

if TYPE_CHECKING:
    import xtgeo

_logger: Final = null_logger(__name__)


class _ExportStructureDepthIsochores(SimpleExportRMSBase):
    def __init__(self, project: Any, zone_folder: str) -> None:
        super().__init__()

        _logger.debug("Process data, establish state prior to export.")
        self._surfaces = get_zones_in_folder(project, zone_folder)
        self._unit = "m" if get_rms_project_units(project) == "metric" else "ft"
        _logger.debug("Process data... DONE")

    def _get_export_config(self, name: str) -> ExportConfig:
        """Export config for the standard result."""
        return (
            ExportConfig.builder()
            .content(Content.thickness)
            .domain(VerticalDomain.depth, DomainReference.msl)
            .unit(self._unit)
            .file_config(
                name=name, subfolder=StandardResultName.structure_depth_isochore.name
            )
            .access(Classification.internal, rep_include=True)
            .global_config(self._config)
            .standard_result(StandardResultName.structure_depth_isochore)
            .build()
        )

    def _export_surface(self, surf: xtgeo.RegularSurface) -> ExportResultItem:
        export_config = self._get_export_config(name=surf.name)
        absolute_export_path = export_with_metadata(export_config, surf)
        _logger.debug("Surface exported to: %s", absolute_export_path)

        return ExportResultItem(
            absolute_path=Path(absolute_export_path),
        )

    def _export_data_as_standard_result(self) -> ExportResult:
        """Do the actual surface export using dataio setup."""
        return ExportResult(
            items=[self._export_surface(surf) for surf in self._surfaces]
        )

    def _validate_data_pre_export(self) -> None:
        """Surface validations."""

        for surf in self._surfaces:
            validate_name_in_stratigraphy(surf.name, self._config)
            if (surf.values < 0).any():
                raise ValidationError(
                    f"Negative values detected for the isochore surface {surf.name}. "
                    "Please ensure input thicknesses are greater or equal to 0."
                )


def export_structure_depth_isochores(
    project: Any,
    zone_folder: str,
) -> ExportResult:
    """Simplified interface when exporting modelled depth isochores from RMS.

    Args:
        project: The 'magic' project variable in RMS.
        zone_folder: Name of zone folder in RMS.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_structure_depth_isochores

            export_results = export_structure_depth_isochores(
                project, "IS_extracted"
            )

            for result in export_results.items:
                print(f"Output isochore surfaces to {result.absolute_path}")

    """

    return _ExportStructureDepthIsochores(project, zone_folder).export()
