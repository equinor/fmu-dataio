"""Test the dataio running RMS specific utility function for field outline"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock
from unittest.mock import MagicMock

import jsonschema
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import xtgeo
from fmu.datamodels.standard_results import (
    SimulatorFipregionsMappingResult,
    SimulatorFipregionsMappingSchema,
)
from fmu.datamodels.standard_results.enums import StandardResultName
from pytest import MonkeyPatch

from fmu import dataio
from fmu.dataio._logging import null_logger

if TYPE_CHECKING:
    from fmu.dataio.export.rms.create_fipnum_property import _ExportFipZoneRegionMapping


logger = null_logger(__name__)


@pytest.fixture
def mapping_table() -> pa.Table:
    return pa.table(
        {
            "FIPNUM": [1, 2, 3, 4],
            "REGION": ["reg1", "reg2", "reg1", "reg2"],
            "ZONE": ["upper", "upper", "lower", "lower"],
        }
    )


@pytest.fixture
def region_property() -> xtgeo.GridProperty:
    prop = xtgeo.GridProperty(
        ncol=2,
        nrow=2,
        nlay=2,
        values=1,
        codes={1: "reg1", 2: "reg2"},
        discrete=True,
    )
    prop.values[1, :, :] = 2  # Set the second region to value 2
    return prop


@pytest.fixture
def zone_property() -> xtgeo.GridProperty:
    prop = xtgeo.GridProperty(
        ncol=2,
        nrow=2,
        nlay=2,
        values=1,
        codes={1: "upper", 2: "lower"},
        discrete=True,
    )
    prop.values[:, :, 1] = 2  # Set the second layer to value 2
    return prop


@pytest.fixture
def mock_export_class(
    monkeypatch: MonkeyPatch,
    rmssetup_with_fmuconfig: Path,
    mapping_table: pa.Table,
) -> Generator[_ExportFipZoneRegionMapping]:
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.create_fipnum_property import (
        _ExportFipZoneRegionMapping,
    )

    yield _ExportFipZoneRegionMapping(mapping_table)


@pytest.mark.usefixtures("inside_rms_interactive")
def test_create_fipnum_from_region_and_zone(
    zone_property: xtgeo.GridProperty,
    region_property: xtgeo.GridProperty,
    mapping_table: pa.Table,
) -> None:
    """Test that the FIPNUM property is created with correct values and mapping."""

    from fmu.dataio.export.rms.create_fipnum_property import (
        _create_fipnum_from_region_and_zone,
    )

    expected_mapping_table = mapping_table

    fipnum, mapping_table = _create_fipnum_from_region_and_zone(
        zone_property, region_property
    )

    expected_fipnum_values = np.array([[[1, 3], [1, 3]], [[2, 4], [2, 4]]])
    assert np.array_equal(fipnum.values, expected_fipnum_values)

    assert mapping_table == expected_mapping_table

    # check that codenames are set on the fipnum property
    assert fipnum.codes == {
        1: "reg1_upper",
        2: "reg2_upper",
        3: "reg1_lower",
        4: "reg2_lower",
    }


@pytest.mark.usefixtures("inside_rms_interactive")
def test_create_fipnum_from_region_and_zone_with_non_sequential_region_numbers(
    zone_property: xtgeo.GridProperty, mapping_table: pa.Table
) -> None:
    """
    Test the FIPNUM property is correctly created for a region with non-sequential
    region numbers.
    """

    from fmu.dataio.export.rms.create_fipnum_property import (
        _create_fipnum_from_region_and_zone,
    )

    region_property = xtgeo.GridProperty(
        ncol=2,
        nrow=2,
        nlay=2,
        values=1,
        codes={1: "reg1", 10: "reg2"},
        discrete=True,
    )
    region_property.values[1, :, :] = 10  # Set the second region to value 10

    expected_mapping_table = mapping_table

    fipnum, mapping_table = _create_fipnum_from_region_and_zone(
        zone_property, region_property
    )

    expected_fipnum_values = np.array([[[1, 3], [1, 3]], [[2, 4], [2, 4]]])
    assert np.array_equal(fipnum.values, expected_fipnum_values)

    assert mapping_table == expected_mapping_table


def test_load_discrete_gridproperty_raises_on_continuous_property(
    mock_project_variable: MagicMock, region_property: xtgeo.GridProperty
) -> None:
    """Test that an exception is raised if the region/zone property is not discrete."""

    from fmu.dataio.export.rms.create_fipnum_property import (
        _load_discrete_gridproperty,
    )

    continuous_property = region_property.copy()
    continuous_property.discrete_to_continuous()

    with (
        mock.patch(
            "fmu.dataio.export.rms.create_fipnum_property.xtgeo.gridproperty_from_roxar",
            return_value=continuous_property,
        ),
        pytest.raises(ValueError, match="must be discrete"),
    ):
        _load_discrete_gridproperty(mock_project_variable, "Simgrid", "Region")


def test_create_fipnum_in_project(
    mock_project_variable: MagicMock,
    zone_property: xtgeo.GridProperty,
    region_property: xtgeo.GridProperty,
    mapping_table: pa.Table,
) -> None:
    """Test that the to_roxar method is called with correct arguments."""

    from fmu.dataio.export.rms.create_fipnum_property import _create_fipnum_in_project

    expected_mapping_table = mapping_table

    with (
        mock.patch(
            "fmu.dataio.export.rms.create_fipnum_property.xtgeo.gridproperty_from_roxar",
            side_effect=[region_property, zone_property],
        ),
        mock.patch(
            "fmu.dataio.export.rms.create_fipnum_property.xtgeo.GridProperty.to_roxar"
        ) as mock_to_roxar,
    ):
        mapping_table = _create_fipnum_in_project(
            mock_project_variable, "Simgrid", "Region", "Zone"
        )
        mock_to_roxar.assert_called_once_with(
            mock_project_variable, "Simgrid", "FIPNUM"
        )

        assert mapping_table == expected_mapping_table


@pytest.mark.usefixtures("inside_rms_interactive")
def test_mapping_file_is_exported_with_metadata(
    mock_export_class: _ExportFipZoneRegionMapping,
    rmssetup_with_fmuconfig: Path,
) -> None:
    """Test that the mapping is exported to disk with metadata"""
    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig
        / "../../share/results/tables/simulator_fipregions_mapping"
    )
    assert export_folder.exists()

    assert (export_folder / "fipnum.parquet").exists()
    assert (export_folder / ".fipnum.parquet.yml").exists()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_standard_result_in_metadata(
    mock_export_class: _ExportFipZoneRegionMapping,
) -> None:
    """Test that the standard_result is set correctly in the metadata"""

    out = mock_export_class.export()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.simulator_fipregions_mapping
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["version"]
        == SimulatorFipregionsMappingSchema.VERSION
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["url"]
        == SimulatorFipregionsMappingSchema.url()
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_public_export_function(
    mock_project_variable: MagicMock,
    mock_export_class: _ExportFipZoneRegionMapping,
    mapping_table: pa.Table,
) -> None:
    """Test that the export function works and metadata is correctly set"""

    from fmu.dataio.export.rms import create_fipnum_property

    with (
        mock.patch(
            "fmu.dataio.export.rms.create_fipnum_property._create_fipnum_in_project",
            return_value=mapping_table,
        ),
    ):
        out = create_fipnum_property(mock_project_variable, "Simgrid", "Region", "Zone")

        assert len(out.items) == 1

        metadata = dataio.read_metadata(out.items[0].absolute_path)

        assert metadata["data"]["content"] == "mapping"
        assert metadata["access"]["classification"] == "internal"
        assert (
            metadata["data"]["standard_result"]["name"]
            == StandardResultName.simulator_fipregions_mapping
        )
        assert metadata["data"]["format"] == "parquet"
        assert metadata["data"]["table_index"] == ["FIPNUM", "ZONE", "REGION"]


@pytest.mark.usefixtures("inside_rms_interactive")
def test_config_missing(
    mock_project_variable: MagicMock,
    # mock_export_class: _ExportFipZoneRegionMapping,
    mapping_table: pa.Table,
    rmssetup_with_fmuconfig: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import create_fipnum_property

    # move up one directory to trigger not finding the config
    monkeypatch.chdir(rmssetup_with_fmuconfig.parent)

    with (
        mock.patch(
            "fmu.dataio.export.rms.create_fipnum_property._create_fipnum_in_project",
            return_value=mapping_table,
        ),
        pytest.raises(FileNotFoundError, match="Could not detect"),
    ):
        create_fipnum_property(mock_project_variable, "Simgrid", "Region", "Zone")


@pytest.mark.usefixtures("inside_rms_interactive")
def test_payload_validates_against_model(
    mock_export_class: _ExportFipZoneRegionMapping,
) -> None:
    """Tests that the table exported is validated against the payload result
    model."""

    out = mock_export_class.export()
    df = (
        pq.read_table(out.items[0].absolute_path)
        .to_pandas()
        .replace(np.nan, None)
        .to_dict(orient="records")
    )
    SimulatorFipregionsMappingResult.model_validate(df)  # Throws if invalid


@pytest.mark.usefixtures("inside_rms_interactive")
def test_payload_validates_against_schema(
    mock_export_class: _ExportFipZoneRegionMapping,
) -> None:
    """Tests that the table exported is validated against the payload result
    schema."""

    out = mock_export_class.export()
    df = (
        pq.read_table(out.items[0].absolute_path)
        .to_pandas()
        .replace(np.nan, None)
        .to_dict(orient="records")
    )
    jsonschema.validate(
        instance=df, schema=SimulatorFipregionsMappingSchema.dump()
    )  # Throws if invalid
