"""The conftest.py, providing magical fixtures to tests."""

import inspect
import json
import logging
import os
import shutil
from pathlib import Path

import fmu.dataio as dio
import numpy as np
import pandas as pd
import pytest
import xtgeo
import yaml
from fmu.config import utilities as ut
from fmu.dataio.dataio import ExportData, read_metadata
from fmu.dataio.datastructure.configuration import global_configuration
from fmu.dataio.providers._fmu import FmuEnv

from .utils import _metadata_examples

logger = logging.getLogger(__name__)

ERTRUN = "tests/data/drogon/ertrun1"
ERTRUN_NO_ITER = "tests/data/drogon/ertrun1_no_iter"
ERTRUN_REAL0_ITER0 = f"{ERTRUN}/realization-0/iter-0"
ERTRUN_PRED = f"{ERTRUN}/realization-0/pred"

ERTRUN_ENV_PREHOOK = {
    f"_ERT_{FmuEnv.EXPERIMENT_ID.name}": "6a8e1e0f-9315-46bb-9648-8de87151f4c7",
    f"_ERT_{FmuEnv.ENSEMBLE_ID.name}": "b027f225-c45d-477d-8f33-73695217ba14",
    f"_ERT_{FmuEnv.SIMULATION_MODE.name}": "test_run",
}
ERTRUN_ENV_FORWARD = {
    f"_ERT_{FmuEnv.ITERATION_NUMBER.name}": "0",
    f"_ERT_{FmuEnv.REALIZATION_NUMBER.name}": "0",
    f"_ERT_{FmuEnv.RUNPATH.name}": "---",  # set dynamically due to pytest tmp rotation
}
ERTRUN_ENV_FULLRUN = {**ERTRUN_ENV_PREHOOK, **ERTRUN_ENV_FORWARD}

ERT_RUNPATH = f"_ERT_{FmuEnv.RUNPATH.name}"


def _current_function_name():
    """Helper to retrieve current function name, e.g. for logging"""
    return inspect.currentframe().f_back.f_code.co_name


@pytest.fixture
def set_export_data_inside_rms(monkeypatch):
    monkeypatch.setattr(ExportData, "_inside_rms", True)


@pytest.fixture
def set_environ_inside_rms(monkeypatch):
    monkeypatch.setattr("fmu.dataio._utils.detect_inside_rms", lambda: True)


@pytest.fixture(scope="session")
def rootpath(request):
    return request.config.rootpath


def _fmu_run1_env_variables(monkeypatch, usepath="", case_only=False):
    """Helper function for fixtures below.

    Will here monkeypatch the ENV variables, with a particular setting for RUNPATH
    (trough `usepath`) which may vary dynamically due to pytest tmp area rotation.
    """
    env = ERTRUN_ENV_FULLRUN if not case_only else ERTRUN_ENV_PREHOOK
    for key, value in env.items():
        env_value = str(usepath) if "RUNPATH" in key else value
        monkeypatch.setenv(key, env_value)
        logger.debug("Setting env %s as %s", key, env_value)


def remove_ert_env(monkeypatch):
    for key in ERTRUN_ENV_FULLRUN:
        monkeypatch.delenv(key, raising=False)


def set_ert_env_forward(monkeypatch):
    for key, val in ERTRUN_ENV_FORWARD.items():
        monkeypatch.setenv(key, val)


def set_ert_env_prehook(monkeypatch):
    for key, val in ERTRUN_ENV_PREHOOK.items():
        monkeypatch.setenv(key, val)


@pytest.fixture(scope="function")
def fmurun(tmp_path_factory, monkeypatch, rootpath):
    """A tmp folder structure for testing; here a new fmurun without case metadata."""
    tmppath = tmp_path_factory.mktemp("data")
    newpath = tmppath / ERTRUN_REAL0_ITER0
    shutil.copytree(rootpath / ERTRUN_REAL0_ITER0, newpath)

    _fmu_run1_env_variables(monkeypatch, usepath=newpath, case_only=False)

    logger.debug("Ran %s", _current_function_name())
    return newpath


@pytest.fixture(name="fmurun_prehook", scope="function")
def fixture_fmurun_prehook(tmp_path_factory, monkeypatch, rootpath):
    """A tmp folder structure for testing; here a new fmurun without case metadata."""
    tmppath = tmp_path_factory.mktemp("data")
    newpath = tmppath / ERTRUN
    shutil.copytree(rootpath / ERTRUN, newpath)

    _fmu_run1_env_variables(monkeypatch, usepath=newpath, case_only=True)

    logger.debug("Ran %s", _current_function_name())
    return newpath


@pytest.fixture(name="fmurun_w_casemetadata", scope="function")
def fixture_fmurun_w_casemetadata(tmp_path_factory, monkeypatch, rootpath):
    """Create a tmp folder structure for testing; here existing fmurun w/ case meta!"""
    tmppath = tmp_path_factory.mktemp("data3")
    newpath = tmppath / ERTRUN
    shutil.copytree(rootpath / ERTRUN, newpath)
    rootpath = newpath / "realization-0/iter-0"

    _fmu_run1_env_variables(monkeypatch, usepath=rootpath, case_only=False)

    logger.debug("Ran %s", _current_function_name())
    return rootpath


@pytest.fixture(name="fmurun_non_equal_real_and_iter", scope="function")
def fixture_fmurun_non_equal_real_and_iter(tmp_path_factory, monkeypatch, rootpath):
    """Create a tmp folder structure for testing; with non equal real and iter num!"""
    tmppath = tmp_path_factory.mktemp("data3")
    newpath = tmppath / ERTRUN
    shutil.copytree(rootpath / ERTRUN, newpath)
    rootpath = newpath / "realization-1/iter-0"

    monkeypatch.setenv(f"_ERT_{FmuEnv.ITERATION_NUMBER.name}", "0")
    monkeypatch.setenv(f"_ERT_{FmuEnv.REALIZATION_NUMBER.name}", "1")
    monkeypatch.setenv(f"_ERT_{FmuEnv.RUNPATH.name}", str(rootpath))

    logger.debug("Ran %s", _current_function_name())
    return rootpath


@pytest.fixture(name="fmurun_no_iter_folder", scope="function")
def fixture_fmurun_no_iter_folder(tmp_path_factory, monkeypatch, rootpath):
    """Create a tmp folder structure for testing; with no iter folder!"""
    tmppath = tmp_path_factory.mktemp("data3")
    newpath = tmppath / ERTRUN_NO_ITER
    shutil.copytree(rootpath / ERTRUN_NO_ITER, newpath)
    rootpath = newpath / "realization-1"

    monkeypatch.setenv(f"_ERT_{FmuEnv.ITERATION_NUMBER.name}", "0")
    monkeypatch.setenv(f"_ERT_{FmuEnv.REALIZATION_NUMBER.name}", "1")
    monkeypatch.setenv(f"_ERT_{FmuEnv.RUNPATH.name}", str(rootpath))

    logger.debug("Ran %s", _current_function_name())
    return rootpath


@pytest.fixture(name="fmurun_w_casemetadata_pred", scope="function")
def fixture_fmurun_w_casemetadata_pred(tmp_path_factory, monkeypatch, rootpath):
    """Create a tmp folder structure for testing; here existing fmurun w/ case meta!"""
    tmppath = tmp_path_factory.mktemp("data3")
    newpath = tmppath / ERTRUN
    shutil.copytree(rootpath / ERTRUN, newpath)
    rootpath = newpath / "realization-0/pred"

    _fmu_run1_env_variables(monkeypatch, usepath=rootpath, case_only=False)

    logger.debug("Ran %s", _current_function_name())
    return rootpath


@pytest.fixture(name="fmurun_pred", scope="session")
def fixture_fmurun_pred(tmp_path_factory, rootpath):
    """Create a tmp folder structure for testing; here a new fmurun for prediction."""
    tmppath = tmp_path_factory.mktemp("data_pred")
    newpath = tmppath / ERTRUN_PRED
    shutil.copytree(rootpath / ERTRUN_PRED, newpath)
    logger.debug("Ran %s", _current_function_name())
    return newpath


@pytest.fixture(name="rmsrun_fmu_w_casemetadata", scope="session")
def fixture_rmsrun_fmu_w_casemetadata(tmp_path_factory, rootpath):
    """Create a tmp folder structure for testing; here existing fmurun w/ case meta!

    Then we locate the folder to the ...rms/model folder, pretending running RMS
    in a FMU setup where case metadata are present
    """
    tmppath = tmp_path_factory.mktemp("data3")
    newpath = tmppath / ERTRUN
    shutil.copytree(rootpath / ERTRUN, newpath)
    rmspath = newpath / "realization-0/iter-0/rms/model"
    rmspath.mkdir(parents=True, exist_ok=True)
    logger.debug("Active folder is %s", rmspath)
    logger.debug("Ran %s", _current_function_name())
    return rmspath


@pytest.fixture(scope="module")
def rmssetup(tmp_path_factory, global_config2_path):
    """Create the folder structure to mimic RMS project."""

    tmppath = tmp_path_factory.mktemp("revision")
    rmspath = tmppath / "rms/model"
    rmspath.mkdir(parents=True, exist_ok=True)
    shutil.copy(global_config2_path, rmspath)

    logger.debug("Ran %s", _current_function_name())

    return rmspath


@pytest.fixture(name="rmsglobalconfig", scope="module")
def fixture_rmsglobalconfig(rmssetup):
    """Read global config."""
    # read the global config
    os.chdir(rmssetup)
    logger.debug("Global config is %s", str(rmssetup / "global_variables.yml"))
    with open("global_variables.yml", encoding="utf8") as stream:
        global_cfg = yaml.safe_load(stream)

    logger.debug("Ran setup for %s", "rmsglobalconfig")
    logger.debug("Ran %s", _current_function_name())
    return global_cfg


@pytest.fixture(name="globalvars_norwegian_letters", scope="module")
def fixture_globalvars_norwegian_letters(tmp_path_factory, rootpath):
    """Read a global config with norwegian special letters w/ fmu.config utilities."""

    tmppath = tmp_path_factory.mktemp("revisionxx")
    rmspath = tmppath / "rms/model"
    rmspath.mkdir(parents=True, exist_ok=True)

    gname = "global_variables_norw_letters.yml"

    # copy a global config with nowr letters here
    shutil.copy(
        rootpath / "tests/data/drogon/global_config2" / gname,
        rmspath,
    )

    os.chdir(rmspath)
    cfg = ut.yaml_load(rmspath / gname)

    return (rmspath, cfg, gname)


@pytest.fixture(name="casesetup", scope="module")
def fixture_casesetup(tmp_path_factory):
    """Create the folder structure to mimic a fmu run"""

    tmppath = tmp_path_factory.mktemp("mycase")
    tmppath = tmppath / "realization-0/iter-0"
    tmppath.mkdir(parents=True, exist_ok=True)

    logger.debug("Ran %s", _current_function_name())

    return tmppath


@pytest.fixture(name="globalconfig1", scope="module")
def fixture_globalconfig1():
    """Minimalistic global config variables no. 1 in ExportData class."""
    return global_configuration.GlobalConfiguration(
        masterdata=global_configuration.meta.Masterdata(
            smda=global_configuration.meta.Smda(
                coordinate_system=global_configuration.meta.CoordinateSystem(
                    identifier="ST_WGS84_UTM37N_P32637",
                    uuid="15ce3b84-766f-4c93-9050-b154861f9100",
                ),
                country=[
                    global_configuration.meta.CountryItem(
                        identifier="Norway",
                        uuid="ad214d85-8a1d-19da-e053-c918a4889309",
                    ),
                ],
                discovery=[
                    global_configuration.meta.DiscoveryItem(
                        short_identifier="abdcef",
                        uuid="56c92484-8798-4f1f-9f14-d237a3e1a4ff",
                    ),
                ],
                stratigraphic_column=global_configuration.meta.StratigraphicColumn(
                    identifier="TestStratigraphicColumn",
                    uuid="56c92484-8798-4f1f-9f14-d237a3e1a4ff",
                ),
                field=[],
            )
        ),
        access=global_configuration.Access(
            asset=global_configuration.Asset(name="Test"),
            ssdl=global_configuration.Ssdl(rep_include=False),
            classification=global_configuration.enums.AccessLevel.internal,
        ),
        model=global_configuration.Model(
            name="Test",
            revision="AUTO",
        ),
        stratigraphy=global_configuration.Stratigraphy(
            root={
                "TopWhatever": global_configuration.StratigraphyElement(
                    name="Whatever Top",
                    stratigraphic=True,
                    alias=["TopDindong", "TopWhatever"],
                )
            }
        ),
    ).model_dump(exclude_none=True)


@pytest.fixture(scope="module")
def global_config2_path(rootpath) -> Path:
    """The path to the second global config."""
    return rootpath / "tests/data/drogon/global_config2/global_variables.yml"


@pytest.fixture(name="edataobj1", scope="module")
def fixture_edataobj1(globalconfig1):
    """Combined globalconfig and settings to instance, for internal testing"""
    logger.debug("Establish edataobj1")

    eobj = dio.ExportData(
        config=globalconfig1,
        name="TopWhatever",
        content="depth",
        tagname="mytag",
        is_observation=False,
    )
    eobj.surface_fformat = "irap_binary"

    logger.debug(
        "Ran %s returning %s", inspect.currentframe().f_code.co_name, type(eobj)
    )
    return eobj


@pytest.fixture(scope="module")
def globalconfig2(global_config2_path) -> dict:
    """More advanced global config from file state variable in ExportData class."""
    with open(global_config2_path, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


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
    eobj.legacy_time_format = False

    eobj._rootpath = Path(".")
    eobj._pwd = Path(".")

    logger.debug("Ran %s", _current_function_name())
    return eobj


# ======================================================================================
# Schema
# ======================================================================================


@pytest.fixture(scope="session")
def schema_080(rootpath):
    """Return 0.8.0 version of schema as json."""
    with open(
        rootpath / "schema/definitions/0.8.0/schema/fmu_results.json", encoding="utf-8"
    ) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def metadata_examples():
    """Parse all metadata examples.

    Returns:
        Dict: Dictionary with filename as key, file contents as value.

    """
    return _metadata_examples()


@pytest.fixture(name="regsurf_nan_only", scope="module")
def fixture_regsurf_nan_only():
    """Create an xtgeo surface with only NaNs."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.RegularSurface(ncol=12, nrow=10, xinc=20, yinc=20, values=np.nan)


@pytest.fixture(name="regsurf_masked_only", scope="module")
def fixture_regsurf_masked_only():
    """Create an xtgeo surface with only masked values."""
    logger.debug("Ran %s", _current_function_name())
    regsurf = xtgeo.RegularSurface(ncol=12, nrow=10, xinc=20, yinc=20, values=1000)
    regsurf.values = np.ma.masked_array(regsurf.values, mask=True)
    return regsurf


# ======================================================================================
# Various objects
# ======================================================================================


@pytest.fixture(name="regsurf", scope="module")
def fixture_regsurf():
    """Create an xtgeo surface."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.RegularSurface(ncol=12, nrow=10, xinc=20, yinc=20, values=1234.0)


@pytest.fixture(name="polygons", scope="module")
def fixture_polygons():
    """Create an xtgeo polygons."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.Polygons(
        [
            [1, 22, 3, 0],
            [6, 25, 4, 0],
            [8, 27, 6, 0],
            [1, 22, 3, 0],
        ]
    )


@pytest.fixture(name="points", scope="module")
def fixture_points():
    """Create an xtgeo points instance."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.Points(
        [
            [1, 22, 3, "WELLA"],
            [6, 25, 4, "WELLB"],
            [8, 27, 6, "WELLB"],
            [1, 22, 3, "WELLC"],
        ],
        attributes={"WellName": "str"},
    )


@pytest.fixture(name="cube", scope="module")
def fixture_cube():
    """Create an xtgeo cube instance."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.Cube(ncol=3, nrow=4, nlay=5, xinc=12, yinc=12, zinc=4, rotation=30)


@pytest.fixture(name="grid", scope="module")
def fixture_grid():
    """Create an xtgeo grid instance."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.create_box_grid((3, 4, 5))


@pytest.fixture(name="gridproperty", scope="module")
def fixture_gridproperty():
    """Create an xtgeo gridproperty instance."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.GridProperty(ncol=3, nrow=7, nlay=3, values=123.0)


@pytest.fixture(name="dataframe", scope="module")
def fixture_dataframe():
    """Create an pandas dataframe instance."""
    logger.debug("Ran %s", _current_function_name())
    return pd.DataFrame({"COL1": [1, 2, 3, 4], "COL2": [99.0, 98.0, 97.0, 96.0]})


@pytest.fixture(name="wellpicks", scope="module")
def fixture_wellpicks():
    """Create a pandas dataframe containing wellpicks"""
    logger.debug("Ran %s", _current_function_name())
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


@pytest.fixture(name="arrowtable", scope="module")
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


# helper function for the two fixtures below
def _create_aggregated_surface_dataset(rmsglobalconfig, regsurf, content):
    edata = dio.ExportData(
        config=rmsglobalconfig,  # read from global config
        content=content,
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
    return surfs, metas


@pytest.fixture(name="aggr_sesimic_surfs_mean", scope="function")
def fixture_aggr_seismic_surfs_mean(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Create aggregated surfaces, and return aggr. mean surface + lists of metadata"""
    logger.debug("Ran %s", _current_function_name())

    origfolder = os.getcwd()
    os.chdir(fmurun_w_casemetadata)

    surfs, metas = _create_aggregated_surface_dataset(
        rmsglobalconfig, regsurf, content={"seismic": {"attribute": "amplitude"}}
    )

    aggregated = surfs.statistics()
    logger.debug(
        "Aggr. mean is %s", aggregated["mean"].values.mean()
    )  # shall be 1238.5

    os.chdir(origfolder)

    return (aggregated["mean"], metas)


@pytest.fixture(name="aggr_surfs_mean", scope="function")
def fixture_aggr_surfs_mean(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Create aggregated surfaces, and return aggr. mean surface + lists of metadata"""
    logger.debug("Ran %s", _current_function_name())

    origfolder = os.getcwd()
    os.chdir(fmurun_w_casemetadata)

    surfs, metas = _create_aggregated_surface_dataset(
        rmsglobalconfig, regsurf, content="depth"
    )

    aggregated = surfs.statistics()
    logger.debug(
        "Aggr. mean is %s", aggregated["mean"].values.mean()
    )  # shall be 1238.5

    os.chdir(origfolder)

    return (aggregated["mean"], metas)


@pytest.fixture(name="edataobj3")
def fixture_edataobj3(globalconfig1):
    """Combined globalconfig and settings to instance, for internal testing"""
    # logger.debug("Establish edataobj1")

    return ExportData(
        config=globalconfig1,
        name="summary",
        content="timeseries",
        tagname="",
    )


@pytest.fixture(name="mock_summary")
def fixture_summary():
    """Return summary mock data

    Returns:
        pd.DataFram: dummy data
    """
    return pd.DataFrame({"alf": ["A", "B", "C"], "DATE": [1, 2, 3]})


@pytest.fixture(name="drogon_summary")
def fixture_drogon_sum(rootpath):
    """Return pyarrow table

    Returns:
        pa.Table: table with summary data
    """
    from pyarrow import feather

    return feather.read_table(rootpath / "tests/data/drogon/tabular/summary.arrow")


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
def fixture_drogon_volumes(rootpath):
    """Return pyarrow table

    Returns:
        pa.Table: table with summary data
    """
    from pyarrow import Table

    return Table.from_pandas(
        pd.read_csv(
            rootpath / "tests/data/drogon/tabular/geogrid--vol.csv",
        )
    )
