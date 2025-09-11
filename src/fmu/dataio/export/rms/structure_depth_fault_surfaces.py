from __future__ import annotations

from pathlib import Path
from typing import Any, Final, Self

import numpy as np

import fmu.dataio as dio
from fmu.dataio._logging import null_logger
from fmu.dataio._readers.tsurf import (
    AllowedKeywordValues,
    CoordinateSystem,
    Header,
    TSurfData,
)
from fmu.dataio.export._decorators import experimental
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.dataio.export.rms._base import SimpleExportRMSBase
from fmu.dataio.export.rms._utils import (
    get_rms_project_units,
)
from fmu.datamodels.fmu_results.enums import (
    Classification,
    Content,
    DomainReference,
    VerticalDomain,
)
from fmu.datamodels.fmu_results.standard_result import (
    StructureDepthFaultSurfaceStandardResult,
)
from fmu.datamodels.standard_results.enums import StandardResultName

_logger: Final = null_logger(__name__)


class _ExportStructureDepthFaultSurfaces(SimpleExportRMSBase):
    def __init__(
        self: Self,
        project: Any,
        structural_model_name: str,
    ) -> None:
        super().__init__()

        _logger.debug("Process data, establish state prior to export.")

        self._unit = "m" if get_rms_project_units(project) == "metric" else "ft"

        self._surfaces = _get_fault_surfaces_from_rms(project, structural_model_name)

        _logger.debug("Process data... DONE")

    @property
    def _standard_result(self) -> StructureDepthFaultSurfaceStandardResult:
        """Standard result type for the exported data."""
        return StructureDepthFaultSurfaceStandardResult(
            name=StandardResultName.structure_depth_fault_surface
        )

    @property
    def _content(self) -> Content:
        """Get content for the exported data."""
        return Content.fault_surface

    @property
    def _classification(self) -> Classification:
        """Get default classification."""
        return Classification.internal

    @property
    def _rep_include(self) -> bool:
        """rep_include status"""
        return True

    def _export_surface(self: Self, surf: TSurfData) -> ExportResultItem:
        edata = dio.ExportData(
            config=self._config,
            content=self._content,
            unit=self._unit,
            vertical_domain=VerticalDomain.depth.value,
            domain_reference=DomainReference.msl.value,
            subfolder=self._subfolder,
            is_prediction=True,
            name=surf.header.name,
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
        """Export the fault surfaces as a standard result."""
        return ExportResult(
            items=[self._export_surface(surf) for surf in self._surfaces]
        )

    def _validate_data_pre_export(self) -> None:
        """Surface validations before export."""
        # The surfaces are Pydantic models and are automatically validated


def _get_fault_surfaces_from_rms(
    project: Any,
    structural_model_name: str,
) -> list[TSurfData]:
    """
    Fetch triangulated fault surfaces in TSurf format from RMS.

    Args:
        project: the 'magic' project variable in RMS
        structural_model_name: name of the structural model

    Returns:
        List of TSurfData objects (GoCAD TSurf) representing
        all fault surfaces in the structural model as triangulations.
    """

    if structural_model_name not in project.structural_models:
        raise ValueError(
            f"Project does not contain a structural model named: "
            f"'{structural_model_name}'."
        )

    fault_model = project.structural_models[structural_model_name].fault_model

    realization = 0
    tsurf_coord_sys = CoordinateSystem(
        name="Default",
        axis_name=AllowedKeywordValues.axis_names["xyz"],
        axis_unit=(
            AllowedKeywordValues.axis_units["mmm"]
            if get_rms_project_units(project) == "metric"
            else AllowedKeywordValues.axis_units["ft"]
        ),
        z_positive=AllowedKeywordValues.z_positives["depth"],
    )

    fault_surfaces = []
    for fault_name in fault_model.fault_names:
        fault_surface = fault_model.get_fault_triangle_surface(
            name=fault_name,
            realisation=realization,
        )

        tsurf_header = Header(name=fault_name)

        vertices = fault_surface.get_vertices()
        # GoCAD TSurf uses 1-based indexing for triangles while RMS uses 0-based
        triangles = fault_surface.get_triangles().astype(np.int64) + 1

        tsurf = TSurfData(
            header=tsurf_header,
            coordinate_system=tsurf_coord_sys,
            vertices=vertices,
            triangles=triangles,
        )

        fault_surfaces.append(tsurf)

    return fault_surfaces


@experimental
def export_structure_depth_fault_surfaces(
    project: Any, structural_model_name: str
) -> ExportResult:
    """
    Simplified interface when exporting triangulated fault surfaces from RMS.

    Args:
        project: the 'magic' project variable in RMS
        structural_model_name: name of the structural model
    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_structure_depth_fault_surfaces

            export_results = export_structure_depth_fault_surfaces(
                project,
                "structural_model_name"
            )

            for result in export_results.items:
                print(f"Output surfaces to {result.absolute_path}")

    """

    return _ExportStructureDepthFaultSurfaces(project, structural_model_name).export()
