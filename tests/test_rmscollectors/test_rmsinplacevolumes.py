"""Test fuc"""
import pytest
import pandas as pd
import roxar
from fmu.dataio.rmscollectors.volumetrics import RmsInplaceVolumes

DROGON_PATH = "/project/fmu/tutorial/drogon/resmod/ff/users/dbs/23.1.1/"


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


def test_inplace_volumes_attributes(geo_volumes):
    """Test class RmsInplaceVolumes

    Args:
        drogon_project (roxar.Project): an instance of the drogon project
    """

    attr_names = ["params", "input", "output", "report", "variables"]

    for attr_name in attr_names:
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
