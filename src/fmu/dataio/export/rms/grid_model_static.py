from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import xtgeo
from pydantic import BaseModel

from fmu.dataio._export import export_with_metadata
from fmu.dataio._export_config import ExportConfig
from fmu.dataio._logging import null_logger
from fmu.dataio.export._base import SimpleExportBase
from fmu.dataio.export._export_result import ExportResult, ExportResultItem
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.attribute_specification import (
    AnyAttributeSpecification,
    AttributeSpecification,
)
from fmu.datamodels.fmu_results.data import Property
from fmu.datamodels.fmu_results.enums import (
    Content,
    DomainReference,
    PropertyAttribute,
    VerticalDomain,
)
from fmu.datamodels.standard_results.enums import StandardResultName

_logger: Final = null_logger(__name__)

BULK_VOLUME_OIL: Final = "Oil_bulk"
BULK_VOLUME_GAS: Final = "Gas_bulk"
FLUID_INDICATOR: Final = "Discrete_fluid"


class _PropertySpecifications(BaseModel):
    zonation: str | None = None
    regions: str | None = None
    porosity: str | None = None
    permeability: str | None = None
    saturation_water: str | None = None
    fluid_indicator: str | None = None
    bulk_volume_oil: str | None = None
    bulk_volume_gas: str | None = None
    facies: str | None = None
    net_to_gross: str | None = None
    volume_shale: str | None = None
    permeability_vertical: str | None = None

    def to_dict(self) -> dict[str, AttributeSpecification]:
        """Convert to property specifications dictionary."""
        properties: dict[str, AttributeSpecification] = {}

        for field, prop_name in self.model_dump(exclude_none=True).items():
            if prop_name in properties:
                raise ValueError(
                    f"Property name '{prop_name}' was input more than once, "
                    "this is not allowed."
                )

            properties[prop_name] = AnyAttributeSpecification.model_validate(
                {"attribute": PropertyAttribute[field]}
            ).root

        return properties


class _ExportStaticGrid(SimpleExportBase):
    def __init__(self, grid: xtgeo.Grid) -> None:
        super().__init__()

        self.grid = grid

    def _get_export_config(self) -> ExportConfig:
        """Export config for the standard result."""
        return (
            ExportConfig.builder()
            .content(Content.depth)
            .domain(VerticalDomain.depth, DomainReference.msl)
            .file_config(
                subfolder=StandardResultName.grid_model_static.value,
            )
            .access(Classification.internal, rep_include=False)
            .global_config(self._config)
            .standard_result(StandardResultName.grid_model_static)
            .build()
        )

    def _export_data_as_standard_result(self) -> ExportResult:
        """Export the grid as a standard result."""

        export_config = self._get_export_config()
        export_path = export_with_metadata(export_config, self.grid)
        _logger.debug("Grid exported to: %s", export_path)

        return ExportResult(items=[ExportResultItem(absolute_path=export_path)])

    def _validate_data_pre_export(self) -> None:
        """Data validations before export."""


class _ExportStaticGridProperties(SimpleExportBase):
    def __init__(
        self,
        prop: xtgeo.GridProperty,
        prop_spec: AttributeSpecification,
        geometry: Path,
    ) -> None:
        super().__init__()

        self.prop = prop
        self.prop_spec = prop_spec
        self.geometry = geometry

    def _get_export_config(self) -> ExportConfig:
        """Export config for the standard result."""
        return (
            ExportConfig.builder()
            .content(
                Content.property,
                Property(attribute=self.prop_spec.attribute),
            )
            .domain(VerticalDomain.depth, DomainReference.msl)
            .file_config(
                geometry=str(self.geometry),
                subfolder=StandardResultName.grid_model_static.value,
            )
            .access(Classification.internal, rep_include=False)
            .global_config(self._config)
            .standard_result(StandardResultName.grid_model_static)
            .build()
        )

    def _export_data_as_standard_result(self) -> ExportResult:
        """Export the grid properties as a standard result."""

        export_config = self._get_export_config()
        export_path = export_with_metadata(export_config, self.prop)
        _logger.debug("Grid property exported to: %s", export_path)

        return ExportResult(items=[ExportResultItem(absolute_path=export_path)])

    def _validate_data_pre_export(self) -> None:
        """Validate a single property against its specification."""

        if self.prop.isdiscrete != self.prop_spec.is_discrete:
            expected_type = "discrete" if self.prop_spec.is_discrete else "continuous"
            raise ValueError(
                f"Property input as '{self.prop_spec.attribute}' needs to be "
                f"of type {expected_type}."
            )

        min_value = self.prop.values.min()
        max_value = self.prop.values.max()

        if self.prop_spec.min_value and (min_value < self.prop_spec.min_value):
            raise ValueError(
                f"Property '{self.prop.name}' has minimum value {min_value} which is "
                f"less than the expected minimum of {self.prop_spec.min_value}."
            )

        if self.prop_spec.max_value and (max_value > self.prop_spec.max_value):
            raise ValueError(
                f"Property '{self.prop.name}' has maximum value {max_value} which is "
                f"greater than the expected maximum of {self.prop_spec.max_value}."
            )


class _ExportGridModelStatic:
    def __init__(
        self,
        project: Any,
        gridname: str,
        properties: _PropertySpecifications,
    ) -> None:

        self.project = project
        self.gridname = gridname
        self.properties = self._prepare_and_validate_properties(properties.to_dict())

    @property
    def available_properties(self) -> list[str]:
        """Get a list of available property names in the grid."""
        return self.project.grid_models[self.gridname].properties

    def _assert_property_available(self, prop_name: str) -> None:
        """Raise if a requested property is not available in the grid."""
        if prop_name not in self.available_properties:
            if prop_name == FLUID_INDICATOR:
                raise ValueError(
                    f"A '{FLUID_INDICATOR}' property must be present in the grid. "
                    "Tip, it can easily be output through the volumetrics job."
                )
            raise ValueError(f"Property '{prop_name}' was not found in the grid.")

    def _prepare_and_validate_properties(
        self, properties: dict[str, AttributeSpecification]
    ) -> dict[str, AttributeSpecification]:
        """Prepare bulk properties and validate that requested properties exist."""

        has_oil_bulk = BULK_VOLUME_OIL in self.available_properties
        has_gas_bulk = BULK_VOLUME_GAS in self.available_properties

        if not has_oil_bulk and not has_gas_bulk:
            raise ValueError(
                f"One of '{BULK_VOLUME_OIL}' or '{BULK_VOLUME_GAS}' must be "
                "present in the grid."
            )

        if not has_oil_bulk:
            properties.pop(BULK_VOLUME_OIL)

        if not has_gas_bulk:
            properties.pop(BULK_VOLUME_GAS)

        for prop_name in properties:
            self._assert_property_available(prop_name)

        return properties

    def load_grid(self) -> xtgeo.Grid:
        """Load the grid from RMS."""
        return xtgeo.grid_from_roxar(self.project, self.gridname)

    def load_property(self, name: str) -> xtgeo.GridProperty:
        """Load a grid property from RMS."""
        return xtgeo.gridproperty_from_roxar(self.project, self.gridname, name)

    def export(self) -> ExportResult:
        exported_items = []

        grid = self.load_grid()

        export_result_grid = _ExportStaticGrid(grid).export()
        geometry_path = export_result_grid.items[0].absolute_path
        exported_items.extend(export_result_grid.items)

        for name, prop_spec in self.properties.items():
            prop = self.load_property(name)

            export_result_prop = _ExportStaticGridProperties(
                prop=prop,
                prop_spec=prop_spec,
                geometry=geometry_path,
            ).export()

            exported_items.extend(export_result_prop.items)

        return ExportResult(items=exported_items)


def export_grid_model_static(
    project: Any,
    gridname: str,
    zonation: str,
    regions: str,
    porosity: str,
    permeability: str,
    saturation_water: str,
    facies: str | None = None,
    net_to_gross: str | None = None,
    volume_shale: str | None = None,
    permeability_vertical: str | None = None,
) -> ExportResult:
    """Simplified interface when exporting a grid model with common properties from RMS.

    Args:
        project: The 'magic' project variable in RMS.
        gridname: Name of the grid model.
        zonation: Name of the zone property.
        regions: Name of the regions property.
        porosity: Name of the porosity property.
        permeability: Name of the permeability property.
        saturation_water: Name of the water saturation property.
        facies: Name of the facies property.
        net_to_gross: Name of the net to gross property.
        volume_shale: Name of the volume shale property.
        permeability_vertical: Name of the vertical permeability property.

    Examples:
        Example usage in an RMS script::

            from fmu.dataio.export.rms import export_grid_model_static

            export_results = export_grid_model_static(
                project,
                gridname="Geogrid",
                zonation="Zone",
                regions="Region",
                porosity="PHIT",
                permeability="KLOGH",
                saturation_water="SW",
                facies="FACIES",
                )

            for result in export_results.items:
                print(f"Exported item to {result.absolute_path}")

    """

    properties = _PropertySpecifications(
        zonation=zonation,
        regions=regions,
        facies=facies,
        porosity=porosity,
        permeability=permeability,
        saturation_water=saturation_water,
        bulk_volume_gas=BULK_VOLUME_GAS,
        bulk_volume_oil=BULK_VOLUME_OIL,
        fluid_indicator=FLUID_INDICATOR,
        permeability_vertical=permeability_vertical,
        net_to_gross=net_to_gross,
        volume_shale=volume_shale,
    )

    return _ExportGridModelStatic(project, gridname, properties).export()
