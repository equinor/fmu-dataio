from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import fmu.dataio as dio
from fmu.dataio._logging import null_logger
from fmu.dataio.export._decorators import experimental
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._base import SimpleExportRMSBase
from fmu.dataio.export.rms._utils import (
    get_horizons_in_folder,
    get_rms_project_units,
    validate_name_in_stratigraphy,
)
from fmu.datamodels.fmu_results import standard_result
from fmu.datamodels.fmu_results.enums import (
    Classification,
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

    @property
    def _standard_result(self) -> standard_result.StructureTimeSurfaceStandardResult:
        """Standard result type for the exported data."""
        return standard_result.StructureTimeSurfaceStandardResult(
            name=StandardResultName.structure_time_surface
        )

    @property
    def _content(self) -> Content:
        """Get content for the exported data."""
        return Content.time

    @property
    def _classification(self) -> Classification:
        """Get default classification."""
        return Classification.internal

    @property
    def _rep_include(self) -> bool:
        """rep_include status"""
        return True

    def _export_surface(self, surf: xtgeo.RegularSurface) -> ExportResultItem:
        edata = dio.ExportData(
            config=self._config,
            content=self._content,
            unit=self._unit,
            vertical_domain=VerticalDomain.time.value,
            domain_reference=DomainReference.msl.value,
            subfolder=self._subfolder,
            is_prediction=True,
            name=surf.name,
            classification=self._classification,
            rep_include=self._rep_include,
        )

        absolute_export_path = edata._export_with_standard_result(
            surf, standard_result=self._standard_result
        )
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


@experimental
def export_structure_time_surfaces(
    project: Any,
    horizon_folder: str,
) -> ExportResult:
    """Simplified interface when exporting modelled time surfaces from RMS.

    Args:
        project: The 'magic' project variable in RMS.
        horizon_folder: Name of horizon folder in RMS.
    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_structure_time_surfaces

            export_results = export_structure_time_surfaces(project, "TS_extracted")

            for result in export_results.items:
                print(f"Output surfaces to {result.absolute_path}")

    """
    return _ExportStructureTimeSurfaces(project, horizon_folder).export()
