"""Test the dataio running RMS spesici utility function for volumetrics"""

from pathlib import Path
from unittest import mock

import jsonschema
import numpy as np
import pyarrow.parquet as pq
import pytest

from fmu import dataio
from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.enums import StandardResultName
from fmu.dataio._models.standard_results.structure_depth_fault_lines import (
    StructureDepthFaultLinesResult,
    StructureDepthFaultLinesSchema,
)
from tests.utils import inside_rms

logger = null_logger(__name__)


@pytest.fixture
def mock_export_class(
    mock_project_variable,
    monkeypatch,
    rmssetup_with_fmuconfig,
    xtgeo_fault_lines,
):
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.structure_depth_fault_lines import (
        _ExportStructureDepthFaultLines,
    )

    with mock.patch(
        "fmu.dataio.export.rms.structure_depth_fault_lines.get_polygons_in_folder",
        return_value=xtgeo_fault_lines,
    ):
        yield _ExportStructureDepthFaultLines(mock_project_variable, "geogrid_vol")


@inside_rms
def test_files_exported_with_metadata(mock_export_class, rmssetup_with_fmuconfig):
    """Test that the standard_result is set correctly in the metadata"""

    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig
        / "../../share/results/polygons/structure_depth_fault_lines"
    )
    assert export_folder.exists()

    assert (export_folder / "topvolantis.parquet").exists()
    assert (export_folder / "toptherys.parquet").exists()
    assert (export_folder / "topvolon.parquet").exists()

    assert (export_folder / ".topvolantis.parquet.yml").exists()
    assert (export_folder / ".toptherys.parquet.yml").exists()
    assert (export_folder / ".topvolon.parquet.yml").exists()


@inside_rms
def test_standard_result_in_metadata(mock_export_class):
    """Test that the standard_result is set correctly in the metadata"""

    out = mock_export_class.export()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.structure_depth_fault_lines
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["version"]
        == StructureDepthFaultLinesSchema.VERSION
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["url"]
        == StructureDepthFaultLinesSchema.url()
    )


@inside_rms
def test_public_export_function(mock_project_variable, mock_export_class):
    """Test that the export function works"""

    from fmu.dataio.export.rms import export_structure_depth_fault_lines

    out = export_structure_depth_fault_lines(mock_project_variable, "DS_extract")

    assert len(out.items) == 3

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "fault_lines" in metadata["data"]["content"]
    assert metadata["access"]["classification"] == "internal"
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.structure_depth_fault_lines
    )
    assert metadata["data"]["format"] == "parquet"


@inside_rms
def test_config_missing(mock_project_variable, rmssetup_with_fmuconfig, monkeypatch):
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_structure_depth_fault_lines
    from fmu.dataio.export.rms._utils import CONFIG_PATH

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    config_path_modified = Path("wrong.yml")

    CONFIG_PATH.rename(config_path_modified)

    with pytest.raises(FileNotFoundError, match="Could not detect"):
        export_structure_depth_fault_lines(mock_project_variable, "DS_extract")

    # restore the global config file for later tests
    config_path_modified.rename(CONFIG_PATH)


@inside_rms
def test_payload_validates_against_model(
    mock_export_class,
):
    """Tests that the volume table exported is validated against the payload result
    model."""

    out = mock_export_class._export_fault_lines()
    df = (
        pq.read_table(out.items[0].absolute_path)
        .to_pandas()
        .replace(np.nan, None)
        .to_dict(orient="records")
    )
    StructureDepthFaultLinesResult.model_validate(df)  # Throws if invalid


@inside_rms
def test_payload_validates_against_schema(
    mock_export_class,
):
    """Tests that the volume table exported is validated against the payload result
    schema."""

    out = mock_export_class._export_fault_lines()
    df = (
        pq.read_table(out.items[0].absolute_path)
        .to_pandas()
        .replace(np.nan, None)
        .to_dict(orient="records")
    )
    jsonschema.validate(
        instance=df, schema=StructureDepthFaultLinesSchema.dump()
    )  # Throws if invalid
