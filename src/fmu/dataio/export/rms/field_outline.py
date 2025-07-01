from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import xtgeo

import fmu.dataio as dio
from fmu.dataio._logging import null_logger
from fmu.dataio.exceptions import ValidationError
from fmu.dataio.export._decorators import experimental
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._base import SimpleExportRMSBase
from fmu.dataio.export.rms._utils import get_open_polygons_id
from fmu.datamodels.fmu_results.enums import (
    Classification,
    Content,
    DomainReference,
    FluidContactType,
    VerticalDomain,
)
from fmu.datamodels.fmu_results.standard_result import FieldOutlineStandardResult
from fmu.datamodels.standard_results.enums import StandardResultName

_logger: Final = null_logger(__name__)


class _ExportFieldOutline(SimpleExportRMSBase):
    def __init__(self, project: Any) -> None:
        super().__init__()

        _logger.debug("Process data, establish state prior to export.")
        self._field_outline = self._get_field_outline_from_rms(project)

        _logger.debug("Process data... DONE")

    @property
    def _standard_result(self) -> FieldOutlineStandardResult:
        """Standard result type for the exported data."""
        return FieldOutlineStandardResult(name=StandardResultName.field_outline)

    @property
    def _content(self) -> Content:
        """Get content for the exported data."""
        return Content.field_outline

    @property
    def _classification(self) -> Classification:
        """Get default classification."""
        return Classification.internal

    @property
    def _rep_include(self) -> bool:
        """rep_include status"""
        return True

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

    def _export_data_as_standard_result(self) -> ExportResult:
        edata = dio.ExportData(
            config=self._config,
            content=self._content,
            content_metadata={"contact": FluidContactType.fwl},
            vertical_domain=VerticalDomain.depth.value,
            domain_reference=DomainReference.msl.value,
            subfolder=self._subfolder,
            is_prediction=True,
            name=StandardResultName.field_outline.value,
            classification=self._classification,
            rep_include=self._rep_include,
        )

        edata.polygons_fformat = "parquet"  # type: ignore

        absolute_export_path = edata._export_with_standard_result(
            self._field_outline, standard_result=self._standard_result
        )
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


@experimental
def export_field_outline(project: Any) -> ExportResult:
    """Simplified interface when exporting field outline from RMS.

    Args:
        project: The 'magic' project variable in RMS.
    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_field_outline

            export_results = export_field_outline(project)

            for result in export_results.items:
                print(f"Output field outline polygon to {result.absolute_path}")

    """

    return _ExportFieldOutline(project).export()
