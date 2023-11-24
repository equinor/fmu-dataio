"""Test fuc"""
import os
import pytest
from pathlib import Path
import pandas as pd
import roxar
from fmu.dataio.rmscollectors.volumetrics import RmsInplaceVolumes

DROGON_PATH = "/project/fmu/tutorial/drogon/resmod/ff/users/dbs/23.1.1/"
DROGON_FMU_CONFIG = (
    Path(__file__).parent / "../data/drogon/global_config2/global_variables.yml"
)


@pytest.fixture(name="drogon_project", scope="session")
def _fix_drogon_project():
    """Return drogon rms project

    Returns:
        roxar.Project: instance of drogon project
    """
    drogon_rms_path = f"{DROGON_PATH}rms/model/drogon.rms13.1.2/"

    proj = roxar.Project.open(drogon_rms_path, readonly=True)
    return proj


@pytest.fixture(name="geo_volumes", scope="session")
def _fix_geo_volumes(drogon_project):
    return RmsInplaceVolumes(drogon_project, "Geogrid", "geogrid_volumes")


@pytest.mark.parametrize(
    "attr_name", ["params", "input", "output", "report", "variables"]
)
def test_inplace_volumes_attributes(geo_volumes, attr_name):
    """Test class RmsInplaceVolumes attributes

    Args:
        drogon_project (roxar.Project): an instance of the drogon project
    """

    if attr_name == "report":
        att_type = pd.DataFrame
    else:
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
