"""Test the dataio running RMS spesici utility function for volumetrics"""

import unittest.mock as mock
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import fmu.dataio as dataio
from fmu.dataio._logging import null_logger
from tests.utils import inside_rms

logger = null_logger(__name__)


VOLDATA_LEGACY = Path("tests/data/drogon/tabular/geogrid--vol.csv").absolute()
VOLDATA_STANDARD = Path("tests/data/drogon/tabular/volumes/geogrid.csv").absolute()

EXPECTED_COLUMN_ORDER = [
    "FLUID",
    "ZONE",
    "REGION",
    "FACIES",
    "LICENSE",
    "BULK",
    "NET",
    "PORV",
    "HCPV",
    "STOIIP",
    "GIIP",
    "ASSOCIATEDGAS",
    "ASSOCIATEDOIL",
]


@pytest.fixture(scope="package")
def voltable_legacy():
    return pd.read_csv(VOLDATA_LEGACY)


@pytest.fixture(scope="package")
def voltable_standard():
    return pd.read_csv(VOLDATA_STANDARD)


@pytest.fixture
def exportvolumetrics(
    mocked_rmsapi_modules,
    mock_project_variable,
    voltable_standard,
    monkeypatch,
    rmssetup_with_fmuconfig,
):
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.inplace_volumes import _ExportVolumetricsRMS

    with mock.patch.object(
        _ExportVolumetricsRMS, "_get_table_with_volumes", return_value=voltable_standard
    ):
        yield _ExportVolumetricsRMS(mock_project_variable, "Geogrid", "geogrid_vol")


@inside_rms
def test_rms_volumetrics_export_class(exportvolumetrics):
    """See mocks in local conftest.py"""

    import rmsapi  # type: ignore # noqa
    import rmsapi.jobs as jobs  # type: ignore # noqa

    assert rmsapi.__version__ == "1.7"
    assert "Report" in jobs.Job.get_job("whatever").get_arguments.return_value

    # volume table name should be picked up by the mocked object
    assert exportvolumetrics._volume_table_name == "geogrid_volumes"

    out = exportvolumetrics._export_volume_table()

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "volumes" in metadata["data"]["content"]
    assert metadata["access"]["classification"] == "restricted"


@inside_rms
def test_rms_volumetrics_export_class_table_index(voltable_standard, exportvolumetrics):
    """See mocks in local conftest.py"""

    from fmu.dataio.export.rms.inplace_volumes import _TABLE_INDEX_COLUMNS

    out = exportvolumetrics._export_volume_table()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    # check that the table index is set correctly
    assert metadata["data"]["table_index"] == _TABLE_INDEX_COLUMNS

    # should fail if missing table index
    exportvolumetrics._dataframe = voltable_standard.drop(columns="ZONE")
    with pytest.raises(KeyError, match="ZONE is not in table"):
        exportvolumetrics._export_volume_table()


@inside_rms
def test_convert_table_from_legacy_to_standard_format(
    mock_project_variable,
    mocked_rmsapi_modules,
    voltable_standard,
    voltable_legacy,
    rmssetup_with_fmuconfig,
    monkeypatch,
):
    """Test that a voltable with legacy format is converted to
    the expected standard format"""

    from fmu.dataio.export.rms.inplace_volumes import (
        _FLUID_COLUMN,
        _ExportVolumetricsRMS,
    )

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    # set the return value to be the table with legacy format
    # conversion to standard format should take place automatically
    with mock.patch.object(
        _ExportVolumetricsRMS,
        "_convert_table_from_rms_to_legacy_format",
        return_value=voltable_legacy,
    ):
        instance = _ExportVolumetricsRMS(
            mock_project_variable, "Geogrid", "geogrid_vol"
        )

    # the _dataframe attribute should now have been converted to standard
    pd.testing.assert_frame_equal(voltable_standard, instance._dataframe)

    # check that the exported table is equal to the expected
    out = instance._export_volume_table()
    exported_table = pd.read_csv(out.items[0].absolute_path)
    pd.testing.assert_frame_equal(voltable_standard, exported_table)

    # check that the fluid column exists and contains oil and gas
    assert _FLUID_COLUMN in exported_table
    assert set(exported_table[_FLUID_COLUMN].unique()) == {"oil", "gas"}

    # check the column order
    assert list(exported_table.columns) == EXPECTED_COLUMN_ORDER

    # check that the legacy format and the standard format gives
    # the same sum for volumetric columns
    assert np.isclose(
        exported_table["STOIIP"].sum(),
        voltable_legacy["STOIIP_OIL"].sum(),
    )
    assert np.isclose(
        exported_table["GIIP"].sum(),
        voltable_legacy["GIIP_GAS"].sum(),
    )
    assert np.isclose(
        exported_table["BULK"].sum(),
        (voltable_legacy["BULK_OIL"] + voltable_legacy["BULK_GAS"]).sum(),
    )
    assert np.isclose(
        exported_table["PORV"].sum(),
        (voltable_legacy["PORV_OIL"] + voltable_legacy["PORV_GAS"]).sum(),
    )
    assert np.isclose(
        exported_table["HCPV"].sum(),
        (voltable_legacy["HCPV_OIL"] + voltable_legacy["HCPV_GAS"]).sum(),
    )

    # make a random check for a particular row as well
    filter_query = (
        "REGION == 'WestLowland' and ZONE == 'Valysar' and FACIES == 'Channel'"
    )
    expected_bulk_for_filter = 8989826.15
    assert np.isclose(
        exported_table.query(filter_query + " and FLUID == 'oil'")["BULK"],
        expected_bulk_for_filter,
    )
    assert np.isclose(
        voltable_legacy.query(filter_query)["BULK_OIL"],
        expected_bulk_for_filter,
    )


@inside_rms
def test_rms_volumetrics_export_config_missing(
    mock_project_variable,
    mocked_rmsapi_modules,
    rmssetup_with_fmuconfig,
    monkeypatch,
):
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_inplace_volumes
    from fmu.dataio.export.rms._utils import CONFIG_PATH

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    config_path_modified = Path("wrong.yml")

    CONFIG_PATH.rename(config_path_modified)

    with pytest.raises(FileNotFoundError, match="Could not detect"):
        export_inplace_volumes(mock_project_variable, "Geogrid", "geogrid_volume")

    # restore the global config file for later tests
    config_path_modified.rename(CONFIG_PATH)


@inside_rms
def test_rms_volumetrics_export_function(
    mock_project_variable,
    mocked_rmsapi_modules,
    voltable_standard,
    rmssetup_with_fmuconfig,
    monkeypatch,
):
    """Test the public function."""

    from fmu.dataio.export.rms import export_inplace_volumes
    from fmu.dataio.export.rms.inplace_volumes import (
        _TABLE_INDEX_COLUMNS,
        _ExportVolumetricsRMS,
    )

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    with mock.patch.object(
        _ExportVolumetricsRMS, "_get_table_with_volumes", return_value=voltable_standard
    ):
        result = export_inplace_volumes(
            mock_project_variable, "Geogrid", "geogrid_volume"
        )
    vol_table_file = result.items[0].absolute_path

    absoulte_path = (
        rmssetup_with_fmuconfig.parent.parent
        / "share/results/tables/volumes/geogrid.csv"
    )

    assert vol_table_file == absoulte_path

    assert Path(vol_table_file).is_file()
    metadata = dataio.read_metadata(vol_table_file)
    logger.debug("Volume_table_file is %s", vol_table_file)

    assert "volumes" in metadata["data"]["content"]
    assert metadata["access"]["classification"] == "restricted"
    assert metadata["data"]["table_index"] == _TABLE_INDEX_COLUMNS
