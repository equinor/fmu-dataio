"""Test the dataio running RMS spesici utility function for volumetrics"""

from pathlib import Path

import pandas as pd
import pytest

import fmu.dataio as dataio
from fmu.dataio._logging import null_logger
from tests.utils import inside_rms

logger = null_logger(__name__)


VOLDATA = (Path("tests/data/drogon/tabular/geogrid--vol.csv")).absolute()
EXPECTED_TABLE_INDEX_COLUMNS = ["ZONE", "REGION", "FACIES"]


@pytest.fixture
def voltable_as_dataframe():
    return pd.read_csv(VOLDATA)


@inside_rms
def test_rms_volumetrics_export_class(
    mock_project_variable, voltable_as_dataframe, rmssetup_with_fmuconfig, monkeypatch
):
    """See mocks in local conftest.py"""

    import rmsapi  # type: ignore # noqa
    import rmsapi.jobs as jobs  # type: ignore # noqa

    from fmu.dataio.export.rms.inplace_volumes import (
        _ExportVolumetricsRMS,
        _TABLE_INDEX_COLUMNS,
    )

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    assert rmsapi.__version__ == "1.7"
    assert "Report" in jobs.Job.get_job("whatever").get_arguments.return_value

    instance = _ExportVolumetricsRMS(
        mock_project_variable,
        "Geogrid",
        "geogrid_vol",
    )

    assert instance._volume_table_name == "geogrid_volumes"

    # patch the dataframe which originally shall be retrieved from RMS
    monkeypatch.setattr(instance, "_dataframe", voltable_as_dataframe)

    out = instance._export_volume_table()

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "volumes" in metadata["data"]["content"]
    assert metadata["access"]["classification"] == "restricted"

    # check that the table index is set correctly
    assert len(_TABLE_INDEX_COLUMNS) > len(EXPECTED_TABLE_INDEX_COLUMNS)
    assert instance._table_index == EXPECTED_TABLE_INDEX_COLUMNS
    assert metadata["data"]["table_index"] == EXPECTED_TABLE_INDEX_COLUMNS


@inside_rms
def test_rms_volumetrics_export_config_missing(
    mock_project_variable, rmssetup_with_fmuconfig, monkeypatch
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
    mock_project_variable, rmssetup_with_fmuconfig, monkeypatch
):
    """Test the public function."""

    from fmu.dataio.export.rms import export_inplace_volumes

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    result = export_inplace_volumes(mock_project_variable, "Geogrid", "geogrid_volume")
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
