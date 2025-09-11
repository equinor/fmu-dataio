"""
Test the dataio running RMS specific utility function for structure depth fault surfaces
"""

from unittest import mock

import pytest
from fmu.datamodels.standard_results.enums import StandardResultName

from fmu import dataio
from fmu.dataio._logging import null_logger

logger = null_logger(__name__)


@pytest.fixture
def mock_export_class(
    mock_project_variable,
    monkeypatch,
    rmssetup_with_fmuconfig,
    fault_surfaces_triangulated,
):
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.structure_depth_fault_surfaces import (
        _ExportStructureDepthFaultSurfaces,
    )

    with mock.patch(
        "fmu.dataio.export.rms.structure_depth_fault_surfaces._get_fault_surfaces_from_rms",
        return_value=fault_surfaces_triangulated,
    ):
        yield _ExportStructureDepthFaultSurfaces(mock_project_variable, "GF_depth_hum")


@pytest.mark.usefixtures("inside_rms_interactive")
def test_files_exported_with_metadata(mock_export_class, rmssetup_with_fmuconfig):
    """Test that the standard_result is set correctly in the metadata"""

    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig
        / "../../share/results/maps/structure_depth_fault_surface"
    )

    assert export_folder.exists()

    filename_f3 = "F3.ts".lower()
    filename_f3_yaml = "." + filename_f3 + ".yml"
    assert (export_folder / filename_f3).exists()
    assert (export_folder / filename_f3_yaml).exists()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_standard_result_in_metadata(mock_export_class):
    """Test that the standard_result is set correctly in the metadata"""

    out = mock_export_class.export()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.structure_depth_fault_surface
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_public_export_function(
    mock_project_variable,
    mock_structural_model,
    mock_export_class,  # 'mock_export_class' must be present
):
    """Test that the export function works"""

    from fmu.dataio.export.rms import export_structure_depth_fault_surfaces

    struct_mod_name = next(iter(mock_structural_model))

    with pytest.warns(UserWarning, match="is experimental and may change in future"):
        out = export_structure_depth_fault_surfaces(
            mock_project_variable, struct_mod_name
        )

    # Check that all fault surfaces are exported
    assert len(out.items) == 6

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert metadata["access"]["classification"] == "internal"
    assert metadata["data"]["content"] == "fault_surface"
    assert metadata["data"]["is_prediction"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.structure_depth_fault_surface
    )

    assert metadata["data"]["format"] == "tsurf"
    assert metadata["data"]["layout"] == "triangulated"
    assert metadata["class"] == "surface"

    assert metadata["data"]["spec"]["num_triangles"] == 2
    assert metadata["data"]["spec"]["num_vertices"] == 4


@pytest.mark.usefixtures("inside_rms_interactive")
def test_config_missing(
    mock_project_variable,
    mock_structural_model,
):
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_structure_depth_fault_surfaces

    struct_mod_name = next(iter(mock_structural_model))
    with (
        pytest.raises(FileNotFoundError, match="Could not detect"),
        pytest.warns(UserWarning, match="is experimental and may change in future"),
    ):
        export_structure_depth_fault_surfaces(
            mock_project_variable,
            struct_mod_name,
        )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_unknown_structural_model_name_raises(
    mock_project_variable,
    monkeypatch,
    rmssetup_with_fmuconfig,
    mock_structural_model,
):
    """
    Test that an exception is raised if the structural model is not found
    among the structural models in RMS.
    """

    from fmu.dataio.export.rms import export_structure_depth_fault_surfaces

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    with (
        pytest.raises(
            ValueError, match="Project does not contain a structural model named"
        ),
        pytest.warns(UserWarning, match="is experimental and may change in future"),
    ):
        export_structure_depth_fault_surfaces(
            mock_project_variable,
            "Non-existing structural model name",
        )
