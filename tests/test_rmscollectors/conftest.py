import pytest
from pathlib import Path
import roxar

DROGON_PATH = "/project/fmu/tutorial/drogon/resmod/ff/users/dbs/23.1.1/"
TEST_DATA = Path(__file__).parent / "../data/drogon/"
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
