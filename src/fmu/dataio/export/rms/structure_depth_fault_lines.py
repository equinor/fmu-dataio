from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import fmu.dataio as dio
from fmu.dataio._logging import null_logger
from fmu.dataio.exceptions import ValidationError
from fmu.dataio.export._decorators import experimental
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._base import SimpleExportRMSBase
from fmu.dataio.export.rms._utils import (
    get_faultlines_in_folder,
    get_open_polygons_id,
    get_rms_project_units,
    validate_name_in_stratigraphy,
)
from fmu.datamodels.fmu_results.enums import (
    Classification,
    Content,
    DomainReference,
    VerticalDomain,
)
from fmu.datamodels.fmu_results.standard_result import (
    StructureDepthFaultLinesStandardResult,
)
from fmu.datamodels.standard_results import enums
from fmu.datamodels.standard_results.enums import StandardResultName

if TYPE_CHECKING:
    import xtgeo

_logger: Final = null_logger(__name__)


class _ExportStructureDepthFaultLines(SimpleExportRMSBase):
    def __init__(self, project: Any, horizon_folder: str) -> None:
        super().__init__()

        _logger.debug("Process data, establish state prior to export.")
        self._horizon_folder = horizon_folder
        self._fault_lines = get_faultlines_in_folder(project, horizon_folder)
        self._unit = "m" if get_rms_project_units(project) == "metric" else "ft"
        _logger.debug("Process data... DONE")

    @property
    def _standard_result(self) -> StructureDepthFaultLinesStandardResult:
        """Standard result type for the exported data."""
        return StructureDepthFaultLinesStandardResult(
            name=StandardResultName.structure_depth_fault_lines
        )

    @property
    def _content(self) -> Content:
        """Get content for the exported data."""
        return Content.fault_lines

    @property
    def _classification(self) -> Classification:
        """Get default classification."""
        return Classification.internal

    @property
    def _rep_include(self) -> bool:
        """rep_include status"""
        return True

    def _export_fault_line(self, pol: xtgeo.Polygons) -> ExportResultItem:
        edata = dio.ExportData(
            config=self._config,
            content=self._content,
            unit=self._unit,
            vertical_domain=VerticalDomain.depth.value,
            domain_reference=DomainReference.msl.value,
            subfolder=self._subfolder,
            is_prediction=True,
            name=pol.name,
            classification=self._classification,
            rep_include=self._rep_include,
            table_index=enums.FaultLines.index_columns(),
        )

        edata.polygons_fformat = "parquet"  # type: ignore

        absolute_export_path = edata._export_with_standard_result(
            pol, standard_result=self._standard_result
        )
        _logger.debug("Fault_lines exported to: %s", absolute_export_path)

        return ExportResultItem(
            absolute_path=Path(absolute_export_path),
        )

    def _export_data_as_standard_result(self) -> ExportResult:
        """Export the fault lines for each stratigraphic horizon."""
        return ExportResult(
            items=[self._export_fault_line(pol) for pol in self._fault_lines]
        )

    def _raise_on_open_polygons(self, pol: xtgeo.Polygons) -> None:
        """
        Check that all fault line polygons within the polygon set are closed.
        Raise error if open polygons are found.
        """

        if open_polygons := get_open_polygons_id(pol):
            df = pol.get_dataframe(copy=False)
            fault_names = (
                df.loc[
                    df[pol.pname].isin(open_polygons),
                    enums.FaultLines.TableIndexColumns.NAME.value,
                ]
                .unique()
                .tolist()
            )
            raise ValidationError(
                "All fault line polygons must be closed. The following faults "
                f"are open for horizon {pol.name}: {fault_names}. Ensure that the "
                f"horizon folder {self._horizon_folder} contains valid fault lines."
            )

    def _validate_data_pre_export(self) -> None:
        """Data validations before export."""

        for pol in self._fault_lines:
            validate_name_in_stratigraphy(pol.name, self._config)
            self._raise_on_open_polygons(pol)


@experimental
def export_structure_depth_fault_lines(
    project: Any,
    horizon_folder: str,
) -> ExportResult:
    """Simplified interface when exporting fault lines from RMS.

    Args:
        project: The 'magic' project variable in RMS.
        horizon_folder: Name of horizon folder in RMS.
    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_structure_depth_fault_lines

            export_results = export_structure_depth_fault_lines(
                project, "DL_faultlines"
            )

            for result in export_results.items:
                print(f"Output fault line polygons to {result.absolute_path}")

    """

    return _ExportStructureDepthFaultLines(project, horizon_folder).export()
