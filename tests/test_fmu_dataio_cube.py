"""Test dataio for cube (most often seismic cube)."""
import json
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
CASEPATH = "tests/data/drogon/ertrun1"
FMU1SHARE = "share/results"


def test_cube_io(tmp_path):
    """Minimal test cube geometry io, uses tmp_path."""

    cube = xtgeo.Cube(ncol=5, nrow=8, nlay=3, values=0.0)
    fmu.dataio.ExportData.cube_fformat = "segy"

    exp = fmu.dataio.ExportData(content="depth", name="testcube", runpath=tmp_path)

    exp.export(cube)

    assert (tmp_path / FMU1SHARE / "cubes" / ".testcube.segy.yml").is_file() is True


def test_cube_io_larger_case(tmp_path):
    """Larger test cube io, uses global config from Drogon to tmp_path."""

    # make a fake cube
    cube = xtgeo.Cube(ncol=33, nrow=44, nlay=22, values=0.0)

    exp = fmu.dataio.ExportData(
        config=CFG2,
        content="time",
        name="Volantis",
        unit="m",
        vertical_domain={"time": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        verbosity="INFO",
        runpath=tmp_path,
    )
    exp.export(cube, verbosity="DEBUG")

    metadataout = tmp_path / FMU1SHARE / "cubes" / ".volantis--what_descr.segy.yml"
    assert metadataout.is_file() is True
    print(metadataout)


def test_cubeprop_io_larger_case(tmp_path):
    """Larger test cube io, uses global config from Drogon to tmp_path."""

    # make a fake cubeProp
    cubep = xtgeo.Cube(ncol=2, nrow=7, nlay=13)

    fmu.dataio.ExportData.cube_fformat = "segy"

    exp = fmu.dataio.ExportData(
        name="poro",
        config=CFG2,
        content={"property": {"attribute": "porosity"}},
        unit="fraction",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="porotag",
        verbosity="INFO",
        runpath=tmp_path,
    )
    exp.export(cubep, verbosity="DEBUG")

    metadataout = tmp_path / FMU1SHARE / "cubes" / ".poro--porotag.segy.yml"
    assert metadataout.is_file() is True
    print(metadataout)


def test_cube_io_larger_case_ertrun(tmp_path):
    """Larger test cube io as ERTRUN, uses global config from Drogon to tmp_path.

    Need some file acrobatics here to make the tmp_path area look like an ERTRUN first.
    """

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree(CASEPATH, current / "mycase")

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = (
        current / "mycase" / "realization-0" / "iter-0" / "share" / "results" / "cubes"
    )

    # alternative 1, set inside_rms True (developer setting for testing)
    exp1 = fmu.dataio.ExportData(
        config=CFG2,
        name="Volantis",
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

    cube = xtgeo.Cube(ncol=23, nrow=12, nlay=5)
    exp1.export(cube, verbosity="INFO")

    metadataout = out / ".volantis--what_descr.segy.yml"

    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r", encoding="utf8") as mstream:
        meta = yaml.safe_load(mstream)
    assert (
        meta["file"]["relative_path"]
        == "realization-0/iter-0/share/results/cubes/volantis--what_descr.segy"
    )
    assert meta["fmu"]["model"]["name"] == "ff"
    assert meta["fmu"]["iteration"]["name"] == "iter-0"
    assert meta["fmu"]["realization"]["name"] == "realization-0"
    assert meta["data"]["stratigraphic"] is False
    assert meta["data"]["bbox"]["xmin"] == 0.0
    assert meta["data"]["bbox"]["xmax"] == 550.0

    logger.info("\n%s", json.dumps(meta, indent=2))
