"""The conftest.py, providing magical fixtures to tests."""
import inspect
import logging
import os
import shutil
from functools import wraps
from pathlib import Path

import pytest
import xtgeo
import yaml

from fmu.dataionew._utils import C, G, S
from fmu.dataionew.dataionew import ExportData

logger = logging.getLogger(__name__)

ROOTPWD = Path(".").absolute()
RUN1 = "tests/data/drogon/ertrun1/realization-0/iter-0"
RUN2 = "tests/data/drogon/ertrun1"


def inside_rms(func):
    """Decorator for being inside RMS"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        ExportData._inside_rms = True
        retval = func(*args, **kwargs)
        ExportData._inside_rms = False
        return retval

    return wrapper


@pytest.fixture(name="testroot", scope="session", autouse=True)
def fixture_testroot():
    return ROOTPWD


@pytest.fixture(name="fmurun", scope="session", autouse=True)
def fixture_fmurun(tmp_path_factory):
    """Create a tmp folder structure for testing; here a new fmurun."""
    tmppath = tmp_path_factory.mktemp("data")
    newpath = tmppath / RUN1
    shutil.copytree(ROOTPWD / RUN1, newpath)
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return newpath


@pytest.fixture(name="fmurun_w_casemetadata", scope="session", autouse=True)
def fixture_fmurun_w_casemetadata(tmp_path_factory):
    """Create a tmp folder structure for testing; here existing fmurun w/ case meta!"""
    tmppath = tmp_path_factory.mktemp("data3")
    newpath = tmppath / RUN2
    shutil.copytree(ROOTPWD / RUN2, newpath)
    basepath = newpath / "realization-0/iter-0"
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return basepath


@pytest.fixture(name="rmsrun_fmu_w_casemetadata", scope="session", autouse=True)
def fixture_rmsrun_fmu_w_casemetadata(tmp_path_factory):
    """Create a tmp folder structure for testing; here existing fmurun w/ case meta!

    Then we locate the folder to the ...rms/model folder, pretending running RMS
    in a FMU setup where case metadata are present
    """
    tmppath = tmp_path_factory.mktemp("data3")
    newpath = tmppath / RUN2
    shutil.copytree(ROOTPWD / RUN2, newpath)
    rmspath = newpath / "realization-0/iter-0/rms/model"
    rmspath.mkdir(parents=True, exist_ok=True)
    logger.info("Active folder is %s", rmspath)
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return rmspath


@pytest.fixture(name="rmssetup", scope="module", autouse=True)
def fixture_rmssetup(tmp_path_factory):
    """Create the folder structure to mimic RMS project."""

    tmppath = tmp_path_factory.mktemp("revision")
    rmspath = tmppath / "rms/model"
    rmspath.mkdir(parents=True, exist_ok=True)

    # copy a global config here
    shutil.copy(
        ROOTPWD / "tests/data/drogon/global_config2/global_variables.yml", rmspath
    )

    logger.info("Ran %s", inspect.currentframe().f_code.co_name)

    return rmspath


@pytest.fixture(name="rmsglobalconfig", scope="module", autouse=True)
def fixture_rmsglobalconfig(rmssetup):
    """Read global config."""
    # read the global config
    os.chdir(rmssetup)
    logger.info("Global config is %s", str(rmssetup / "global_variables.yml"))
    with open("global_variables.yml", "r", encoding="utf8") as stream:
        global_cfg = yaml.safe_load(stream)

    logger.info("Ran setup for %s", "rmsglobalconfig")
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return global_cfg


@pytest.fixture(name="casesetup", scope="module", autouse=True)
def fixture_casesetup(tmp_path_factory):
    """Create the folder structure to mimic a fmu run"""

    tmppath = tmp_path_factory.mktemp("mycase")
    tmppath = tmppath / "realization-0/iter-0"
    tmppath.mkdir(parents=True, exist_ok=True)

    logger.info("Ran %s", inspect.currentframe().f_code.co_name)

    return tmppath


@pytest.fixture(name="caseglobalconfig", scope="module", autouse=True)
def fixture_caseglobalconfig():
    """Create as global config for case testing."""
    gconfig = dict()
    gconfig["model"] = {"name": "Test", "revision": "21.0.0"}
    gconfig["masterdata"] = {
        "smda": {
            "country": [
                {"identifier": "Norway", "uuid": "ad214d85-8a1d-19da-e053-c918a4889309"}
            ],
            "discovery": [{"short_identifier": "abdcef", "uuid": "ghijk"}],
        }
    }
    gconfig["stratigraphy"] = {"TopVolantis": {}}
    gconfig["model"] = {"revision": "0.99.0"}
    gconfig["access"] = {"asset": "Drogon", "ssdl": "internal"}
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return gconfig


@pytest.fixture(name="globalconfig1", scope="module")
def fixture_globalconfig1():
    """Minimalistic global config variables no. 1 in ExportData class."""

    cfg = dict()

    cfg = dict()
    cfg["model"] = {"name": "Test", "revision": "AUTO"}
    cfg["stratigraphy"] = {
        "TopWhatever": {
            "stratigraphic": True,
            "name": "Whatever Top",
            "alias": ["TopDindong", "TopWhatever"],
        },
    }
    cfg["masterdata"] = {
        "smda": {
            "country": [
                {"identifier": "Norway", "uuid": "ad214d85-8a1d-19da-e053-c918a4889309"}
            ],
            "discovery": [{"short_identifier": "abdcef", "uuid": "ghijk"}],
        }
    }
    cfg["access"] = {
        "asset": {
            "name": "Test",
        },
        "ssdl": {
            "access_level": "internal",
            "rep_include": False,
        },
    }
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return cfg


@pytest.fixture(name="globalconfig_asfile", scope="module")
def fixture_globalconfig_asfile() -> str:
    """Global config as file for use with environment variable"""

    globalconfigfile = ROOTPWD / "tests/data/drogon/global_config2/global_variables.yml"

    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return str(globalconfigfile)


@pytest.fixture(name="internalcfg1", scope="module")
def fixture_internalcfg1(globalconfig1) -> dict:
    """Combined globalconfig1 and other settings; for internal testing"""
    logger.info("Establish internalcfg1")
    internalcfg1 = {}

    internalcfg1[G] = globalconfig1
    internalcfg1[S] = {"name": "TopWhatever", "content": "depth", "tagname": "mytag"}
    # class variables
    internalcfg1[C] = {
        "surface_fformat": "irap_binary",
        "createfolder": False,
        "verifyfolder": False,
    }

    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    # settings per instance
    return internalcfg1


@pytest.fixture(name="globalconfig2", scope="module")
def fixture_globalconfig2() -> dict:
    """More advanced global config from file state variable in ExportData class."""
    globvar = {}
    with open(
        ROOTPWD / "tests/data/drogon/global_config2/global_variables.yml", "r"
    ) as stream:
        globvar = yaml.safe_load(stream)

    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return globvar


@pytest.fixture(name="internalcfg2", scope="module")
def fixture_internalcfg2(globalconfig2):
    """Combined globalconfig2 and other settings; NB for internal unit testing"""
    internalcfg2 = {}

    internalcfg2[G] = globalconfig2

    # class variables
    internalcfg2[C] = {
        "surface_fformat": "irap_binary",
        "createfolder": False,
        "verifyfolder": False,
    }

    # settings per instance
    internalcfg2[S] = {
        "content": "depth",
        "name": "TopVolantis",
        "unit": "m",
        "tagname": "mytag",
        "parentname": "",
        "basepath": Path("."),
        "pwd": Path("."),
        "time1": "",
        "time2": "",
        "is_prediction": True,
        "is_observation": False,
        "forcefolder": None,
        "subfolder": "",
    }
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return internalcfg2


# ======================================================================================
# Various objects
# ======================================================================================


@pytest.fixture(name="regsurf", scope="module", autouse=True)
def fixture_regsurf():
    """Create an xtgeo surface."""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return xtgeo.RegularSurface(ncol=12, nrow=10, xinc=20, yinc=20, values=1234.0)
