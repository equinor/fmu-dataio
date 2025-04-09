from pathlib import Path
from unittest import mock

import jsonschema
import numpy as np
import pyarrow.parquet as pq
import pytest

from fmu import dataio
from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.enums import StandardResultName
from fmu.dataio._models.standard_results.field_outline import (
    FieldOutlineResult,
    FieldOutlineSchema,
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

    from fmu.dataio.export.rms.field_outline import (
        _ExportFieldOutline,
    )

    with mock.patch(
        "fmu.dataio.export.rms.field_outline.xtgeo.polygons_from_roxar"
    ) as mock_polygons_from_roxar:
        # Mock the return value of xtgeo.polygons_from_roxar
        mock_polygons_from_roxar.return_value = xtgeo_fault_lines[0]

        yield _ExportFieldOutline(mock_project_variable)


@inside_rms
def test_files_exported_with_metadata(mock_export_class, rmssetup_with_fmuconfig):
    """Test that the standard_result is set correctly in the metadata"""

    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig / "../../share/results/polygons/field_outline"
    )
    assert export_folder.exists()

    assert (export_folder / "field_outline.parquet").exists()


@inside_rms
def test_standard_result_in_metadata(mock_export_class):
    """Test that the standard_result is set correctly in the metadata"""

    out = mock_export_class.export()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"] == StandardResultName.field_outline
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["version"]
        == FieldOutlineSchema.VERSION
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["url"]
        == FieldOutlineSchema.url()
    )


@inside_rms
def test_public_export_function(mock_project_variable, mock_export_class):
    """Test that the export function works"""

    from fmu.dataio.export.rms import export_field_outline

    out = export_field_outline(mock_project_variable)

    assert len(out.items) == 1

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert metadata["data"]["content"] == "field_outline"
    assert metadata["data"]["field_outline"]["contact"] == "fwl"
    assert metadata["access"]["classification"] == "internal"
    assert (
        metadata["data"]["standard_result"]["name"] == StandardResultName.field_outline
    )
    assert metadata["data"]["format"] == "parquet"


@inside_rms
def test_config_missing(mock_project_variable, rmssetup_with_fmuconfig, monkeypatch):
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_field_outline
    from fmu.dataio.export.rms._utils import CONFIG_PATH

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    config_path_modified = Path("wrong.yml")

    CONFIG_PATH.rename(config_path_modified)

    with pytest.raises(FileNotFoundError, match="Could not detect"):
        export_field_outline(mock_project_variable)

    # restore the global config file for later tests
    config_path_modified.rename(CONFIG_PATH)


@inside_rms
def test_payload_validates_against_model(
    mock_export_class,
):
    """Tests that the table exported is validated against the payload result
    model."""

    out = mock_export_class.export()
    df = (
        pq.read_table(out.items[0].absolute_path)
        .to_pandas()
        .replace(np.nan, None)
        .to_dict(orient="records")
    )
    FieldOutlineResult.model_validate(df)  # Throws if invalid


@inside_rms
def test_payload_validates_against_schema(
    mock_export_class,
):
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
        instance=df, schema=FieldOutlineSchema.dump()
    )  # Throws if invalid
