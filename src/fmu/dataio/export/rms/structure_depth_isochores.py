from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import fmu.dataio as dio
from fmu.dataio._export import export_with_metadata
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
from fmu.datamodels.fmu_results import standard_result
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

    @property
    def _standard_result(self) -> standard_result.StructureDepthIsochoreStandardResult:
        """Standard result type for the exported data."""
        return standard_result.StructureDepthIsochoreStandardResult(
            name=StandardResultName.structure_depth_isochore
        )

    @property
    def _content(self) -> Content:
        """Get content for the exported data."""
        return Content.thickness

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
            vertical_domain=VerticalDomain.depth.value,
            domain_reference=DomainReference.msl.value,
            subfolder=self._subfolder,
            is_prediction=True,
            name=surf.name,
            classification=self._classification,
            rep_include=self._rep_include,
        )

        absolute_export_path = export_with_metadata(
            edata._export_config, surf, standard_result=self._standard_result
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
