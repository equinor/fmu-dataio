"""The conftest.py, providing magical fixtures to tests."""
import contextlib
import datetime
import inspect
import json
import logging
import os
import shutil
from functools import wraps
from pathlib import Path

import fmu.dataio as dio
import pandas as pd
import pytest
import xtgeo
import yaml
from fmu.config import utilities as ut
from fmu.dataio.dataio import ExportData, read_metadata
from termcolor import cprint

logger = logging.getLogger(__name__)

ROOTPWD = Path(".").absolute()
RUN1 = "tests/data/drogon/ertrun1/realization-0/iter-0"
RUN2 = "tests/data/drogon/ertrun1"
RUN_PRED = "tests/data/drogon/ertrun1/realization-0/pred"


def pytest_configure():
    if "RMSVER" in os.environ and "INSIDE_RMS" not in os.environ:
        cprint(80 * "=", "red", attrs=["blink"])
        cprint(
            "You run a RMS python somehow; need to set INSIDE_RMS=0 for pytest:",
            "red",
            attrs=["blink"],
        )
        cprint("INSIDE_RMS=0 pytest", "red", attrs=["blink"])
        cprint(80 * "=", "red", attrs=["blink"])


@contextlib.contextmanager
def set_export_data_inside_rms_flag():
    old = ExportData._inside_rms
    ExportData._inside_rms = True
    try:
        yield
    finally:
        ExportData._inside_rms = old


@contextlib.contextmanager
def set_environ_inside_rms_flag():
    unset = object()
    old = os.environ.get("INSIDE_RMS", unset)
    os.environ["INSIDE_RMS"] = "1"
    try:
        yield
    finally:
        if old is unset:
            del os.environ["INSIDE_RMS"]
        else:
            os.environ["INSIDE_RMS"] = old


def inside_rms(func):
    """Decorator for being inside RMS"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with contextlib.ExitStack() as exitstack:
            exitstack.enter_context(set_environ_inside_rms_flag())
            exitstack.enter_context(set_export_data_inside_rms_flag())
            return func(*args, **kwargs)

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
    rootpath = newpath / "realization-0/iter-0"
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return rootpath


@pytest.fixture(name="fmurun_w_casemetadata_pred", scope="session", autouse=True)
def fixture_fmurun_w_casemetadata_pred(tmp_path_factory):
    """Create a tmp folder structure for testing; here existing fmurun w/ case meta!"""
    tmppath = tmp_path_factory.mktemp("data3")
    newpath = tmppath / RUN2
    shutil.copytree(ROOTPWD / RUN2, newpath)
    rootpath = newpath / "realization-0/pred"
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return rootpath


@pytest.fixture(name="fmurun_pred", scope="session", autouse=True)
def fixture_fmurun_pred(tmp_path_factory):
    """Create a tmp folder structure for testing; here a new fmurun for prediction."""
    tmppath = tmp_path_factory.mktemp("data_pred")
    newpath = tmppath / RUN_PRED
    shutil.copytree(ROOTPWD / RUN_PRED, newpath)
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return newpath


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
    with open("global_variables.yml", encoding="utf8") as stream:
        global_cfg = yaml.safe_load(stream)

    logger.info("Ran setup for %s", "rmsglobalconfig")
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return global_cfg


@pytest.fixture(name="globalvars_norw_letters", scope="module", autouse=True)
def fixture_globalvars_norw_letters(tmp_path_factory):
    """Read a global config with norwegian special letters w/ fmu.config utilities."""

    tmppath = tmp_path_factory.mktemp("revisionxx")
    rmspath = tmppath / "rms/model"
    rmspath.mkdir(parents=True, exist_ok=True)

    gname = "global_variables_norw_letters.yml"

    # copy a global config with nowr letters here
    shutil.copy(
        ROOTPWD / "tests/data/drogon/global_config2" / gname,
        rmspath,
    )

    os.chdir(rmspath)
    cfg = ut.yaml_load(rmspath / gname)

    return (rmspath, cfg, gname)


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
    gconfig = {}
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

    cfg = {}

    cfg = {}
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


@pytest.fixture(name="edataobj1", scope="module")
def fixture_edataobj1(globalconfig1):
    """Combined globalconfig and settings to instance, for internal testing"""
    logger.info("Establish edataobj1")

    eobj = dio.ExportData(
        config=globalconfig1,
        name="TopWhatever",
        content="depth",
        tagname="mytag",
        is_observation=False,
    )
    eobj.surface_fformat = "irap_binary"
    eobj.createfolder = False
    eobj.verifyfolder = False

    logger.info(
        "Ran %s returning %s", inspect.currentframe().f_code.co_name, type(eobj)
    )
    return eobj


@pytest.fixture(name="globalconfig2", scope="module")
def fixture_globalconfig2() -> dict:
    """More advanced global config from file state variable in ExportData class."""
    globvar = {}
    with open(
        ROOTPWD / "tests/data/drogon/global_config2/global_variables.yml",
        encoding="utf-8",
    ) as stream:
        globvar = yaml.safe_load(stream)

    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return globvar


@pytest.fixture(name="edataobj2", scope="function")
def fixture_edataobj2(globalconfig2):
    """Combined globalconfig2 and other settings; NB for internal unit testing"""
    eobj = dio.ExportData(
        config=globalconfig2,
        content="depth",
        name="TopVolantis",
        unit="m",
        tagname="mytag",
        parent="",
        timedata=[[20330105, "moni"], [19990102, "base"]],
        is_prediction=True,
        is_observation=False,
        forcefolder=None,
        subfolder="",
        fmu_context="realization",
    )

    eobj.surface_fformat = "irap_binary"
    eobj.createfolder = False
    eobj.verifyfolder = False
    eobj.legacy_time_format = False

    eobj._rootpath = Path(".")
    eobj._pwd = Path(".")

    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return eobj


# ======================================================================================
# Schema
# ======================================================================================


@pytest.fixture(name="schema_080", scope="session", autouse=True)
def fixture_schema_080():
    """Return 0.8.0 version of schema as json."""

    return _parse_json(ROOTPWD / "schema/definitions/0.8.0/schema/fmu_results.json")


@pytest.fixture(name="metadata_examples", scope="session", autouse=True)
def fixture_metadata_examples():
    """Parse all metadata examples.

    Returns:
        Dict: Dictionary with filename as key, file contents as value.

    """

    # hard code 0.8.0 for now
    return {
        path.name: _isoformat_all_datetimes(_parse_yaml(str(path)))
        for path in ROOTPWD.glob("schema/definitions/0.8.0/examples/*.yml")
    }


# ======================================================================================
# Various objects
# ======================================================================================


@pytest.fixture(name="regsurf", scope="module", autouse=True)
def fixture_regsurf():
    """Create an xtgeo surface."""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return xtgeo.RegularSurface(ncol=12, nrow=10, xinc=20, yinc=20, values=1234.0)


@pytest.fixture(name="polygons", scope="module", autouse=True)
def fixture_polygons():
    """Create an xtgeo polygons."""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return xtgeo.Polygons(
        [
            [1, 22, 3, 0],
            [6, 25, 4, 0],
            [8, 27, 6, 0],
            [1, 22, 3, 0],
        ]
    )


@pytest.fixture(name="points", scope="module", autouse=True)
def fixture_points():
    """Create an xtgeo points instance."""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return xtgeo.Points(
        [
            [1, 22, 3, "WELLA"],
            [6, 25, 4, "WELLB"],
            [8, 27, 6, "WELLB"],
            [1, 22, 3, "WELLC"],
        ],
        attributes={"WellName": "str"},
    )


@pytest.fixture(name="cube", scope="module", autouse=True)
def fixture_cube():
    """Create an xtgeo cube instance."""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return xtgeo.Cube(ncol=3, nrow=4, nlay=5, xinc=12, yinc=12, zinc=4, rotation=30)


@pytest.fixture(name="grid", scope="module", autouse=True)
def fixture_grid():
    """Create an xtgeo grid instance."""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return xtgeo.create_box_grid((3, 4, 5))


@pytest.fixture(name="gridproperty", scope="module", autouse=True)
def fixture_gridproperty():
    """Create an xtgeo gridproperty instance."""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return xtgeo.GridProperty(ncol=3, nrow=7, nlay=3, values=123.0)


@pytest.fixture(name="dataframe", scope="module", autouse=True)
def fixture_dataframe():
    """Create an pandas dataframe instance."""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return pd.DataFrame({"COL1": [1, 2, 3, 4], "COL2": [99.0, 98.0, 97.0, 96.0]})


@pytest.fixture(name="wellpicks", scope="module", autouse=True)
def fixture_wellpicks():
    """Create a pandas dataframe containing wellpicks"""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)
    return pd.DataFrame(
        {
            "X_UTME": [
                46123.45,
                46124.56,
                46125.67,
            ],
            "Y_UTMN": [
                5931123.45,
                5931124.56,
                5931125.78,
            ],
            "Z_TVDSS": [
                0.0,
                10.0,
                22.2,
            ],
            "MD": [
                0.1,
                10.1,
                10323323.83223,
            ],
            "WELL": ["55_33-A-6", "55_34-B-7", "55_34-B-7"],
            "HORIZON": ["MSL", "TopTherys", "TopVolantis"],
        }
    )


@pytest.fixture(name="arrowtable", scope="module", autouse=True)
def fixture_arrowtable():
    """Create an arrow table instance."""
    try:
        from pyarrow import Table

        return Table.from_pandas(
            pd.DataFrame(
                {
                    "COL1": [1, 2, 3, 4],
                    "COL2": [99.0, 98.0, 97.0, 96.0],
                }
            )
        )
    except ImportError:
        return None


@pytest.fixture(name="aggr_surfs_mean", scope="module", autouse=True)
def fixture_aggr_surfs_mean(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Create aggregated surfaces, and return aggr. mean surface + lists of metadata"""
    logger.info("Ran %s", inspect.currentframe().f_code.co_name)

    origfolder = os.getcwd()
    os.chdir(fmurun_w_casemetadata)

    edata = dio.ExportData(
        config=rmsglobalconfig,  # read from global config
        content="depth",
    )

    aggs = []
    # create "forward" files
    for i in range(10):  # TODO! 10
        use_regsurf = regsurf.copy()
        use_regsurf.values += float(i)
        expfile = edata.export(use_regsurf, name="mymap_" + str(i), realization=i)
        aggs.append(expfile)

    # next task is to do an aggradation, and now the metadata already exists
    # per input element which shall be re-used
    surfs = xtgeo.Surfaces()
    metas = []
    for mapfile in aggs:
        surf = xtgeo.surface_from_file(mapfile)
        meta = read_metadata(mapfile)

        metas.append(meta)
        surfs.append([surf])

    aggregated = surfs.statistics()
    logger.info("Aggr. mean is %s", aggregated["mean"].values.mean())  # shall be 1238.5

    os.chdir(origfolder)

    return (aggregated["mean"], metas)


@pytest.fixture(name="edataobj3")
def fixture_edataobj3(globalconfig1):
    """Combined globalconfig and settings to instance, for internal testing"""
    # logger.info("Establish edataobj1")

    return ExportData(
        config=globalconfig1, name="summary", content="timeseries", tagname=""
    )


@pytest.fixture(name="mock_summary")
def fixture_summary():
    """Return summary mock data

    Returns:
        pd.DataFram: dummy data
    """
    return pd.DataFrame({"alf": ["A", "B", "C"], "DATE": [1, 2, 3]})


@pytest.fixture(name="drogon_summary")
def fixture_drogon_sum():
    """Return pyarrow table

    Returns:
        pa.Table: table with summary data
    """
    from pyarrow import feather

    path = ROOTPWD / "tests/data/drogon/tabular/summary.arrow"
    return feather.read_table(path)


@pytest.fixture(name="mock_volumes")
def fixture_mock_volumes():
    """Return volume mock data

    Returns:
        pd.DataFrame: dummy data
    """
    return pd.DataFrame(
        {
            "ZONE": ["B", "A", "C"],
            "LICENCE": ["L3", "L2", "L1"],
            "nums": [1, 2, 3],
            "OTHER": ["q", "a", "f"],
        }
    )


@pytest.fixture(name="drogon_volumes")
def fixture_drogon_volumes():
    """Return pyarrow table

    Returns:
        pa.Table: table with summary data
    """
    from pyarrow import Table

    return Table.from_pandas(
        pd.read_csv(
            ROOTPWD / "tests/data/drogon/tabular/geogrid--vol.csv",
        )
    )


# ======================================================================================
# Utilities
# ======================================================================================


def _parse_json(schema_path):
    """Parse the schema, return JSON"""
    with open(schema_path, encoding="utf-8") as stream:
        return json.load(stream)


def _parse_yaml(yaml_path):
    """Parse the filename as json, return data"""
    with open(yaml_path, encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    return _isoformat_all_datetimes(data)


def _isoformat_all_datetimes(indate):
    """Recursive function to isoformat all datetimes in a dictionary"""

    if isinstance(indate, list):
        return [_isoformat_all_datetimes(i) for i in indate]

    if isinstance(indate, dict):
        return {key: _isoformat_all_datetimes(indate[key]) for key in indate}

    if isinstance(indate, (datetime.datetime, datetime.date)):
        return indate.isoformat()

    return indate
