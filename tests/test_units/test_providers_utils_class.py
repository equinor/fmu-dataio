import numpy as np
import pytest

from fmu.dataio._metadata.objectdata._utils import Utils, get_value_statistics
from fmu.dataio.dataio import ExportData


def test_stratigraphy(drogon_exportdata: ExportData) -> None:
    """Test the stratigraphy."""

    strat = drogon_exportdata._export_config.config.stratigraphy

    ###### Test get stratigraphic name ######

    # Correct name
    assert Utils.get_stratigraphic_name(strat, "Valysar") == "Valysar Fm."

    # Incorrect name
    with pytest.warns(UserWarning, match="not found in the stratigraphic column"):
        assert Utils.get_stratigraphic_name(strat, "Ile") == ""

    # Empty name
    with pytest.warns(UserWarning, match="not found in the stratigraphic column"):
        assert Utils.get_stratigraphic_name(strat, "") == ""


def test_get_value_statistics_with_valid_values() -> None:
    """Test the get_value_statistics function with valid values."""

    values = [1, 2, 3, 4, 5]
    stats = get_value_statistics(values)

    assert stats.min == 1.0
    assert stats.max == 5.0
    assert stats.mean == 3.0
    np.testing.assert_almost_equal(stats.std, 1.414, decimal=3)


def test_get_value_statistics_with_some_nan_values() -> None:
    """Test the get_value_statistics function with some NaN values."""

    values = [1, 2, np.nan, 4, 5]
    stats = get_value_statistics(values)

    assert stats.min == 1.0
    assert stats.max == 5.0
    assert stats.mean == 3.0
    np.testing.assert_almost_equal(stats.std, 1.581, decimal=3)


def test_get_value_statistics_with_only_nan_values() -> None:
    """Test the get_value_statistics function with only NaN values."""

    values = [np.nan, np.nan, np.nan]
    assert get_value_statistics(values) is None
