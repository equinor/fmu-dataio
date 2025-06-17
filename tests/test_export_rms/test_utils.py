from unittest import mock

import pandas as pd
import pytest


def test_get_horizons_in_folder(mock_project_variable):
    from fmu.dataio.export.rms._utils import get_horizons_in_folder

    horizon_folder = "DS_final"

    horizon1 = mock.MagicMock()
    horizon1[horizon_folder].is_empty.return_value = True
    horizon1.name = "msl"

    horizon2 = mock.MagicMock()
    horizon2[horizon_folder].is_empty.return_value = False
    horizon2.name = "TopVolantis"

    horizon3 = mock.MagicMock()
    horizon3[horizon_folder].is_empty.return_value = False
    horizon3.name = "TopTherys"

    mock_project_variable.horizons.__iter__.return_value = [
        horizon1,
        horizon2,
        horizon3,
    ]
    # Mock xtgeo.surface_from_roxar to return just the surface name
    with mock.patch(
        "xtgeo.surface_from_roxar",
        side_effect=lambda _project, name, _category, stype: name,
    ):
        surfaces = get_horizons_in_folder(mock_project_variable, horizon_folder)

        # cthe empty 'msl' surface should not be included
        assert surfaces == ["TopVolantis", "TopTherys"]


def test_get_horizons_in_folder_folder_not_exist(mock_project_variable):
    from fmu.dataio.export.rms._utils import get_horizons_in_folder

    horizon_folder = "non_existent_folder"

    with pytest.raises(ValueError, match="not exist inside RMS"):
        get_horizons_in_folder(mock_project_variable, horizon_folder)


def test_get_horizons_in_folder_all_empty(mock_project_variable):
    from fmu.dataio.export.rms._utils import get_horizons_in_folder

    horizon_folder = "DS_final"

    horizon1 = mock.MagicMock()
    horizon1[horizon_folder].is_empty.return_value = True

    mock_project_variable.horizons.__iter__.return_value = [horizon1]

    with pytest.raises(RuntimeError, match="only empty items"):
        get_horizons_in_folder(mock_project_variable, horizon_folder)


def test_get_horizons_in_folder_wrong_type(mock_project_variable):
    """Test that an error is raised if no surfaces are detected due to wrong type"""
    from fmu.dataio.export.rms._utils import get_horizons_in_folder

    horizon_folder = "DS_final"

    class MockSurface(mock.MagicMock): ...

    class MockPolygon(mock.MagicMock): ...

    with mock.patch("fmu.dataio.export.rms._utils.rmsapi.Surface", MockSurface):
        horizon1 = mock.MagicMock()
        horizon1[horizon_folder] = MockPolygon  # Mock not being a Surface
        horizon1[horizon_folder].is_empty.return_value = False

        mock_project_variable.horizons.__iter__.return_value = [horizon1]

        with pytest.raises(RuntimeError, match="No surfaces detected"):
            get_horizons_in_folder(mock_project_variable, horizon_folder)


def test_get_zones_in_folder(mock_project_variable):
    from fmu.dataio.export.rms._utils import get_zones_in_folder

    zone_folder = "IS_final"

    zone1 = mock.MagicMock()
    zone1[zone_folder].is_empty.return_value = False
    zone1.name = "Valysar"

    zone2 = mock.MagicMock()
    zone2[zone_folder].is_empty.return_value = False
    zone2.name = "Therys"

    zone3 = mock.MagicMock()
    zone3[zone_folder].is_empty.return_value = True
    zone3.name = "Below"

    mock_project_variable.zones.__iter__.return_value = [zone1, zone2, zone3]
    # Mock xtgeo.surface_from_roxar to return just the surface name
    with mock.patch(
        "xtgeo.surface_from_roxar",
        side_effect=lambda _project, name, _category, stype: name,
    ):
        zones = get_zones_in_folder(mock_project_variable, zone_folder)

        # cthe empty 'Below' surface should not be included
        assert zones == ["Valysar", "Therys"]


def test_get_zones_in_folder_folder_not_exist(mock_project_variable):
    from fmu.dataio.export.rms._utils import get_zones_in_folder

    zone_folder = "non_existent_folder"

    with pytest.raises(ValueError, match="not exist inside RMS"):
        get_zones_in_folder(mock_project_variable, zone_folder)


def test_get_zones_in_folder_all_empty(mock_project_variable):
    from fmu.dataio.export.rms._utils import get_zones_in_folder

    zone_folder = "IS_final"

    zone1 = mock.MagicMock()
    zone1[zone_folder].is_empty.return_value = True

    mock_project_variable.zones.__iter__.return_value = [zone1]

    with pytest.raises(RuntimeError, match="only empty items"):
        get_zones_in_folder(mock_project_variable, zone_folder)


def test_get_zones_in_folder_wrong_type(mock_project_variable):
    """Test that an error is raised if no surfaces are detected due to wrong type"""
    from fmu.dataio.export.rms._utils import get_zones_in_folder

    zone_folder = "IS_final"

    class MockSurface(mock.MagicMock): ...

    class MockPolygon(mock.MagicMock): ...

    with mock.patch("fmu.dataio.export.rms._utils.rmsapi.Surface", MockSurface):
        zone1 = mock.MagicMock()
        zone1[zone_folder] = MockPolygon  # Mock not being a Surface
        zone1[zone_folder].is_empty.return_value = False

        mock_project_variable.zones.__iter__.return_value = [zone1]

        with pytest.raises(RuntimeError, match="No surfaces detected"):
            get_zones_in_folder(mock_project_variable, zone_folder)


def test_get_polygons_in_folder_folder_not_exist(mock_project_variable):
    from fmu.dataio.export.rms._utils import get_polygons_in_folder

    horizon_folder = "non_existent_folder"

    with pytest.raises(ValueError, match="not exist inside RMS"):
        get_polygons_in_folder(mock_project_variable, horizon_folder)


def test_get_polygons_in_folder_all_empty(mock_project_variable):
    from fmu.dataio.export.rms._utils import get_polygons_in_folder

    horizon_folder = "DS_final"

    horizon1 = mock.MagicMock()
    horizon1[horizon_folder].is_empty.return_value = True

    mock_project_variable.horizons.__iter__.return_value = [horizon1]

    with pytest.raises(RuntimeError, match="only empty items"):
        get_polygons_in_folder(mock_project_variable, horizon_folder)


def test_get_polygons_in_folder_wrong_type(mock_project_variable):
    """Test that an error is raised if no polygons are detected due to wrong type"""
    from fmu.dataio.export.rms._utils import get_polygons_in_folder

    horizon_folder = "DS_final"

    class MockSurface(mock.MagicMock): ...

    class MockPolygon(mock.MagicMock): ...

    with mock.patch("fmu.dataio.export.rms._utils.rmsapi.Polylines", MockPolygon):
        horizon1 = mock.MagicMock()
        horizon1[horizon_folder] = MockSurface  # Mock not being a Polygon
        horizon1[horizon_folder].is_empty.return_value = False

        mock_project_variable.horizons.__iter__.return_value = [horizon1]

        with pytest.raises(RuntimeError, match="No polygons detected"):
            get_polygons_in_folder(mock_project_variable, horizon_folder)


def test_get_faultlines_in_folder(mock_project_variable, polygons):
    """
    Test that the get_faultlines_in_folder works as expected when the
    'Name' attribute is present.
    """
    from fmu.dataio.export.rms._utils import get_faultlines_in_folder

    fault_line = polygons.copy()
    df = fault_line.get_dataframe()

    # make sure test assumpions are correct
    assert "NAME" not in df
    assert "Name" not in df

    # fault lines from RMS will have a 'Name' attribute
    df["Name"] = "F1"
    fault_line.set_dataframe(df)

    with mock.patch(
        "fmu.dataio.export.rms._utils.get_polygons_in_folder",
        return_value=[fault_line],
    ):
        fault_lines = get_faultlines_in_folder(mock_project_variable, "DL_faultlines")

        # Check that the 'Name' column has been translated to uppercase
        assert "NAME" in fault_lines[0].get_dataframe(copy=False)
        assert "Name" not in fault_lines[0].get_dataframe(copy=False)


def test_get_faultlines_in_folder_raises_if_missing_name(
    mock_project_variable, polygons
):
    """
    Test that the get_faultlines_in_folder raises error when the
    'Name' attribute is missing.
    """
    from fmu.dataio.export.rms._utils import get_faultlines_in_folder

    fault_line = polygons.copy()
    df = fault_line.get_dataframe()

    # make sure test assumpions are correct
    assert "NAME" not in df
    assert "Name" not in df

    with (
        mock.patch(
            "fmu.dataio.export.rms._utils.get_polygons_in_folder",
            return_value=[fault_line],
        ),
        pytest.raises(ValueError, match="missing"),
    ):
        get_faultlines_in_folder(mock_project_variable, "DL_faultlines")


def test_get_open_polygons_id(polygons):
    """Test the function to list open polygons in an xtgoe.Polygons object"""
    from fmu.dataio.export.rms._utils import get_open_polygons_id

    df_closed = polygons.get_dataframe()

    # create an open polygon dataframe
    df_open = polygons.get_dataframe().drop(index=0)
    df_open[polygons.pname] = 2  # set id to 2 for the open polygon

    # add the open polygon to the polygons object
    df_combined = pd.concat([df_closed, df_open])
    polygons.set_dataframe(df_combined)

    open_polygons = get_open_polygons_id(polygons)
    assert open_polygons == [2]


def test_get_surfaces_in_general2d_folder(mock_project_variable):
    """Test that get_surfaces_in_general2d_folder only picks up non-empty surfaces"""

    from fmu.dataio.export.rms._utils import get_surfaces_in_general2d_folder

    folder = "MyFolder"
    mock_folder = mock.MagicMock()

    surf1 = mock.MagicMock()
    surf1.is_empty.return_value = True
    surf1.name = "msl"

    surf2 = mock.MagicMock()
    surf2.is_empty.return_value = False
    surf2.name = "TopVolantis"

    surf3 = mock.MagicMock()
    surf3.is_empty.return_value = False
    surf3.name = "TopTherys"

    mock_folder.values.return_value = [surf1, surf2, surf3]

    mock_project_variable.general2d_data.folders = {folder: mock_folder}

    # Mock xtgeo.surface_from_roxar to return just the surface name
    with mock.patch(
        "xtgeo.surface_from_roxar",
        side_effect=lambda _project, name, _category, stype: name,
    ):
        surfaces = get_surfaces_in_general2d_folder(mock_project_variable, folder)

        # the empty 'msl' surface should not be included
        assert surfaces == ["TopVolantis", "TopTherys"]


def test_get_surfaces_in_general2d_folder_all_empty(mock_project_variable):
    """Test that an error is raised if all surfaces are empty"""
    from fmu.dataio.export.rms._utils import get_surfaces_in_general2d_folder

    folder = ["MainFolder"]

    surf = mock.MagicMock()
    surf.is_empty.return_value = True

    mock_folder = mock_project_variable.general2d_data.folders[folder]
    mock_folder.values.return_value = [surf]

    with pytest.raises(RuntimeError, match="No surfaces detected"):
        get_surfaces_in_general2d_folder(mock_project_variable, folder)


def test_get_polygons_in_general2d_folder(mock_project_variable):
    """Test that get_polygons_in_general2d_folder only picks up non-empty surfaces"""

    from fmu.dataio.export.rms._utils import get_polygons_in_general2d_folder

    folder = "MyFolder"
    mock_folder = mock.MagicMock()

    pol1 = mock.MagicMock()
    pol1.is_empty.return_value = True
    pol1.name = "msl"

    pol2 = mock.MagicMock()
    pol2.is_empty.return_value = False
    pol2.name = "TopVolantis"

    pol3 = mock.MagicMock()
    pol3.is_empty.return_value = False
    pol3.name = "TopTherys"

    mock_folder.values.return_value = [pol1, pol2, pol3]

    mock_project_variable.general2d_data.folders = {folder: mock_folder}

    # Mock xtgeo.polygons_from_roxar to return just the polygon name
    with mock.patch(
        "xtgeo.polygons_from_roxar",
        side_effect=lambda _project, name, _category, stype: name,
    ):
        polygons = get_polygons_in_general2d_folder(mock_project_variable, folder)

        # the empty 'msl' polygon should not be included
        assert polygons == ["TopVolantis", "TopTherys"]


def test_get_polygons_in_general2d_folder_all_empty(mock_project_variable):
    """Test that an error is raised if all polygons are empty"""
    from fmu.dataio.export.rms._utils import get_polygons_in_general2d_folder

    folder = ["MainFolder"]

    pol = mock.MagicMock()
    pol.is_empty.return_value = True

    mock_folder = mock_project_variable.general2d_data.folders[folder]
    mock_folder.values.return_value = [pol]

    with pytest.raises(RuntimeError, match="No polygons detected"):
        get_polygons_in_general2d_folder(mock_project_variable, folder)


def test_get_general2d_folder(mock_project_variable):
    """
    Test that accessing a General 2D folder works if a folder is present.
    While an error is raised if not.
    """
    from fmu.dataio.export.rms._utils import get_general2d_folder

    horizon_folder = ["MainFolder"]
    get_general2d_folder(mock_project_variable, horizon_folder)

    horizon_folder = ["non_existent_folder"]
    with pytest.raises(ValueError, match="not exist"):
        get_general2d_folder(mock_project_variable, horizon_folder)

    horizon_folder = ["MainFolder", "SubFolder"]
    get_general2d_folder(mock_project_variable, horizon_folder)

    horizon_folder = ["MainFolder", "non_existent_folder"]
    with pytest.raises(ValueError, match="not exist"):
        get_general2d_folder(mock_project_variable, horizon_folder)
