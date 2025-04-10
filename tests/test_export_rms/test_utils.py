from unittest import mock

import pandas as pd
import pytest

from fmu.dataio._models.fmu_results.global_configuration import GlobalConfiguration


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

    with (
        mock.patch(
            "fmu.dataio.export.rms._utils.get_polygons_in_folder",
            return_value=[fault_line],
        ),
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


def test_validate_global_config(globalconfig1):
    from fmu.dataio.export.rms._utils import validate_global_config

    config = validate_global_config(globalconfig1)
    assert isinstance(config, GlobalConfiguration)


def test_validate_global_config_invalid(globalconfig1):
    from fmu.dataio.export.rms._utils import validate_global_config

    invalid_config = globalconfig1.copy()
    invalid_config.pop("masterdata")

    with pytest.raises(ValueError, match="valid config"):
        validate_global_config(invalid_config)


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
