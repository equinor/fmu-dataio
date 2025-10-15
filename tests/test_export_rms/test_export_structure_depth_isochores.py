"""Test the dataio running RMS specific utility function for depth isochores"""

from unittest import mock

import pytest
from fmu.datamodels.standard_results.enums import StandardResultName

from fmu import dataio
from fmu.dataio._logging import null_logger
from fmu.dataio.exceptions import ValidationError

logger = null_logger(__name__)


@pytest.fixture
def mock_export_class(
    mock_project_variable,
    monkeypatch,
    rmssetup_with_fmuconfig,
    xtgeo_zones,
):
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.structure_depth_isochores import (
        _ExportStructureDepthIsochores,
    )

    with mock.patch(
        "fmu.dataio.export.rms.structure_depth_isochores.get_zones_in_folder",
        return_value=xtgeo_zones,
    ):
        yield _ExportStructureDepthIsochores(mock_project_variable, "IS_extracted")


@pytest.mark.usefixtures("inside_rms_interactive")
def test_files_exported_with_metadata(mock_export_class, rmssetup_with_fmuconfig):
    """Test that the data is exported with metadata"""

    mock_export_class.export()

    export_folder = (
        rmssetup_with_fmuconfig / "../../share/results/maps/structure_depth_isochore"
    )
    assert export_folder.exists()

    assert (export_folder / "valysar.gri").exists()
    assert (export_folder / "therys.gri").exists()
    assert (export_folder / "volon.gri").exists()

    assert (export_folder / ".valysar.gri.yml").exists()
    assert (export_folder / ".therys.gri.yml").exists()
    assert (export_folder / ".volon.gri.yml").exists()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_standard_result_in_metadata(mock_export_class):
    """Test that the standard_result is set correctly in the metadata"""

    out = mock_export_class.export()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.structure_depth_isochore
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_public_export_function(mock_project_variable, mock_export_class):
    """Test that the export function works"""

    from fmu.dataio.export.rms import export_structure_depth_isochores

    out = export_structure_depth_isochores(mock_project_variable, "IS_extracted")

    assert len(out.items) == 3

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert metadata["data"]["content"] == "thickness"
    assert metadata["access"]["classification"] == "internal"
    assert metadata["data"]["is_prediction"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.structure_depth_isochore
    )


@pytest.mark.usefixtures("inside_rms_interactive")
def test_unknown_name_in_stratigraphy_raises(mock_export_class):
    """Test that an error is raised if horizon name is missing in the stratigraphy"""

    mock_export_class._surfaces[0].name = "missing"

    with pytest.raises(ValueError, match="not listed"):
        mock_export_class.export()


@pytest.mark.usefixtures("inside_rms_interactive")
def test_stratigraphy_missing_raises(
    mock_project_variable, mock_export_class, globalconfig1
):
    """Test that an error is raised if stratigraphy is missing from the config"""

    from fmu.dataio.export.rms import export_structure_depth_isochores

    # remove the stratigraphy block
    del globalconfig1["stratigraphy"]

    with (
        mock.patch(
            "fmu.dataio.export._base.load_config_from_path", return_value=globalconfig1
        ),
        pytest.raises(ValueError, match=r"stratigraphy.*is lacking"),
    ):
        export_structure_depth_isochores(mock_project_variable, "IS_extracted")


@pytest.mark.usefixtures("inside_rms_interactive")
def test_validation_negative_values(
    mock_project_variable, monkeypatch, rmssetup_with_fmuconfig, regsurf
):
    """Test that the export function raises error if negative values are detected"""

    from fmu.dataio.export.rms import export_structure_depth_isochores

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    surf_with_negative_values = regsurf.copy()
    surf_with_negative_values.values = -20
    surf_with_negative_values.name = "TopVolantis"  # should be a startigraphic name

    with mock.patch(  # noqa
        "fmu.dataio.export.rms.structure_depth_isochores.get_zones_in_folder",
        return_value=[surf_with_negative_values],
    ):
        with pytest.raises(ValidationError, match="Negative values"):
            export_structure_depth_isochores(mock_project_variable, "IS_extracted")


@pytest.mark.usefixtures("inside_rms_interactive")
def test_config_missing(mock_project_variable, rmssetup_with_fmuconfig, monkeypatch):
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_structure_depth_isochores

    # move up one directory to trigger not finding the config
    monkeypatch.chdir(rmssetup_with_fmuconfig.parent)
    with pytest.raises(FileNotFoundError, match="Could not detect"):
        export_structure_depth_isochores(mock_project_variable, "IS_extracted")
