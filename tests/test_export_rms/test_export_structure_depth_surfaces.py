"""Test the dataio running RMS spesici utility function for volumetrics"""

from pathlib import Path
from unittest import mock

import pytest

from fmu import dataio
from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.enums import StandardResultName
from tests.utils import inside_rms

logger = null_logger(__name__)


@pytest.fixture
def mock_export_class(
    mock_project_variable,
    monkeypatch,
    rmssetup_with_fmuconfig,
    xtgeo_surfaces,
):
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.structure_depth_surfaces import (
        _ExportStructureDepthSurfaces,
    )

    with mock.patch(
        "fmu.dataio.export.rms.structure_depth_surfaces.get_horizons_in_folder",
        return_value=xtgeo_surfaces,
    ):
        yield _ExportStructureDepthSurfaces(mock_project_variable, "geogrid_vol")


@inside_rms
def test_files_exported_with_metadata(mock_export_class, rmssetup_with_fmuconfig):
    """Test that the standard_result is set correctly in the metadata"""

    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig / "../../share/results/maps/structure_depth_surfaces"
    )
    assert export_folder.exists()

    assert (export_folder / "topvolantis.gri").exists()
    assert (export_folder / "toptherys.gri").exists()
    assert (export_folder / "topvolon.gri").exists()

    assert (export_folder / ".topvolantis.gri.yml").exists()
    assert (export_folder / ".toptherys.gri.yml").exists()
    assert (export_folder / ".topvolon.gri.yml").exists()


@inside_rms
def test_standard_result_in_metadata(mock_export_class):
    """Test that the standard_result is set correctly in the metadata"""

    out = mock_export_class.export()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.structure_depth_surface
    )


@inside_rms
def test_public_export_function(mock_project_variable, mock_export_class):
    """Test that the export function works"""

    from fmu.dataio.export.rms import export_structure_depth_surfaces

    out = export_structure_depth_surfaces(mock_project_variable, "DS_extract")

    assert len(out.items) == 3

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "depth" in metadata["data"]["content"]
    assert metadata["access"]["classification"] == "internal"
    assert metadata["data"]["is_prediction"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.structure_depth_surface
    )


@inside_rms
def test_config_missing(mock_project_variable, rmssetup_with_fmuconfig, monkeypatch):
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_structure_depth_surfaces
    from fmu.dataio.export.rms._utils import CONFIG_PATH

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    config_path_modified = Path("wrong.yml")

    CONFIG_PATH.rename(config_path_modified)

    with pytest.raises(FileNotFoundError, match="Could not detect"):
        export_structure_depth_surfaces(mock_project_variable, "DS_extract")

    # restore the global config file for later tests
    config_path_modified.rename(CONFIG_PATH)
