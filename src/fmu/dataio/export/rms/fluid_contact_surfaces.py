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
    get_rms_project_units,
    get_surfaces_in_general2d_folder,
    list_folder_names_in_general2d_folder,
    validate_name_in_stratigraphy,
)
from fmu.datamodels.fmu_results import standard_result
from fmu.datamodels.fmu_results.enums import (
    Classification,
    Content,
    DomainReference,
    FluidContactType,
    VerticalDomain,
)
from fmu.datamodels.standard_results.enums import StandardResultName

if TYPE_CHECKING:
    import xtgeo

_logger: Final = null_logger(__name__)

GENERAL2D_FOLDER = "fluid_contact_surfaces"


class _ExportFluidContactSurfaces(SimpleExportRMSBase):
    def __init__(self, project: Any) -> None:
        super().__init__()

        _logger.debug("Process data, establish state prior to export.")
        self.project = project
        self._contact_surfaces = self._get_contact_surfaces()
        self._unit = "m" if get_rms_project_units(project) == "metric" else "ft"
        _logger.debug("Process data... DONE")

    @property
    def _standard_result(self) -> standard_result.FluidContactSurfaceStandardResult:
        """Standard result type for the exported data."""
        return standard_result.FluidContactSurfaceStandardResult(
            name=StandardResultName.fluid_contact_surface
        )

    @property
    def _content(self) -> Content:
        """Get content for the exported data."""
        return Content.fluid_contact

    @property
    def _classification(self) -> Classification:
        """Get default classification."""
        return Classification.internal

    @property
    def _rep_include(self) -> bool:
        """rep_include status"""
        return True

    def _get_contacts(self) -> list[FluidContactType]:
        """
        Get FluidContactTypes from available subfolder names in the main folder.
        Folders with invalid contact names will be skipped. If no valid contact
        names are found an error is raised.
        """

        contact_folders = list_folder_names_in_general2d_folder(
            self.project, folder_path=[GENERAL2D_FOLDER]
        )
        valid_contact_folders = []
        for contact in contact_folders:
            try:
                valid_contact_folders.append(FluidContactType(contact))
            except ValueError:
                _logger.info(f"{contact} is not a valid contact name, skipping folder.")
                continue

        _logger.debug(f"Found valid contact folders {valid_contact_folders}.")
        return valid_contact_folders

    def _contact_folder_present(self) -> bool:
        """Check if the main contact folder is present in General 2D data"""
        return GENERAL2D_FOLDER in self.project.general2d_data.folders

    def _get_contact_surfaces(
        self,
    ) -> dict[FluidContactType, list[xtgeo.RegularSurface]]:
        """
        Get a dictionary with fluid contact surfaces per contact folder
        found in the main folder.
        """

        if self._contact_folder_present() and (contacts := self._get_contacts()):
            return {
                contact: get_surfaces_in_general2d_folder(
                    self.project, folder_path=[GENERAL2D_FOLDER, contact.value]
                )
                for contact in contacts
            }
        raise ValueError(
            "Could not detect any fluid contact surfaces from RMS. "
            f"Ensure the folder '{GENERAL2D_FOLDER}' exists in the "
            "'General 2D data' folder, and that it contains minimum one subfolder "
            f"with a valid contact name: {list(FluidContactType.__members__)}. The "
            "contact surfaces should be contained inside these subfolders."
        )

    def _export_contact_surface(
        self, contact: FluidContactType, surf: xtgeo.RegularSurface
    ) -> ExportResultItem:
        """Export a fluid contact surface as a standard result"""
        edata = dio.ExportData(
            config=self._config,
            content=self._content,
            content_metadata={"contact": contact, "truncated": False},
            unit=self._unit,
            vertical_domain=VerticalDomain.depth.value,
            domain_reference=DomainReference.msl.value,
            subfolder=f"{self._subfolder}/{contact.value}",
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
        """Do the actual export using dataio setup."""
        result_items = []
        for contact, surfaces in self._contact_surfaces.items():
            for surf in surfaces:
                result_items.append(self._export_contact_surface(contact, surf))
        return ExportResult(items=result_items)

    def _validate_data_pre_export(self) -> None:
        """Data validations."""
        # TODO: Check that all contacts have positive values
        for contact, surfaces in self._contact_surfaces.items():
            for surf in surfaces:
                try:
                    validate_name_in_stratigraphy(surf.name, self._config)
                except ValidationError as err:
                    raise ValidationError(
                        f"Error detected for surface '{surf.name}' in the contact "
                        f"folder '{contact.value}'. Detailed information:\n{str(err)}"
                    ) from err


@experimental
def export_fluid_contact_surfaces(project: Any) -> ExportResult:
    """Simplified interface when exporting initial fluid contact surfaces from RMS.

    Args:
        project: The 'magic' project variable in RMS.
    Note:
        This function is experimental and may change in future versions.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_fluid_contact_surfaces

            export_results = export_fluid_contact_surfaces(project)

            for result in export_results.items:
                print(f"Output surfaces to {result.absolute_path}")

    """

    return _ExportFluidContactSurfaces(project).export()
