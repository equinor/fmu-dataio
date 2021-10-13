"""Test the polygons_io module."""
import logging
import shutil
from collections import OrderedDict

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

# make a fake Polygons
POLY = [
    (1.0, 2.0, 3.0, 1),
    (1.5, 2.5, 3.5, 1),
    (1.2, 2.2, 3.1, 1),
    (1.1, 2.0, 3.0, 1),
    (1.1, 2.0, 3.0, 2),
    (1.1, 2.0, 3.0, 2),
    (1.1, 2.0, 3.0, 2),
]
CASEPATH = "tests/data/drogon/ertrun1"
FMUP1 = "share/results"


def test_polygons_io(tmp_path):
    """Minimal test polygons io, uses tmp_path."""

    srf = xtgeo.Polygons(POLY)
    fmu.dataio.ExportData.polygons_fformat = "csv"

    exp = fmu.dataio.ExportData(name="test", content="depth", runpath=tmp_path)
    exp.export(srf)

    assert (tmp_path / FMUP1 / "polygons" / ".test.csv.yml").is_file() is True


def test_polygons_io_larger_case_ertrun(tmp_path):
    """Larger test polygons io as ERTRUN, uses global config from Drogon to tmp_path."""

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree(CASEPATH, current / "mycase")

    fmu.dataio.ExportData.polygons_fformat = "irap_ascii"

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = (
        current
        / "mycase"
        / "realization-0"
        / "iter-0"
        / "share"
        / "results"
        / "polygons"
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

    # make a fake Polygons object
    poly = xtgeo.Polygons()
    poly.from_list([(123.0, 345.0, 222.0, 0), (123.0, 345.0, 222.0, 0)])
    print(poly.dataframe)

    exp.export(poly, verbosity="INFO")

    metadataout = out / ".topvolantis--what_descr.pol.yml"
    assert metadataout.is_file() is True
