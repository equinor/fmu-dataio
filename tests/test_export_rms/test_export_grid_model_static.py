"""Test the dataio running RMS specific utility function for field outline"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock
from unittest.mock import MagicMock

import numpy as np
import pytest
from fmu.datamodels.fmu_results.attribute_specification import AnyAttributeSpecification
from fmu.datamodels.fmu_results.enums import PropertyAttribute
from fmu.datamodels.standard_results.enums import StandardResultName
from pytest import MonkeyPatch

from fmu import dataio
from fmu.dataio._logging import null_logger

if TYPE_CHECKING:
    import xtgeo

    from fmu.dataio.export.rms.grid_model_static import (
        _ExportGridModelStatic,
        _PropertySpecifications,
    )


logger = null_logger(__name__)


@pytest.fixture
def property_specifications(mock_rmsapi):
    from fmu.dataio.export.rms.grid_model_static import _PropertySpecifications

    return _PropertySpecifications(
        zonation="Zone",
        regions="Regions",
        porosity="PHIT",
        permeability="KLOGH",
        saturation_water="SW",
        fluid_indicator="Discrete_fluid",
        bulk_volume_oil="Oil_bulk",
        bulk_volume_gas="Gas_bulk",
    )


@pytest.fixture
def mock_export_class(
    mock_project_variable: MagicMock,
    monkeypatch: MonkeyPatch,
    rmssetup_with_fmuconfig: Path,
    property_specifications: _PropertySpecifications,
    xtgeo_grid: xtgeo.Grid,
    xtgeo_discrete_property: xtgeo.GridProperty,
    xtgeo_continuous_property: xtgeo.GridProperty,
) -> Generator[_ExportGridModelStatic]:
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.grid_model_static import _ExportGridModelStatic

    with (
        mock.patch(
            "fmu.dataio.export.rms.grid_model_static.xtgeo.grid_from_roxar",
            return_value=xtgeo_grid,
        ),
        mock.patch(
            "fmu.dataio.export.rms.grid_model_static.xtgeo.gridproperty_from_roxar"
        ) as mock_prop,
    ):

        def side_effect_property(_project, _gridname, propname):
            if property_specifications.to_dict()[propname].is_discrete:
                prop = xtgeo_discrete_property
            else:
                prop = xtgeo_continuous_property
            prop.name = propname
            return prop

        mock_prop.side_effect = side_effect_property

        yield _ExportGridModelStatic(
            mock_project_variable, "Geogrid", property_specifications
        )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_files_exported_with_metadata(
    mock_export_class: _ExportGridModelStatic,
    rmssetup_with_fmuconfig: Path,
) -> None:
    """Test that the standard_result is set correctly in the metadata"""

    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig / "../../share/results/grids/grid_model_static"
    )
    assert export_folder.exists()

    assert (export_folder / "geogrid.roff").exists()
    assert (export_folder / "geogrid--zone.roff").exists()
    assert (export_folder / "geogrid--regions.roff").exists()
    assert (export_folder / "geogrid--phit.roff").exists()
    assert (export_folder / "geogrid--klogh.roff").exists()
    assert (export_folder / "geogrid--sw.roff").exists()
    assert (export_folder / "geogrid--discrete_fluid.roff").exists()
    assert (export_folder / "geogrid--oil_bulk.roff").exists()
    assert (export_folder / "geogrid--gas_bulk.roff").exists()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_public_export_function(
    mock_project_variable: MagicMock,
    mock_export_class: _ExportGridModelStatic,
) -> None:
    """Test that the export function works"""

    from fmu.dataio.export.rms import export_grid_model_static

    out = export_grid_model_static(
        mock_project_variable,
        gridname="Geogrid",
        zonation="Zone",
        regions="Regions",
        porosity="PHIT",
        permeability="KLOGH",
        saturation_water="SW",
    )

    assert len(out.items) == 9

    # first item should be the grid geometry
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert metadata["class"] == "cpgrid"
    assert metadata["data"]["content"] == "depth"
    assert metadata["access"]["classification"] == "internal"
    assert metadata["data"]["format"] == "roff"
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.grid_model_static
    )

    # second item should be a grid property
    metadata = dataio.read_metadata(out.items[1].absolute_path)

    assert metadata["class"] == "cpgrid_property"
    assert metadata["data"]["content"] == "property"
    assert "property" in metadata["data"]
    assert metadata["access"]["classification"] == "internal"
    assert metadata["data"]["format"] == "roff"
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.grid_model_static
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_config_missing(
    mock_project_variable: MagicMock,
    rmssetup_with_fmuconfig: Path,
    monkeypatch: MonkeyPatch,
    mock_export_class: _ExportGridModelStatic,
) -> None:
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_grid_model_static

    # move up one directory to trigger not finding the config
    monkeypatch.chdir(rmssetup_with_fmuconfig.parent)

    with pytest.raises(FileNotFoundError, match="Could not detect"):
        export_grid_model_static(
            mock_project_variable,
            gridname="Geogrid",
            zonation="Zone",
            regions="Regions",
            porosity="PHIT",
            permeability="KLOGH",
            saturation_water="SW",
        )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_duplicate_input_raises(
    mock_project_variable: MagicMock,
    rmssetup_with_fmuconfig: Path,
    monkeypatch: MonkeyPatch,
    mock_export_class: _ExportGridModelStatic,
) -> None:
    """
    Test that an exception is raised if a the same property name is input for more
    than one argument.
    """

    from fmu.dataio.export.rms import export_grid_model_static

    # move up one directory to trigger not finding the config
    monkeypatch.chdir(rmssetup_with_fmuconfig.parent)

    with pytest.raises(
        ValueError, match="Property name 'Zone' was input more than once"
    ):
        export_grid_model_static(
            mock_project_variable,
            gridname="Geogrid",
            zonation="Zone",
            regions="Zone",  # duplicate property name
            porosity="PHIT",
            permeability="KLOGH",
            saturation_water="SW",
        )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_property_not_found_in_rms(mock_project_variable: MagicMock) -> None:
    """Test that an error is raised if the property is not found in RMS."""

    from fmu.dataio.export.rms.grid_model_static import (
        _ExportGridModelStatic,
        _PropertySpecifications,
    )

    properties = _PropertySpecifications(zonation="Zone_do_not_exist")

    with pytest.raises(
        ValueError, match="Property 'Zone_do_not_exist' was not found in the grid."
    ):
        _ExportGridModelStatic(mock_project_variable, "Geogrid", properties)


@pytest.mark.usefixtures("inside_rms_interactive")
def test_oil_and_gas_bulk_missing(
    mock_project_variable: MagicMock, property_specifications: _PropertySpecifications
) -> None:
    """Test that an error is raised if both oil and gas bulk properties are missing."""

    from fmu.dataio.export.rms.grid_model_static import _ExportGridModelStatic

    del mock_project_variable.grid_models["Geogrid"].properties["Oil_bulk"]
    del mock_project_variable.grid_models["Geogrid"].properties["Gas_bulk"]

    with pytest.raises(
        ValueError, match="One of 'Oil_bulk' or 'Gas_bulk' must be present in the grid."
    ):
        _ExportGridModelStatic(
            mock_project_variable, "Geogrid", property_specifications
        )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_one_of_oil_and_gas_bulk_missing_works(
    mock_project_variable: MagicMock, property_specifications: _PropertySpecifications
) -> None:
    """Test that no error is raised if one of 'Oil_bulk' or 'Gas_bulk' is present."""

    from fmu.dataio.export.rms.grid_model_static import _ExportGridModelStatic

    del mock_project_variable.grid_models["Geogrid"].properties["Oil_bulk"]

    # should work
    _ExportGridModelStatic(mock_project_variable, "Geogrid", property_specifications)


@pytest.mark.usefixtures("inside_rms_interactive")
def test_fluid_indicator_property_is_required(
    mock_project_variable: MagicMock, property_specifications: _PropertySpecifications
) -> None:
    """Test that an error is raised if the 'Discrete_fluid' property is missing."""

    from fmu.dataio.export.rms.grid_model_static import _ExportGridModelStatic

    del mock_project_variable.grid_models["Geogrid"].properties["Discrete_fluid"]

    with pytest.raises(
        ValueError, match="A 'Discrete_fluid' property must be present in the grid."
    ):
        _ExportGridModelStatic(
            mock_project_variable, "Geogrid", property_specifications
        )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_property_value_outside_specification_raises(
    mock_export_class: _ExportGridModelStatic,
) -> None:
    """Test that an error is raised if a property value is outside specification."""

    from fmu.dataio.export.rms.grid_model_static import _ExportStaticGridProperties

    prop = MagicMock()
    prop.isdiscrete = False
    prop.values = np.array([0, 1.2])  # porosity should be between 0 and 1

    prop_spec = AnyAttributeSpecification.model_validate(
        {"attribute": PropertyAttribute.porosity}
    ).root

    with pytest.raises(ValueError, match="has maximum value .* greater than"):
        _ExportStaticGridProperties(
            prop=prop,
            prop_spec=prop_spec,
            geometry=Path("geogrid.roff"),
        ).export()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_property_type_mismatch_raises(
    mock_export_class: _ExportGridModelStatic,
) -> None:
    """
    Test that an error is raised if a property is of a different type
    than specification.
    """

    from fmu.dataio.export.rms.grid_model_static import _ExportStaticGridProperties

    prop = MagicMock()
    prop.isdiscrete = True  # this should be False for porosity
    prop.values = np.array([0, 1])

    prop_spec = AnyAttributeSpecification.model_validate(
        {"attribute": PropertyAttribute.porosity}
    ).root

    with pytest.raises(ValueError, match="needs to be of type continuous"):
        _ExportStaticGridProperties(
            prop=prop,
            prop_spec=prop_spec,
            geometry=Path("geogrid.roff"),
        ).export()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_property_specification_fields_in_attribute_specification() -> None:
    """
    Ensure all property specification fields are present as property attributes and
    in the attribute specification.
    """

    from fmu.dataio.export.rms.grid_model_static import _PropertySpecifications

    for field in _PropertySpecifications.model_fields:
        assert field in PropertyAttribute.__members__

        AnyAttributeSpecification.model_validate(
            {"attribute": PropertyAttribute[field]}
        )
