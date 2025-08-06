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
        fault_names: list[str] | None = None,
    ) -> None:
        super().__init__()

        _logger.debug("Process data, establish state prior to export.")

        if not self._is_valid_input(project, structural_model_name, fault_names):
            raise ValueError("Invalid input for export of fault surfaces.")

        self._unit = "m" if get_rms_project_units(project) == "metric" else "ft"

        self._surfaces = []
        structural_model = project.structural_models[structural_model_name]
        fault_model = structural_model.fault_model

        # Use only the fault_names requested in the input.
        # If fault_names are not given, use all faults in the fault model

        fault_names_for_export = (
            fault_names
            if fault_names is not None and len(fault_names) > 0
            else fault_model.fault_names
        )

        fault_surfaces = get_fault_surfaces_from_rms(
            project, structural_model_name, fault_names_for_export
        )

        self._surfaces = fault_surfaces
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
        # TODO: @ecs: correct return value?
        return True

    def _export_surface(self: Self, surf: TSurfData) -> ExportResultItem:
        edata = dio.ExportData(
            config=self._config,
            content=self._content,
            # TODO: @ecs: provide 'fmu_context'?
            # If yes, should also provide 'casepath'
            # What's a 'case', is it the input RMS model?
            # TODO: @ecs: specify 'geometry', where it should reference either
            # the 3D grid or the fault surface?
            # TODO: @ecs: 'name' = tsurf.header.name?
            unit=self._unit,
            vertical_domain=VerticalDomain.depth.value,
            # TODO: @ecs: is MSL the correct domain reference?
            # If that is the default, how can we know?
            domain_reference=DomainReference.msl.value,
            subfolder=self._subfolder,
            # TODO: @ecs: is the surface a prediction?
            # If that is the default, how can we know?
            is_prediction=True,
            name=surf.header.name,
            classification=self._classification,
            rep_include=self._rep_include,
            # TODO: @ecs: how do we infer which RMS project the data originate from?
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

    def _is_valid_input(
        self: Self,
        project: Any,
        structural_model_name: str,
        fault_names: list[str] | None = None,
    ) -> bool:
        """
        Validate the content of the structural model:
        project exists, structural model exists,
        fault model is None or exists, and, if fault names are given,
        these faults exist in the fault model..

        Args:
        project: the 'magic' project variable in RMS
        structural_model_name: name of the structural model
        fault_names: optional list of fault names
        """

        # TODO: maybe this already verified somewhere else? In dataio or rms_api?
        # TODO: check rms_api for similar functionalities
        # TODO: if function is to be kept, make a test for it

        if not project:
            _logger.warning("Project not found.")
            return False

        if structural_model_name not in project.structural_models:
            _logger.warning(
                "Structural model '%s' not found in project.", structural_model_name
            )
            return False

        fault_model = project.structural_models[structural_model_name].fault_model

        # TODO: it is assumed that it is a valid state that no fault model exists in
        # the structural model.
        # If this assumption is incorrect, the following validation logic
        # must be updated.

        if fault_names is not None and len(fault_names) > 0:
            if fault_model is None or len(fault_model.fault_names) == 0:
                _logger.warning(
                    "Fault names are given but no faults exist in the "
                    "structural model '%s'.",
                    structural_model_name,
                )
                return False

            # Check that all given fault names are in the fault model
            if not set(fault_names).issubset(set(fault_model.fault_names)):
                # Find the fault names that are not in the fault model
                missing_faults = set(fault_names) - set(fault_model.fault_names)
                _logger.warning(
                    "Some fault names are not found in structural model '%s'. "
                    "The faults in the structural model are: %s."
                    "The faults that are missing in the structural model are: %s.",
                    structural_model_name,
                    fault_model.fault_names,
                    missing_faults,
                )
                return False

        return True


# TODO: @ecs: this method retrieves fault surfaces via rmsapi and returns them in memory
# so that they can be exported directly.
# Should they be stored in an RMS folder first, and then fetched from there - as we do
# with e.g. structure depth surfaces?


@experimental
# Temporary placement, should be moved to e.g. xtgeo
# TODO: @ecs: where to put this function?
def get_fault_surfaces_from_rms(
    project: Any,
    structural_model_name: str,
    fault_names: list[str],
) -> list[TSurfData]:
    """
    Fetch triangulated fault surfaces in TSurf format from RMS.

    Args:
        project: the 'magic' project variable in RMS
        structural_model_name: name of the structural model
        fault_names: optional list of fault names to export
            (if not given or empty: all faults in structural model are exported)

    Returns:
        List of TSurfData objects (GoCAD TSurf format) representing
        the fault surfaces as triangulations.
    """

    import warnings

    warnings.warn(
        "This method ('get_fault_surfaces_from_rms') will soon be moved to another "
        "module, most likely 'xtgeo'. It is therefore marked as experimental.",
        DeprecationWarning,
    )

    # Get points and triangles for each fault surface in the structural model
    # and use them to construct a TSurfData object

    fault_surfaces = []
    # TODO: @ecs: realization hardcoded = 0. But probably need to be more flexible?
    # Also includes storing realization number to SUMO?
    realization = 0
    for fault_name in fault_names:
        fault_surface = project.structural_models[
            structural_model_name
        ].fault_model.get_fault_triangle_surface(
            name=fault_name,
            realisation=realization,
        )

        if fault_surface is None:
            _logger.warning(
                "Could not retrieve triangulated surface for fault '%s' in "
                "structural model '%s'.",
                fault_name,
                structural_model_name,
            )
            continue

        tsurf_header = Header(name=fault_name)
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

        # Both triangles and vertices are on the same format as in TSurfData
        vertices = fault_surface.get_vertices()
        # TODO: @ecs: verify that RMS returns 0-based indices
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
    project: Any, structural_model_name: str, fault_names: list[str] | None = None
) -> ExportResult:
    """
    Simplified interface when exporting triangulated fault surfaces from RMS.

    Args:
        project: the 'magic' project variable in RMS
        structural_model_name: name of the structural model
        fault_names: optional list (if not given or empty: all faults are exported)
    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_structure_depth_fault_surfaces

            export_results = export_structure_depth_fault_surfaces(
                project,
                "struct_mod_scenario_54_sand_injectites_polyg_faults",
                ["fault1", "fault2"]
            )

            for result in export_results.items:
                print(f"Output surfaces to {result.absolute_path}")

    """

    return _ExportStructureDepthFaultSurfaces(
        project, structural_model_name, fault_names
    ).export()
