"""The conftest.py, providing magical fixtures to tests."""

import inspect
import logging
import shutil
import sys
import uuid
from collections.abc import Callable, Generator
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pytest
import xtgeo
import yaml
from fmu.datamodels.common.access import Asset
from fmu.datamodels.common.masterdata import (
    CoordinateSystem,
    CountryItem,
    DiscoveryItem,
    Masterdata,
    Smda,
    StratigraphicColumn,
)
from fmu.datamodels.fmu_results import fields, global_configuration
from pytest import MonkeyPatch

import fmu.dataio as dio
from fmu.dataio._readers.faultroom import FaultRoomSurface
from fmu.dataio._readers.tsurf import TSurfData
from fmu.dataio.dataio import ExportData

from .utils import _metadata_examples

logger = logging.getLogger(__name__)

ERTRUN = "tests/data/drogon/ertrun1"
ERTRUN_NO_ITER = "tests/data/drogon/ertrun1_no_iter"
ERTRUN_REAL0_ITER0 = f"{ERTRUN}/realization-0/iter-0"
ERTRUN_PRED = f"{ERTRUN}/realization-0/pred"

ERTRUN_ENV_PREHOOK = {
    "_ERT_EXPERIMENT_ID": "6a8e1e0f-9315-46bb-9648-8de87151f4c7",
    "_ERT_ENSEMBLE_ID": "b027f225-c45d-477d-8f33-73695217ba14",
    "_ERT_SIMULATION_MODE": "test_run",
}
ERTRUN_ENV_FORWARD = {
    "_ERT_ITERATION_NUMBER": "0",
    "_ERT_REALIZATION_NUMBER": "0",
    "_ERT_RUNPATH": "---",  # set dynamically due to pytest tmp rotation
}
ERTRUN_ENV_FULLRUN = {**ERTRUN_ENV_PREHOOK, **ERTRUN_ENV_FORWARD}

ERT_RUNPATH = "_ERT_RUNPATH"


def _current_function_name() -> str:
    """Helper to retrieve current function name, e.g. for logging"""
    curr_frame = inspect.currentframe()
    assert curr_frame is not None
    assert curr_frame.f_back is not None
    f_code = curr_frame.f_back.f_code
    assert f_code is not None
    co_name = f_code.co_name
    assert co_name is not None
    return co_name


@pytest.fixture(scope="session")
def rootpath(request: pytest.FixtureRequest) -> Path:
    return request.config.rootpath


@pytest.fixture
def inside_rms_interactive(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("RUNRMS_EXEC_MODE", "interactive")


def _set_fmurun_env_variables(
    monkeypatch: MonkeyPatch,
    runpath: Path = Path(""),
    case_only: bool = False,
) -> None:
    """Set Ert environment variables based upon the path and stage."""
    env = ERTRUN_ENV_FULLRUN if not case_only else ERTRUN_ENV_PREHOOK

    for key, value in env.items():
        env_value = str(runpath) if "RUNPATH" in key else value
        monkeypatch.setenv(key, env_value)
        logger.debug("Setting env %s as %s", key, env_value)


@pytest.fixture
def remove_ert_env(monkeypatch: MonkeyPatch) -> Callable[[], None]:
    def _remove_ert_env() -> None:
        for key in ERTRUN_ENV_FULLRUN:
            monkeypatch.delenv(key, raising=False)

    return _remove_ert_env


@pytest.fixture
def set_ert_env_forward(monkeypatch: MonkeyPatch) -> Callable[[], None]:
    def _set_ert_env_forward() -> None:
        for key, val in ERTRUN_ENV_FORWARD.items():
            monkeypatch.setenv(key, val)

    return _set_ert_env_forward


@pytest.fixture
def set_ert_env_prehook(monkeypatch: MonkeyPatch) -> Callable[[], None]:
    def _set_ert_env_prehook() -> None:
        for key, val in ERTRUN_ENV_PREHOOK.items():
            monkeypatch.setenv(key, val)

    return _set_ert_env_prehook


@pytest.fixture(scope="function")
def runpath_no_case_metadata(
    tmp_path: Path, monkeypatch: MonkeyPatch, rootpath: Path
) -> Path:
    """A standard runpath without metadata exported in the case path."""
    runpath = tmp_path / ERTRUN_REAL0_ITER0
    shutil.copytree(rootpath / ERTRUN_REAL0_ITER0, runpath)

    _set_fmurun_env_variables(monkeypatch, runpath=runpath)

    monkeypatch.chdir(runpath)
    return runpath


@pytest.fixture(scope="function")
def runpath_prehook(tmp_path: Path, monkeypatch: MonkeyPatch, rootpath: Path) -> Path:
    """Runpath mocking a prehook context."""
    runpath = tmp_path / ERTRUN
    shutil.copytree(rootpath / ERTRUN, runpath)

    _set_fmurun_env_variables(monkeypatch, runpath=runpath, case_only=True)

    monkeypatch.chdir(runpath)
    return runpath


@pytest.fixture(scope="function")
def runpath_no_dotfmu(tmp_path: Path, monkeypatch: MonkeyPatch, rootpath: Path) -> Path:
    """Runpath mocking an FMU run without a .fmu/ directory."""
    runpath = tmp_path / ERTRUN
    shutil.copytree(rootpath / ERTRUN, runpath)
    iter_path = runpath / "realization-0/iter-0"

    _set_fmurun_env_variables(monkeypatch, runpath=iter_path)

    monkeypatch.chdir(iter_path)
    return iter_path


@pytest.fixture(scope="function")
def runpath_non_equal_real_and_iter(
    tmp_path: Path, monkeypatch: MonkeyPatch, rootpath: Path
) -> Path:
    """Runpath with non-equal real and iter num."""
    runpath = tmp_path / ERTRUN
    shutil.copytree(rootpath / ERTRUN, runpath)
    rootpath = runpath / "realization-1/iter-0"

    monkeypatch.setenv("_ERT_ITERATION_NUMBER", "0")
    monkeypatch.setenv("_ERT_REALIZATION_NUMBER", "1")
    monkeypatch.setenv("_ERT_RUNPATH", str(rootpath))

    monkeypatch.chdir(rootpath)
    return rootpath


@pytest.fixture(scope="function")
def runpath_no_iter_dir(
    tmp_path: Path, monkeypatch: MonkeyPatch, rootpath: Path
) -> Path:
    """Runpath without an iter dir."""
    runpath = tmp_path / ERTRUN_NO_ITER
    shutil.copytree(rootpath / ERTRUN_NO_ITER, runpath)
    rootpath = runpath / "realization-1"

    monkeypatch.setenv("_ERT_ITERATION_NUMBER", "0")
    monkeypatch.setenv("_ERT_REALIZATION_NUMBER", "1")
    monkeypatch.setenv("_ERT_RUNPATH", str(rootpath))

    monkeypatch.chdir(rootpath)
    return rootpath


@pytest.fixture(scope="function")
def runpath_no_dotfmu_pred(
    tmp_path: Path, monkeypatch: MonkeyPatch, rootpath: Path
) -> Path:
    """Prediction runpath with no .fmu/ dir."""
    runpath = tmp_path / ERTRUN
    shutil.copytree(rootpath / ERTRUN, runpath)
    rootpath = runpath / "realization-0/pred"

    _set_fmurun_env_variables(monkeypatch, runpath=rootpath)

    monkeypatch.chdir(rootpath)
    return rootpath


@pytest.fixture(scope="function")
def runpath_pred_files(tmp_path: Path, rootpath: Path) -> Path:
    """Copies prediction run files into the tmp path.

    Typically used in combination with another runpath fixture."""
    runpath = tmp_path / ERTRUN_PRED
    shutil.copytree(rootpath / ERTRUN_PRED, runpath, dirs_exist_ok=True)
    return runpath


@pytest.fixture(scope="function")
def drogon_global_config_path(rootpath: Path) -> Path:
    """The path to the Drogon's global config."""
    return rootpath / "tests/data/drogon/global_config/global_variables.yml"


@pytest.fixture(scope="function")
def rmssetup(
    tmp_path_factory: pytest.TempPathFactory, drogon_global_config_path: Path
) -> Path:
    """Create the folder structure to mimic RMS project."""

    tmppath = tmp_path_factory.mktemp("revision")
    rmspath = tmppath / "rms/model"
    rmspath.mkdir(parents=True, exist_ok=True)
    shutil.copy(drogon_global_config_path, rmspath)

    logger.debug("Ran %s", _current_function_name())

    return rmspath


@pytest.fixture(scope="function")
def rmssetup_with_fmuconfig(
    tmp_path_factory: pytest.TempPathFactory, drogon_global_config_path: Path
) -> Path:
    """Create the folder structure to mimic RMS project and standard global config."""

    tmppath = tmp_path_factory.mktemp("revision")
    rmspath = tmppath / "rms/model"
    rmspath.mkdir(parents=True, exist_ok=True)
    fmuconfigpath = tmppath / "fmuconfig/output"
    fmuconfigpath.mkdir(parents=True, exist_ok=True)
    shutil.copy(drogon_global_config_path, fmuconfigpath)

    logger.debug("Ran %s", _current_function_name())

    return rmspath


@pytest.fixture(scope="function")
def rmsglobalconfig(rmssetup: Path, monkeypatch: MonkeyPatch) -> dict[str, Any]:
    """Read global config."""
    monkeypatch.chdir(rmssetup)
    logger.debug("Global config is %s", str(rmssetup / "global_variables.yml"))
    with open("global_variables.yml", encoding="utf8") as stream:
        global_cfg = yaml.safe_load(stream)

    logger.debug("Ran setup for %s", "rmsglobalconfig")
    logger.debug("Ran %s", _current_function_name())
    return global_cfg


@pytest.fixture(scope="function")
def mock_global_config_validated() -> global_configuration.GlobalConfiguration:
    """Minimalistic global config variables no. 1 in ExportData class."""
    return global_configuration.GlobalConfiguration(
        masterdata=Masterdata(
            smda=Smda(
                coordinate_system=CoordinateSystem(
                    identifier="ST_WGS84_UTM37N_P32637",
                    uuid=uuid.UUID("15ce3b84-766f-4c93-9050-b154861f9100"),
                ),
                country=[
                    CountryItem(
                        identifier="Norway",
                        uuid=uuid.UUID("ad214d85-8a1d-19da-e053-c918a4889309"),
                    ),
                ],
                discovery=[
                    DiscoveryItem(
                        short_identifier="abdcef",
                        uuid=uuid.UUID("56c92484-8798-4f1f-9f14-d237a3e1a4ff"),
                    ),
                ],
                stratigraphic_column=StratigraphicColumn(
                    identifier="TestStratigraphicColumn",
                    uuid=uuid.UUID("56c92484-8798-4f1f-9f14-d237a3e1a4ff"),
                ),
                field=[],
            )
        ),
        access=global_configuration.Access(
            asset=Asset(name="Test"),
            classification=global_configuration.Classification.internal,
        ),
        model=fields.Model(
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
    )


@pytest.fixture(scope="function")
def mock_global_config(
    mock_global_config_validated: global_configuration.GlobalConfiguration,
) -> dict[str, Any]:
    """Minimalistic global config variables no. 1 in ExportData class."""
    return mock_global_config_validated.model_dump(exclude_none=True)


@pytest.fixture(scope="function")
def mock_exportdata(
    mock_global_config: dict[str, Any], tmp_path: Path, monkeypatch: MonkeyPatch
) -> ExportData:
    """ExportData instance with a mock global configuration."""
    monkeypatch.chdir(tmp_path)
    return dio.ExportData(
        config=mock_global_config,
        name="TopWhatever",
        content="depth",
        tagname="mytag",
        is_observation=False,
    )


@pytest.fixture()
def simulationtimeseries_exportdata(mock_global_config: dict[str, Any]) -> ExportData:
    """ExportData instance with simulationtimeseries content type."""
    return ExportData(
        config=mock_global_config,
        name="summary",
        content="simulationtimeseries",
        tagname="",
    )


@pytest.fixture
def timeseries_exportdata(mock_global_config: dict[str, Any]) -> ExportData:
    """Combined globalconfig and settings to instance, for internal testing"""
    return ExportData(
        config=mock_global_config,
        name="some timeseries",
        content="timeseries",
        tagname="",
    )


@pytest.fixture(scope="function")
def drogon_global_config(drogon_global_config_path: Path) -> dict[str, Any]:
    """Drogon's global config from file state variable in ExportData class."""
    with open(drogon_global_config_path, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


@pytest.fixture(scope="function")
def drogon_exportdata(drogon_global_config: dict[str, Any]) -> ExportData:
    """ExportData instance with Drogon's global configuration."""
    return dio.ExportData(
        config=drogon_global_config,
        content="depth",
        name="TopVolantis",
        unit="m",
        tagname="mytag",
        parent="",
        timedata=[["20330105", "moni"], ["19990102", "base"]],
        is_prediction=True,
        is_observation=False,
        subfolder="",
        fmu_context="realization",
        rep_include=True,
    )


# ======================================================================================
# Schema
# ======================================================================================


@pytest.fixture(scope="session")
def metadata_examples() -> dict[str, Any]:
    """Parse all metadata examples.

    Returns:
        Dict: Dictionary with filename as key, file contents as value.

    """
    return _metadata_examples()


@pytest.fixture(scope="function")
def regsurf_nan_only() -> xtgeo.RegularSurface:
    """Create an xtgeo surface with only NaNs."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.RegularSurface(ncol=12, nrow=10, xinc=20, yinc=20, values=np.nan)


@pytest.fixture(scope="function")
def regsurf_masked_only() -> xtgeo.RegularSurface:
    """Create an xtgeo surface with only masked values."""
    logger.debug("Ran %s", _current_function_name())
    regsurf = xtgeo.RegularSurface(ncol=12, nrow=10, xinc=20, yinc=20, values=1000)
    regsurf.values = np.ma.masked_array(regsurf.values, mask=True)
    return regsurf


# ======================================================================================
# Various objects
# ======================================================================================


@pytest.fixture(scope="function")
def regsurf() -> xtgeo.RegularSurface:
    """Create an xtgeo surface."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.RegularSurface(ncol=12, nrow=10, xinc=20, yinc=20, values=1234.0)


@pytest.fixture(scope="function")
def faultroom_object(drogon_global_config: dict[str, Any]) -> FaultRoomSurface:
    """Create a faultroom object."""
    logger.debug("Ran %s", _current_function_name())
    cfg = deepcopy(drogon_global_config)

    horizons = cfg["rms"]["horizons"]["TOP_RES"]
    faults = ["F1", "F2", "F3", "F4", "F5", "F6"]
    juxtaposition_hw = cfg["rms"]["zones"]["ZONE_RES"]
    juxtaposition_fw = cfg["rms"]["zones"]["ZONE_RES"]
    juxtaposition = {"fw": juxtaposition_fw, "hw": juxtaposition_hw}
    properties = [
        "Juxtaposition",
    ]
    coordinates = [[[1.1, 1.2, 1.3], [2.1, 2.2, 2.3]]]
    features = [{"geometry": {"coordinates": coordinates}}]
    name = cfg["access"]["asset"]["name"]

    faultroom_data = {
        "horizons": horizons,
        "faults": {"default": faults},
        "juxtaposition": juxtaposition,
        "properties": properties,
        "name": name,
    }

    return FaultRoomSurface({"metadata": faultroom_data, "features": features})


@pytest.fixture()
def tsurf() -> TSurfData:
    """
    Create a basic TSurfData object from a dictionary.
    """

    tsurf_dict: dict[str, Any] = {}
    tsurf_dict["header"] = {"name": "Fault F1"}
    tsurf_dict["coordinate_system"] = {
        "name": "Default",
        "axis_name": ("X", "Y", "Z"),
        "axis_unit": ("m", "m", "m"),
        "z_positive": "Depth",
    }
    tsurf_dict["vertices"] = np.array(
        [
            (0.1, 0.2, 0.3),
            (1.1, 1.2, 1.3),
            (2.1, 2.2, 2.3),
            (3.1, 3.2, 3.3),
        ]
    ).astype(np.float64)
    tsurf_dict["triangles"] = np.array([(1, 2, 3), (1, 2, 4)]).astype(np.int64)

    return TSurfData.model_validate(tsurf_dict)


@pytest.fixture()
def tsurf_as_lines(tsurf: TSurfData) -> list[str]:
    """
    Create lines to simulate the results of parsing a file with a basic TSurf object.
    """

    vertices_lines = [
        f"VRTX {i + 1} {tsurf.vertices[i][0]} {tsurf.vertices[i][1]} "
        f"{tsurf.vertices[i][2]} CNXYZ"
        for i in range(len(tsurf.vertices))
    ]

    triangles_lines = [
        f"TRGL {tsurf.triangles[i][0]} {tsurf.triangles[i][1]} {tsurf.triangles[i][2]}"
        for i in range(len(tsurf.triangles))
    ]

    assert tsurf.coordinate_system is not None
    return [
        "GOCAD TSurf 1",
        "HEADER {",
        f"name: {tsurf.header.name}",
        "}",
        "GOCAD_ORIGINAL_COORDINATE_SYSTEM",
        f"NAME {tsurf.coordinate_system.name}",
        f'AXIS_NAME "{tsurf.coordinate_system.axis_name[0]}" '
        f'"{tsurf.coordinate_system.axis_name[1]}" '
        f'"{tsurf.coordinate_system.axis_name[2]}"',
        f'AXIS_UNIT "{tsurf.coordinate_system.axis_unit[0]}" '
        f'"{tsurf.coordinate_system.axis_unit[1]}" '
        f'"{tsurf.coordinate_system.axis_unit[2]}"',
        f"ZPOSITIVE {tsurf.coordinate_system.z_positive}",
        "END_ORIGINAL_COORDINATE_SYSTEM",
        "TFACE",
        *vertices_lines,
        *triangles_lines,
        "END",
    ]


@pytest.fixture(scope="function")
def polygons() -> xtgeo.Polygons:
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


@pytest.fixture(scope="function")
def fault_line() -> xtgeo.Polygons:
    """Create an xtgeo polygons."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.Polygons(
        [
            [1, 22, 3, 0, "F1"],
            [6, 25, 4, 0, "F1"],
            [8, 27, 6, 0, "F1"],
            [1, 22, 3, 0, "F1"],
        ],
        attributes={"NAME": "str"},
    )


@pytest.fixture(scope="function")
def points() -> xtgeo.Points:
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


@pytest.fixture(scope="function")
def cube() -> xtgeo.Cube:
    """Create an xtgeo cube instance."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.Cube(ncol=3, nrow=4, nlay=5, xinc=12, yinc=12, zinc=4, rotation=30)


@pytest.fixture(scope="function")
def grid() -> xtgeo.Grid:
    """Create an xtgeo grid instance."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.create_box_grid((3, 4, 5))


@pytest.fixture(scope="function")
def gridproperty() -> xtgeo.GridProperty:
    """Create an xtgeo gridproperty instance."""
    logger.debug("Ran %s", _current_function_name())
    return xtgeo.GridProperty(ncol=3, nrow=7, nlay=3, values=123.0)


@pytest.fixture(scope="function")
def dataframe() -> pd.DataFrame:
    """Create an pandas dataframe instance."""
    logger.debug("Ran %s", _current_function_name())
    return pd.DataFrame({"COL1": [1, 2, 3, 4], "COL2": [99.0, 98.0, 97.0, 96.0]})


@pytest.fixture(scope="function")
def wellpicks() -> pd.DataFrame:
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


@pytest.fixture(scope="function")
def arrowtable() -> pa.Table:
    """Create an arrow table instance."""
    return pa.Table.from_pandas(
        pd.DataFrame(
            {
                "COL1": [1, 2, 3, 4],
                "COL2": [99.0, 98.0, 97.0, 96.0],
            }
        )
    )


@pytest.fixture()
def mock_summary() -> pd.DataFrame:
    """Return summary mock data

    Returns:
        pd.DataFram: dummy data
    """
    return pd.DataFrame({"alf": ["A", "B", "C"], "DATE": [1, 2, 3]})


@pytest.fixture()
def mock_relperm() -> pd.DataFrame:
    """Return relperm mock data"""
    return pd.DataFrame({"alf": ["A", "B", "C"], "SATNUM": [1, 2, 3]})


@pytest.fixture()
def drogon_summary(rootpath: Path) -> pa.Table:
    """Return pyarrow table

    Returns:
        pa.Table: table with summary data
    """
    import pyarrow.feather as feather

    return feather.read_table(rootpath / "tests/data/drogon/tabular/summary.arrow")


@pytest.fixture()
def mock_volumes() -> pd.DataFrame:
    """Return volume mock data

    Returns:
        pd.DataFrame: dummy data
    """
    return pd.DataFrame(
        {
            "ZONE": ["B", "A", "C"],
            "LICENSE": ["L3", "L2", "L1"],
            "FLUID": ["oil", "gas", "water"],
            "REGION": ["N", "S", "E"],
            "nums": [1, 2, 3],
            "OTHER": ["q", "a", "f"],
        }
    )


@pytest.fixture()
def drogon_volumes(rootpath: Path) -> pa.Table:
    """Return pyarrow table

    Returns:
        pa.Table: table with summary data
    """

    return pa.Table.from_pandas(
        pd.read_csv(
            rootpath / "tests/data/drogon/tabular/geogrid--vol.csv",
        )
    )


@pytest.fixture
def unregister_pandas_parquet() -> Generator[None, None, None]:
    """Unregisters pandas extensions in pyarrow.

    Use this fixture if you get errors like:

    pyarrow.lib.ArrowKeyError: A type extension with name pandas.period already defined

    Using `read_parquet()` or `to_parquet` more than once in the same pytest module
    causes errors due to an issue in pandas registering a type extension globally on
    every invocation. This cannot be patched because it's done on the C side.
    This is probably a pandas bug. https://github.com/apache/arrow/issues/41857"""

    # This condition may not be needed, or may not be sufficient
    if sys.modules.get("pandas"):
        try:
            import pyarrow

            try:
                pyarrow.unregister_extension_type("pandas.interval")
                pyarrow.unregister_extension_type("pandas.period")
            except pyarrow.lib.ArrowKeyError:
                # They might already be unregistered
                pass
            yield
        except ImportError:
            pass
