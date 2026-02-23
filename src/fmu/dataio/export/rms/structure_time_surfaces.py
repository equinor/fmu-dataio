from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from fmu.dataio._export import export_with_metadata
from fmu.dataio._export_config import ExportConfig
from fmu.dataio._logging import null_logger
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._base import SimpleExportRMSBase
from fmu.dataio.export.rms._utils import (
    get_horizons_in_folder,
    get_rms_project_units,
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


class _ExportStructureTimeSurfaces(SimpleExportRMSBase):
    def __init__(self, project: Any, horizon_folder: str) -> None:
        super().__init__()

        _logger.debug("Process data, establish state prior to export.")
        self._surfaces = get_horizons_in_folder(project, horizon_folder)
        self._unit = "m" if get_rms_project_units(project) == "metric" else "ft"
        _logger.debug("Process data... DONE")

    def _get_export_config(self, name: str) -> ExportConfig:
        """Export config for the standard result."""
        return (
            ExportConfig.builder()
            .content(Content.time)
            .domain(VerticalDomain.time, DomainReference.msl)
            .unit(self._unit)
            .file_config(
                name=name, subfolder=StandardResultName.structure_time_surface.name
            )
            .access(Classification.internal, rep_include=True)
            .global_config(self._config)
            .standard_result(StandardResultName.structure_time_surface)
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
        # TODO: Add check that the surfaces are consistent, i.e. a stratigraphic
        # deeper surface should never have shallower values than the one above
        for surf in self._surfaces:
            validate_name_in_stratigraphy(surf.name, self._config)


def export_structure_time_surfaces(
    project: Any,
    horizon_folder: str,
) -> ExportResult:
    """Simplified interface when exporting modelled time surfaces from RMS.

    Args:
        project: The 'magic' project variable in RMS.
        horizon_folder: Name of horizon folder in RMS.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_structure_time_surfaces

            export_results = export_structure_time_surfaces(project, "TS_extracted")

            for result in export_results.items:
                print(f"Output surfaces to {result.absolute_path}")

    """
    return _ExportStructureTimeSurfaces(project, horizon_folder).export()
