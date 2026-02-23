from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import xtgeo

from fmu.dataio._export import export_with_metadata
from fmu.dataio._export_config import ExportConfig
from fmu.dataio._logging import null_logger
from fmu.dataio.exceptions import ValidationError
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._base import SimpleExportRMSBase
from fmu.dataio.export.rms._utils import get_open_polygons_id
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.data import FieldOutline
from fmu.datamodels.fmu_results.enums import (
    Content,
    DomainReference,
    FluidContactType,
    VerticalDomain,
)
from fmu.datamodels.standard_results.enums import StandardResultName

_logger: Final = null_logger(__name__)


class _ExportFieldOutline(SimpleExportRMSBase):
    def __init__(self, project: Any) -> None:
        super().__init__()

        _logger.debug("Process data, establish state prior to export.")
        self._field_outline = self._get_field_outline_from_rms(project)

        _logger.debug("Process data... DONE")

    def _get_field_outline_from_rms(self, project: Any) -> xtgeo.Polygons:
        """Fetch the field outline polygon from RMS."""
        try:
            return xtgeo.polygons_from_roxar(
                project, "field_outline", category="", stype="general2d_data"
            )
        except Exception as err:
            raise ValueError(
                "Could not load the field outline polygon from RMS. "
                "Ensure a polygon named 'field_outline' exists in the root "
                "of the 'General 2D data' folder."
            ) from err

    def _get_export_config(self) -> ExportConfig:
        """Export config for the standard result."""
        return (
            ExportConfig.builder()
            .content(Content.field_outline, FieldOutline(contact=FluidContactType.fwl))
            .domain(VerticalDomain.depth, DomainReference.msl)
            .file_config(
                name=StandardResultName.field_outline.value,
                subfolder=StandardResultName.field_outline.value,
            )
            .access(Classification.internal, rep_include=True)
            .global_config(self._config)
            .standard_result(StandardResultName.field_outline)
            .build()
        )

    def _export_data_as_standard_result(self) -> ExportResult:
        export_config = self._get_export_config()

        absolute_export_path = export_with_metadata(export_config, self._field_outline)
        _logger.debug("Field outline exported to: %s", absolute_export_path)

        return ExportResult(
            items=[ExportResultItem(absolute_path=Path(absolute_export_path))],
        )

    def _validate_data_pre_export(self) -> None:
        """Data validations before export."""
        if get_open_polygons_id(self._field_outline):
            raise ValidationError(
                "The field outline object can only contain closed polygons. "
            )


def export_field_outline(project: Any) -> ExportResult:
    """Simplified interface when exporting field outline from RMS.

    Args:
        project: The 'magic' project variable in RMS.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_field_outline

            export_results = export_field_outline(project)

            for result in export_results.items:
                print(f"Output field outline polygon to {result.absolute_path}")

    """

    return _ExportFieldOutline(project).export()
