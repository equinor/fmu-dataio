"""Test the dataio running RMS spesici utility function for volumetrics"""

import os
from pathlib import Path

import pandas as pd
import pytest

import fmu.dataio as dataio
from fmu.dataio._logging import null_logger
from tests.utils import inside_rms

logger = null_logger(__name__)


VOLDATA = (Path("tests/data/drogon/tabular/geogrid--vol.csv")).absolute()


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

    from fmu.dataio.export.rms.volumetrics import _ExportVolumetricsRMS

    os.chdir(rmssetup_with_fmuconfig)

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
    metadata = dataio.read_metadata(out["volume_table"])

    assert "volumes" in metadata["data"]["content"]


@inside_rms
def test_rms_volumetrics_export_function(
    mock_project_variable, rmssetup_with_fmuconfig
):
    """Test the public function."""

    from fmu.dataio.export.rms import export_volumetrics

    os.chdir(rmssetup_with_fmuconfig)

    result = export_volumetrics(mock_project_variable, "Geogrid", "geogrid_volume")
    vol_table_file = result["volume_table"]

    assert Path(vol_table_file).is_file()
    metadata = dataio.read_metadata(vol_table_file)
    logger.debug("Volume_table_file is %s", vol_table_file)

    assert "volumes" in metadata["data"]["content"]
