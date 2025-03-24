from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import fmu.dataio as dio
from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.enums import (
    Classification,
    Content,
    StandardResultName,
)
from fmu.dataio._models.fmu_results.standard_result import (
    StructureDepthFaultLinesStandardResult,
)
from fmu.dataio.exceptions import ValidationError
from fmu.dataio.export._decorators import experimental
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._utils import (
    get_polygons_in_folder,
    get_rms_project_units,
    load_global_config,
)

if TYPE_CHECKING:
    import xtgeo

_logger: Final = null_logger(__name__)


class _ExportStructureDepthFaultLines:
    def __init__(
        self,
        project: Any,
        horizon_folder: str,
    ) -> None:
        _logger.debug("Process data, establish state prior to export.")
        self._horizon_folder = horizon_folder
        self._config = load_global_config()
        self._fault_lines = get_polygons_in_folder(project, horizon_folder)
        self._unit = "m" if get_rms_project_units(project) == "metric" else "ft"

        _logger.debug("Process data... DONE")

    @property
    def _standard_result(self) -> StructureDepthFaultLinesStandardResult:
        """Standard result type for the exported data."""
        return StructureDepthFaultLinesStandardResult(
            name=StandardResultName.structure_depth_fault_lines
        )

    @property
    def _classification(self) -> Classification:
        """Get default classification."""
        return Classification.internal

    @property
    def _subfolder(self) -> str:
        """Subfolder for exporting the data to."""
        return StandardResultName.structure_depth_fault_lines.value

    def _export_fault_line(self, pol: xtgeo.Polygons) -> ExportResultItem:
        edata = dio.ExportData(
            config=self._config,
            content=Content.fault_lines.value,
            unit=self._unit,
            vertical_domain="depth",
            domain_reference="msl",
            subfolder=self._subfolder,
            is_prediction=True,
            name=pol.name,
            classification=self._classification,
            rep_include=True,
        )

        edata.polygons_fformat = "parquet"  # type: ignore

        absolute_export_path = edata._export_with_standard_result(
            pol, standard_result=self._standard_result
        )
        _logger.debug("Fault_lines exported to: %s", absolute_export_path)

        return ExportResultItem(
            absolute_path=Path(absolute_export_path),
        )

    def _export_fault_lines(self) -> ExportResult:
        """Export the fault lines for each stratigraphic horizon."""
        return ExportResult(
            items=[self._export_fault_line(pol) for pol in self._fault_lines]
        )

    def _raise_on_open_polygons(self, pol: xtgeo.Polygons) -> None:
        """
        Check that all fault line polygons within the polygon set are closed. In a
        closed polygon the first and last row of the dataframe are equal i.e. equal
        coordinates. If an open polygon is found an error is given.
        """
        open_polygons = []
        for polid, poldf in pol.get_dataframe(copy=False).groupby("POLY_ID"):
            if not poldf.iloc[0].equals(poldf.iloc[-1]):
                open_polygons.append(polid)

        # TODO provide fault names when NAME attribute is possible to
        # fetch with xtgeo.
        if open_polygons:
            raise ValidationError(
                "All fault line polygons must be closed. Found "
                f"{len(open_polygons)} open ones for horizon {pol.name}. "
                f"Ensure that the horizon folder {self._horizon_folder} "
                "actually contains fault lines."
            )

    def _validate_data(self) -> None:
        """Data validations before export."""
        # TODO: check that the fault lines have a stratigraphy entry.

        for pol in self._fault_lines:
            self._raise_on_open_polygons(pol)

    def export(self) -> ExportResult:
        """Export the fault lines as a standard_result."""
        self._validate_data()
        return self._export_fault_lines()


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
