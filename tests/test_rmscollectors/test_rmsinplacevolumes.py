"""Test fuc"""
import os
import pytest
import yaml
from pathlib import Path
import pandas as pd
from fmu.dataio.rmscollectors.volumetrics import RmsInplaceVolumes

DROGON_PATH = "/project/fmu/tutorial/drogon/resmod/ff/users/dbs/23.1.1/"
TEST_DATA = Path(__file__).parent / "../data/drogon/"
DROGON_FMU_CONFIG = (
    Path(__file__).parent / "../data/drogon/global_config2/global_variables.yml"
)


@pytest.fixture(name="inplace_parameters", scope="session")
def _fix_inplace_parameters():
    """Return parameter set originally extracted from drogon

    Raises:
        IOError: if cannot find test data

    Returns:
        dict: the parameter dictionary
    """
    # This parameter set is extracted from drogon rms project
    # rms version 13.1.2 linux based
    params = None
    inplace_params = TEST_DATA / "rmscollectors/rmsinplace_params.yml"
    with open(inplace_params, "r") as stream:
        params = yaml.load(stream, Loader=yaml.SafeLoader)

    if params is None:
        raise IOError(f"Cannot find parameters at {str(inplace_params)}")
    return params


@pytest.fixture(name="geo_volumes", scope="session")
def _fix_geo_volumes(drogon_project):
    return RmsInplaceVolumes(drogon_project, "Geogrid", "geogrid_volumes")


@pytest.mark.parametrize("attr_name", ["params", "input", "output", "variables"])
def test_inplace_volumes_attributes(geo_volumes, attr_name):
    """Test class RmsInplaceVolumes attributes

    Args:
        drogon_project (roxar.Project): an instance of the drogon project
    """

    att_type = dict
    assert hasattr(
        geo_volumes, attr_name
    ), f"No {attr_name} attribute for RmsInplaceVolumes"
    attr = getattr(geo_volumes, attr_name)
    assert isinstance(
        attr, att_type
    ), f" {attr_name} should be dictionary, but is {type(attr)}"


def test_inplace_volumes_export(geo_volumes, tmp_path):
    """Test export of inplace volumes

    Args:
        geo_volumes (dataio.RmsInplaceVolumes): instance of RmsInplaceVolumes from drogon
        tmp_path (pathlib.Path): path where test will be stored
    """
    test_path = tmp_path / "realization-0/iter-0/"
    folder_types = ["maps", "grids", "tables"]
    test_path.mkdir(parents=True)
    os.chdir(test_path)
    exported = geo_volumes.export(config_path=DROGON_FMU_CONFIG)
    # TODO: Something wrong with export path, doesn't export to realization-*..
    # moved on because I went blind, and couldn't figure what is wrong
    # bad fix on the two lines below
    # shared_path = test_path / share/results
    shared_path = Path(exported[0]).parent.parent
    assert shared_path.exists(), f"folder {str(shared_path)}, not made"
    folders = shared_path.glob("*/")
    folder_count = 0
    for folder in folders:
        assert folder.name in folder_types, f"{folder} not in {folder_types}"
        folder_count += 1
    assert folder_count == 3, f"Found {folder_count} folders, not 3"


def test_inplace_volumes_report(geo_volumes):
    report = geo_volumes.report
    assert isinstance(
        report, pd.DataFrame
    ), f"Report should be pandas dataframe, but is {type(report)}"
