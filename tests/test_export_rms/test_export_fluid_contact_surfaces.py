"""Test the dataio running RMS specific utility function for fluid contact surfaces"""

from unittest import mock

import pytest
from fmu.datamodels.fmu_results.enums import FluidContactType
from fmu.datamodels.standard_results.enums import StandardResultName

from fmu import dataio
from fmu.dataio._logging import null_logger

logger = null_logger(__name__)


CONTACT_FOLDERS = ["fwl", "goc"]


@pytest.fixture
def mock_export_class(
    mock_project_variable,
    monkeypatch,
    rmssetup_with_fmuconfig,
    xtgeo_zones,
):
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.fluid_contact_surfaces import (
        _ExportFluidContactSurfaces,
    )

    with (
        mock.patch.object(
            _ExportFluidContactSurfaces, "_contact_folder_present", return_value=True
        ),
        mock.patch(
            "fmu.dataio.export.rms.fluid_contact_surfaces.list_folder_names_in_general2d_folder",
            return_value=CONTACT_FOLDERS,
        ),
        mock.patch(
            "fmu.dataio.export.rms.fluid_contact_surfaces.get_surfaces_in_general2d_folder",
            return_value=xtgeo_zones,
        ),
    ):
        yield _ExportFluidContactSurfaces(mock_project_variable)


@pytest.mark.parametrize("contact", CONTACT_FOLDERS)
@pytest.mark.usefixtures("inside_rms_interactive")
def test_files_exported_with_metadata(
    mock_export_class, rmssetup_with_fmuconfig, contact
):
    """Test that the standard_result is set correctly in the metadata"""

    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig
        / f"../../share/results/maps/fluid_contact_surface/{contact}"
    )
    assert export_folder.exists()

    assert (export_folder / "valysar.gri").exists()
    assert (export_folder / "therys.gri").exists()
    assert (export_folder / "volon.gri").exists()

    assert (export_folder / ".valysar.gri.yml").exists()
    assert (export_folder / ".therys.gri.yml").exists()
    assert (export_folder / ".volon.gri.yml").exists()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_no_valid_contact_folders_found(mock_export_class):
    """Test that an error is raised if no valid contact surfaces are found"""

    with (
        mock.patch(
            "fmu.dataio.export.rms.fluid_contact_surfaces.list_folder_names_in_general2d_folder",
            return_value=["invalid_folder"],
        ),
        pytest.raises(ValueError, match="Could not detect"),
    ):
        mock_export_class._get_contact_surfaces()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_only_valid_contact_folders_processed(
    rmssetup_with_fmuconfig, mock_export_class
):
    """Test that only folders with valid contact names are processed"""

    with mock.patch(
        "fmu.dataio.export.rms.fluid_contact_surfaces.list_folder_names_in_general2d_folder",
        return_value=["owc", "fwl", "invalid_folder", "gwc"],
    ):
        mock_export_class._contact_surfaces = mock_export_class._get_contact_surfaces()

        assert set(mock_export_class._get_contacts()) == {
            FluidContactType.owc,
            FluidContactType.fwl,
            FluidContactType.gwc,
        }
        mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig / "../../share/results/maps/fluid_contact_surface/"
    )
    assert export_folder.exists()
    assert (export_folder / "owc").exists()
    assert (export_folder / "fwl").exists()
    assert (export_folder / "gwc").exists()
    assert not (export_folder / "invalid_folder").exists()

    # test for one of the folders that expected files are present
    assert {file.name for file in (export_folder / "gwc").glob("*")} == {
        "valysar.gri",
        "therys.gri",
        "volon.gri",
        ".valysar.gri.yml",
        ".therys.gri.yml",
        ".volon.gri.yml",
    }


@pytest.mark.usefixtures("inside_rms_interactive")
def test_standard_result_in_metadata(mock_export_class):
    """Test that the standard_result is set correctly in the metadata"""

    out = mock_export_class.export()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.fluid_contact_surface
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_public_export_function(mock_project_variable, mock_export_class):
    """Test that the export function works"""

    from fmu.dataio.export.rms import export_fluid_contact_surfaces

    out = export_fluid_contact_surfaces(mock_project_variable)

    assert len(out.items) == 6  # 3 per contact

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "fluid_contact" in metadata["data"]["content"]
    assert metadata["data"]["fluid_contact"]["contact"] == "fwl"
    assert metadata["data"]["fluid_contact"]["truncated"] is False

    assert metadata["access"]["classification"] == "internal"
    assert metadata["data"]["is_prediction"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.fluid_contact_surface
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_unknown_name_in_stratigraphy_raises(mock_export_class):
    """Test that an error is raised if horizon name is missing in the stratigraphy"""

    mock_export_class._contact_surfaces["fwl"][0].name = "missing"

    with pytest.raises(ValueError, match="not listed"):
        mock_export_class.export()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_stratigraphy_missing_raises(
    mock_project_variable, mock_export_class, globalconfig1
):
    """Test that an error is raised if stratigraphy is missing from the config"""

    from fmu.dataio.export.rms import export_fluid_contact_surfaces

    # remove the stratigraphy block
    del globalconfig1["stratigraphy"]

    with (
        mock.patch(
            "fmu.dataio.export._base.load_config_from_path", return_value=globalconfig1
        ),
        pytest.raises(ValueError, match=r"stratigraphy.*is lacking"),
    ):
        export_fluid_contact_surfaces(mock_project_variable)


@pytest.mark.usefixtures("inside_rms_interactive")
def test_config_missing(mock_project_variable, rmssetup_with_fmuconfig, monkeypatch):
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_fluid_contact_surfaces

    # move up one directory to trigger not finding the config
    monkeypatch.chdir(rmssetup_with_fmuconfig.parent)

    with pytest.raises(FileNotFoundError, match="Could not detect"):
        export_fluid_contact_surfaces(mock_project_variable)
