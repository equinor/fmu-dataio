"""Test the points_io module."""
import logging
import shutil
from collections import OrderedDict

import pandas as pd
import xtgeo
import yaml

import fmu.dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


CFG = OrderedDict()
CFG["template"] = {"name": "Test", "revision": "AUTO"}
CFG["masterdata"] = {
    "smda": {
        "country": [
            {"identifier": "Norway", "uuid": "ad214d85-8a1d-19da-e053-c918a4889309"}
        ],
        "discovery": [{"short_identifier": "abdcef", "uuid": "ghijk"}],
    }
}

CFG2 = {}
with open("tests/data/drogon/global_config2/global_variables.yml", "r") as stream:
    CFG2 = yaml.safe_load(stream)

RUN = "tests/data/drogon/ertrun1/realization-0/iter-0/rms"

# make a fake points
POI = [
    (1.0, 2.0, 3.0),
    (1.5, 2.5, 3.5),
    (1.2, 2.2, 3.1),
    (1.1, 2.0, 3.0),
    (1.1, 2.0, 3.0),
    (1.1, 2.0, 3.0),
    (1.1, 2.0, 3.0),
]

# points with extra columns (attributes)
POI2 = {
    "X": [1.0, 2.0],
    "Y": [1.1, 2.1],
    "Z": [1.2, 2.2],
    "A1": [1.0, 2.0],
    "A2": ["x1", "x2"],
}

CASEPATH = "tests/data/drogon/ertrun1"
FMUP1 = "share/results"


def test_points_io(tmp_path):
    """Minimal test points io, uses tmp_path."""

    pox = xtgeo.Points(POI)
    fmu.dataio.ExportData.points_fformat = "csv"

    exp = fmu.dataio.ExportData(name="test", content="depth", runpath=tmp_path)
    exp.export(pox)

    assert (tmp_path / FMUP1 / "points" / ".test.csv.yml").is_file() is True


def test_points_io_with_attrs(tmp_path):
    """Minimal test points io with attributes, uses tmp_path."""

    pox = xtgeo.Points()
    dfr = pd.DataFrame(POI2)
    print(dfr)
    pox.from_dataframe(
        dfr,
        east="X",
        north="Y",
        tvdmsl="Z",
        attributes={"A1": "A1", "A2": "A2"},
    )
    print(pox.dataframe)
    fmu.dataio.ExportData.points_fformat = "csv"
    exp = fmu.dataio.ExportData(name="test2", content="depth", runpath=tmp_path)
    exp.export(pox)

    assert (tmp_path / FMUP1 / "points" / ".test2.csv.yml").is_file() is True
    dfr2 = pd.read_csv(tmp_path / FMUP1 / "points" / "test2.csv")
    assert dfr2["A2"][0] == "x1"


def test_points_io_larger_case_ertrun(tmp_path):
    """Larger test points io as ERTRUN, uses global config from Drogon to tmp_path."""

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree(CASEPATH, current / "mycase")

    fmu.dataio.ExportData.points_fformat = "irap_ascii"

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = (
        current / "mycase" / "realization-0" / "iter-0" / "share" / "results" / "points"
    )

    exp = fmu.dataio.ExportData(
        name="TopVolantis",
        config=CFG2,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        verbosity="INFO",
        runfolder=runfolder.resolve(),
        inside_rms=True,
        workflow="my current workflow",
    )

    # make a fake points object
    poi = xtgeo.Points()
    poi.from_list([(123.0, 345.0, 222.0), (123.0, 345.0, 222.0)])
    print(poi.dataframe)

    exp.export(poi, verbosity="INFO")

    metadataout = out / ".topvolantis--what_descr.poi.yml"
    assert metadataout.is_file() is True
