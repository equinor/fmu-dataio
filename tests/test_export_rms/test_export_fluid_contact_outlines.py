"""Test the dataio running RMS specific utility function for fluid contact outlines"""

from unittest import mock

import jsonschema
import numpy as np
import pyarrow.parquet as pq
import pytest
from fmu.datamodels.fmu_results.enums import FluidContactType
from fmu.datamodels.standard_results.enums import StandardResultName
from fmu.datamodels.standard_results.fluid_contact_outline import (
    FluidContactOutlineResult,
    FluidContactOutlineSchema,
)

from fmu import dataio
from fmu.dataio._logging import null_logger

logger = null_logger(__name__)


CONTACT_FOLDERS = ["fwl", "goc"]


@pytest.fixture
def mock_export_class(
    mock_project_variable,
    monkeypatch,
    rmssetup_with_fmuconfig,
    xtgeo_zone_polygons,
):
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.fluid_contact_outlines import (
        _ExportFluidContactOutlines,
    )

    with (
        mock.patch.object(
            _ExportFluidContactOutlines, "_contact_folder_present", return_value=True
        ),
        mock.patch(
            "fmu.dataio.export.rms.fluid_contact_outlines.list_folder_names_in_general2d_folder",
            return_value=CONTACT_FOLDERS,
        ),
        mock.patch(
            "fmu.dataio.export.rms.fluid_contact_outlines.get_polygons_in_general2d_folder",
            return_value=xtgeo_zone_polygons,
        ),
    ):
        yield _ExportFluidContactOutlines(mock_project_variable)


@pytest.mark.parametrize("contact", CONTACT_FOLDERS)
@pytest.mark.usefixtures("inside_rms_interactive")
def test_files_exported_with_metadata(
    mock_export_class, rmssetup_with_fmuconfig, contact
):
    """Test that the standard_result is set correctly in the metadata"""

    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig
        / f"../../share/results/polygons/fluid_contact_outline/{contact}"
    )
    assert export_folder.exists()

    assert (export_folder / "valysar.parquet").exists()
    assert (export_folder / "therys.parquet").exists()
    assert (export_folder / "volon.parquet").exists()

    assert (export_folder / ".valysar.parquet.yml").exists()
    assert (export_folder / ".therys.parquet.yml").exists()
    assert (export_folder / ".volon.parquet.yml").exists()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_no_valid_contact_folders_found(mock_export_class):
    """Test that an error is raised if no valid contact surfaces are found"""

    with (
        mock.patch(
            "fmu.dataio.export.rms.fluid_contact_outlines.list_folder_names_in_general2d_folder",
            return_value=["invalid_folder"],
        ),
        pytest.raises(ValueError, match="Could not detect"),
    ):
        mock_export_class._get_contact_outlines()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_only_valid_contact_folders_processed(
    rmssetup_with_fmuconfig, mock_export_class
):
    """Test that only folders with valid contact names are processed"""

    with mock.patch(
        "fmu.dataio.export.rms.fluid_contact_outlines.list_folder_names_in_general2d_folder",
        return_value=["owc", "fwl", "invalid_folder", "gwc"],
    ):
        mock_export_class._contact_outlines = mock_export_class._get_contact_outlines()

        assert set(mock_export_class._get_contacts()) == {
            FluidContactType.owc,
            FluidContactType.fwl,
            FluidContactType.gwc,
        }
        mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig / "../../share/results/polygons/fluid_contact_outline/"
    )
    assert export_folder.exists()
    assert (export_folder / "owc").exists()
    assert (export_folder / "fwl").exists()
    assert (export_folder / "gwc").exists()
    assert not (export_folder / "invalid_folder").exists()

    # test for one of the folders that expected files are present
    assert {file.name for file in (export_folder / "gwc").glob("*")} == {
        "valysar.parquet",
        "therys.parquet",
        "volon.parquet",
        ".valysar.parquet.yml",
        ".therys.parquet.yml",
        ".volon.parquet.yml",
    }


@pytest.mark.usefixtures("inside_rms_interactive")
def test_standard_result_in_metadata(mock_export_class):
    """Test that the standard_result is set correctly in the metadata"""

    out = mock_export_class.export()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.fluid_contact_outline
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["version"]
        == FluidContactOutlineSchema.VERSION
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["url"]
        == FluidContactOutlineSchema.url()
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_public_export_function(mock_project_variable, mock_export_class):
    """Test that the export function works"""

    from fmu.dataio.export.rms import export_fluid_contact_outlines

    out = export_fluid_contact_outlines(mock_project_variable)

    assert len(out.items) == 6  # 3 per contact

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "fluid_contact" in metadata["data"]["content"]
    assert metadata["data"]["fluid_contact"]["contact"] == "fwl"
    assert metadata["data"]["fluid_contact"]["truncated"] is False

    assert metadata["access"]["classification"] == "internal"
    assert metadata["data"]["is_prediction"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.fluid_contact_outline
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_unknown_name_in_stratigraphy_raises(mock_export_class):
    """Test that an error is raised if horizon name is missing in the stratigraphy"""

    mock_export_class._contact_outlines["fwl"][0].name = "missing"

    with pytest.raises(ValueError, match="not listed"):
        mock_export_class.export()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_stratigraphy_missing_raises(
    mock_project_variable, mock_export_class, globalconfig1
):
    """Test that an error is raised if stratigraphy is missing from the config"""

    from fmu.dataio.export.rms import export_fluid_contact_outlines

    # remove the stratigraphy block
    del globalconfig1["stratigraphy"]

    with (
        mock.patch(
            "fmu.dataio.export._base.load_config_from_path", return_value=globalconfig1
        ),
        pytest.raises(ValueError, match=r"stratigraphy.*is lacking"),
    ):
        export_fluid_contact_outlines(mock_project_variable)


@pytest.mark.usefixtures("inside_rms_interactive")
def test_config_missing(mock_project_variable, rmssetup_with_fmuconfig, monkeypatch):
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_fluid_contact_outlines

    # move up one directory to trigger not finding the config
    monkeypatch.chdir(rmssetup_with_fmuconfig.parent)

    with pytest.raises(FileNotFoundError, match="Could not detect"):
        export_fluid_contact_outlines(mock_project_variable)


@pytest.mark.usefixtures("inside_rms_interactive")
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
    FluidContactOutlineResult.model_validate(df)  # Throws if invalid


@pytest.mark.usefixtures("inside_rms_interactive")
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
        instance=df, schema=FluidContactOutlineSchema.dump()
    )  # Throws if invalid
