"""Test the dataio running RMS specific utility function for simulator layer mapping"""

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
    SimulatorZoneLayerMappingResult,
    SimulatorZoneLayerMappingSchema,
    StandardResultName,
)
from fmu.datamodels.standard_results.simulator_zone_layer_mapping import (
    SimulatorZoneLayerMappingResultRow,
)
from pydantic import ValidationError
from pytest import MonkeyPatch

from fmu import dataio

if TYPE_CHECKING:
    from fmu.dataio.export.rms.simulator_zone_layer_mapping import (
        _ExportZoneLayerMapping,
    )


@pytest.fixture
def mapping_table() -> pa.Table:
    return pa.table(
        {
            "LAYER": [1, 2, 3, 4],
            "ZONE": ["upper", "upper", "lower", "lower"],
        }
    )


@pytest.fixture
def mock_export_class(
    monkeypatch: MonkeyPatch,
    rmssetup_with_fmuconfig: Path,
    mapping_table: pa.Table,
) -> Generator[_ExportZoneLayerMapping]:
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.simulator_zone_layer_mapping import (
        _ExportZoneLayerMapping,
    )

    yield _ExportZoneLayerMapping(mapping_table)


def test_create_zone_layer_mapping_table_from_grid_object() -> None:
    """Test creating a mapping table from a loaded xtgeo grid object."""

    from fmu.dataio.export.rms.simulator_zone_layer_mapping import (
        _create_zone_layer_mapping_table,
    )

    grid = xtgeo.create_box_grid((2, 2, 4))
    grid.set_subgrids({"upper": 1, "lower": 3})

    mapping_table = _create_zone_layer_mapping_table(grid)

    assert mapping_table.to_pylist() == [
        {"LAYER": 1, "ZONE": "upper"},
        {"LAYER": 2, "ZONE": "lower"},
        {"LAYER": 3, "ZONE": "lower"},
        {"LAYER": 4, "ZONE": "lower"},
    ]


def test_create_zone_layer_mapping_table_with_inactive_layer() -> None:
    """Test mapping table contains all layers even when there are inactive layers."""

    from fmu.dataio.export.rms.simulator_zone_layer_mapping import (
        _create_zone_layer_mapping_table,
    )

    grid = xtgeo.create_box_grid((2, 2, 4))
    grid.set_subgrids({"upper": 1, "lower": 3})

    # set layer 2 as inactive
    actnum = grid.get_actnum()
    actnum.values[:, :, 1] = 0
    grid.set_actnum(actnum)

    mapping_table = _create_zone_layer_mapping_table(grid)

    assert mapping_table.to_pylist() == [
        {"LAYER": 1, "ZONE": "upper"},
        {"LAYER": 2, "ZONE": "lower"},
        {"LAYER": 3, "ZONE": "lower"},
        {"LAYER": 4, "ZONE": "lower"},
    ]


def test_extract_zone_layer_mapping_from_grid_calls_dependencies() -> None:
    """Test that extracting mappings from a grid calls dependencies as expected."""

    from fmu.dataio.export.rms.simulator_zone_layer_mapping import (
        _extract_zone_layer_mapping_from_grid,
    )

    mock_project = MagicMock()
    mock_grid = MagicMock()
    expected_table = MagicMock(spec=pa.Table)

    with (
        mock.patch(
            "fmu.dataio.export.rms.simulator_zone_layer_mapping.xtgeo.grid_from_roxar",
            return_value=mock_grid,
        ) as mock_grid_from_roxar,
        mock.patch(
            "fmu.dataio.export.rms.simulator_zone_layer_mapping._create_zone_layer_mapping_table",
            return_value=expected_table,
        ) as mock_create_table,
    ):
        result = _extract_zone_layer_mapping_from_grid(mock_project, "Simgrid")

    mock_grid_from_roxar.assert_called_once_with(mock_project, "Simgrid")
    mock_create_table.assert_called_once_with(mock_grid)
    assert result is expected_table


@pytest.mark.usefixtures("inside_rms_interactive")
def test_mapping_file_is_exported_with_metadata(
    mock_export_class: _ExportZoneLayerMapping,
    rmssetup_with_fmuconfig: Path,
) -> None:
    """Test that the layer mapping is exported to disk with metadata."""

    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig
        / "../../share/results/tables/simulator_zone_layer_mapping"
    )
    assert export_folder.exists()

    assert (export_folder / "simulator_zone_layer_mapping.parquet").exists()
    assert (export_folder / ".simulator_zone_layer_mapping.parquet.yml").exists()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_standard_result_in_metadata(
    mock_export_class: _ExportZoneLayerMapping,
) -> None:
    """Test that the standard_result is set correctly in the metadata."""

    out = mock_export_class.export()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.simulator_zone_layer_mapping
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["version"]
        == SimulatorZoneLayerMappingSchema.VERSION
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["url"]
        == SimulatorZoneLayerMappingSchema.url()
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_public_export_function(
    mock_project_variable: MagicMock,
    mapping_table: pa.Table,
    mock_export_class: _ExportZoneLayerMapping,
) -> None:
    """Test that the public export function works and metadata is set."""

    from fmu.dataio.export.rms.simulator_zone_layer_mapping import (
        export_simulator_zone_layer_mapping,
    )

    with mock.patch(
        "fmu.dataio.export.rms.simulator_zone_layer_mapping._extract_zone_layer_mapping_from_grid",
        return_value=mapping_table,
    ) as mock_extract_zone_layer:
        out = export_simulator_zone_layer_mapping(mock_project_variable, "Simgrid")

    mock_extract_zone_layer.assert_called_with(mock_project_variable, "Simgrid")

    assert len(out.items) == 1

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert metadata["data"]["content"] == "mapping"
    assert metadata["access"]["classification"] == "internal"
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.simulator_zone_layer_mapping
    )
    assert metadata["data"]["format"] == "parquet"
    assert metadata["data"]["table_index"] == list(
        SimulatorZoneLayerMappingResultRow.model_fields
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_config_missing(
    mock_project_variable: MagicMock,
    mapping_table: pa.Table,
    rmssetup_with_fmuconfig: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms.simulator_zone_layer_mapping import (
        export_simulator_zone_layer_mapping,
    )

    # move up one directory to trigger not finding the config
    monkeypatch.chdir(rmssetup_with_fmuconfig.parent)

    with (
        mock.patch(
            "fmu.dataio.export.rms.simulator_zone_layer_mapping._extract_zone_layer_mapping_from_grid",
            return_value=mapping_table,
        ),
        pytest.raises(FileNotFoundError, match="Could not find"),
    ):
        export_simulator_zone_layer_mapping(mock_project_variable, "Simgrid")


@pytest.mark.usefixtures("inside_rms_interactive")
def test_payload_validates_against_model(
    mock_export_class: _ExportZoneLayerMapping,
) -> None:
    """Tests that the table exported is validated against the payload result model."""

    out = mock_export_class.export()
    df = (
        pq.read_table(out.items[0].absolute_path)
        .to_pandas()
        .replace(np.nan, None)
        .to_dict(orient="records")
    )
    SimulatorZoneLayerMappingResult.model_validate(df)  # Throws if invalid


@pytest.mark.usefixtures("inside_rms_interactive")
def test_payload_validates_against_schema(
    mock_export_class: _ExportZoneLayerMapping,
) -> None:
    """Tests that the table exported is validated against the payload result schema."""

    out = mock_export_class.export()
    df = (
        pq.read_table(out.items[0].absolute_path)
        .to_pandas()
        .replace(np.nan, None)
        .to_dict(orient="records")
    )
    jsonschema.validate(
        instance=df, schema=SimulatorZoneLayerMappingSchema.dump()
    )  # Throws if invalid


def test_payload_model_validation_raises_for_invalid_payload() -> None:
    """Tests that payload model validation raises for invalid table rows."""

    invalid_payload = [{"LAYER": "invalid", "ZONE": 1}]

    with pytest.raises(ValidationError):
        SimulatorZoneLayerMappingResult.model_validate(invalid_payload)


def test_payload_schema_validation_raises_for_invalid_payload() -> None:
    """Tests that payload schema validation raises for invalid table rows."""

    invalid_payload = [{"LAYER": "invalid", "ZONE": 1}]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance=invalid_payload,
            schema=SimulatorZoneLayerMappingSchema.dump(),
        )
