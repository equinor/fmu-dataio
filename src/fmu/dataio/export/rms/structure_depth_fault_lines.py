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
    get_faultlines_in_folder,
    get_open_polygons_id,
    get_rms_project_units,
    validate_name_in_stratigraphy,
)
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.enums import (
    Content,
    DomainReference,
    VerticalDomain,
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

    def _get_export_config(self, name: str) -> ExportConfig:
        """Export config for the standard result."""
        return (
            ExportConfig.builder()
            .content(Content.fault_lines)
            .domain(VerticalDomain.depth, DomainReference.msl)
            .unit(self._unit)
            .file_config(
                name=name,
                subfolder=StandardResultName.structure_depth_fault_lines.value,
            )
            .table_config(table_index=enums.FaultLines.index_columns())
            .access(Classification.internal, rep_include=True)
            .global_config(self._config)
            .standard_result(StandardResultName.structure_depth_fault_lines)
            .build()
        )

    def _export_fault_line(self, pol: xtgeo.Polygons) -> ExportResultItem:
        export_config = self._get_export_config(name=pol.name)
        absolute_export_path = export_with_metadata(export_config, pol)
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


def export_structure_depth_fault_lines(
    project: Any,
    horizon_folder: str,
) -> ExportResult:
    """Simplified interface when exporting fault lines from RMS.

    Args:
        project: The 'magic' project variable in RMS.
        horizon_folder: Name of horizon folder in RMS.

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
