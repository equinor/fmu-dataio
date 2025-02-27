from unittest import mock

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
        side_effect=lambda _project, name, _category: name,
    ):
        surfaces = get_horizons_in_folder(mock_project_variable, horizon_folder)

        # cthe empty 'msl' surface should not be included
        assert surfaces == ["TopVolantis", "TopTherys"]


def test_get_horizons_in_folder_folder_not_exist(mock_project_variable):
    from fmu.dataio.export.rms._utils import get_horizons_in_folder

    horizon_folder = "non_existent_folder"

    with pytest.raises(ValueError, match="not exist inside RMS"):
        get_horizons_in_folder(mock_project_variable, horizon_folder)
