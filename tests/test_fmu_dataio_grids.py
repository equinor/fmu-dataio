"""Test the grid and grid property outputs."""
import json
import logging
import shutil
from collections import OrderedDict

import pytest
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
CFG["access"] = {
    "asset": "Drogon",
    "ssdl": {"access_level": "internal", "some_access_tag": True},
}
CFG["model"] = {"revision": "0.99.0"}

CFG2 = {}
with open("tests/data/drogon/global_config2/global_variables.yml", "r") as stream:
    CFG2 = yaml.safe_load(stream)

RUN = "tests/data/drogon/ertrun1/realization-0/iter-0/rms"
CASEPATH = "tests/data/drogon/ertrun1"

FMUP1 = "share/results"


def test_grid_io(tmp_path):
    """Minimal test grid geometry io, uses tmp_path."""

    grd = xtgeo.create_box_grid(dimension=(2, 3, 4))
    grd.name = "test"
    fmu.dataio.ExportData.grid_fformat = "roff"

    exp = fmu.dataio.ExportData(
        content="depth",
        runpath=tmp_path,
        config=CFG,
    )
    exp.export(grd)

    assert (tmp_path / FMUP1 / "grids" / ".test.roff.yml").is_file() is True


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_gridproperty_io(tmp_path):
    """Minimal test gridproperty io, uses tmp_path."""

    gpr = xtgeo.GridProperty(ncol=10, nrow=11, nlay=12)
    gpr.name = "testgp"
    fmu.dataio.ExportData.grid_fformat = "roff"

    exp = fmu.dataio.ExportData(
        parent={"name": "Geogrid"}, runpath=tmp_path, config=CFG
    )
    exp.export(gpr)

    assert (tmp_path / FMUP1 / "grids" / ".geogrid--testgp.roff.yml").is_file() is True


def test_grid_io_larger_case(tmp_path):
    """Larger test grid io, uses global config from Drogon to tmp_path."""

    # make a fake Grid
    grd = xtgeo.create_box_grid(dimension=(2, 3, 4))
    grd.name = "Volantis"

    fmu.dataio.ExportData.grid_fformat = "roff"

    exp = fmu.dataio.ExportData(
        config=CFG2,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        verbosity="INFO",
        runpath=tmp_path,
    )

    exp.export(grd, verbosity="DEBUG")

    metadataout = tmp_path / FMUP1 / "grids" / ".volantis--what_descr.roff.yml"
    assert metadataout.is_file() is True
    print(metadataout)


def test_gridprop_io_larger_case(tmp_path):
    """Larger test gridprop io, uses global config from Drogon to tmp_path."""

    # make a fake GridProp
    grdp = xtgeo.GridProperty(ncol=2, nrow=7, nlay=13)
    grdp.name = "poro"

    fmu.dataio.ExportData.grid_fformat = "roff"

    exp = fmu.dataio.ExportData(
        config=CFG2,
        content={"property": {"attribute": "porosity"}},
        unit="fraction",
        vertical_domain={"depth": "msl"},
        parent={"name": "Geogrid"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="porotag",
        verbosity="INFO",
        runpath=tmp_path,
    )
    exp.export(grdp, verbosity="DEBUG")

    metadataout = tmp_path / FMUP1 / "grids" / ".geogrid--poro--porotag.roff.yml"
    assert metadataout.is_file() is True
    print(metadataout)


def test_grid_io_larger_case_ertrun(tmp_path):
    """Larger test grid io as ERTRUN, uses global config from Drogon to tmp_path.

    Need some file acrobatics here to make the tmp_path area look like an ERTRUN first,
    and in this case we pretend to be in RMS python.
    """

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree(CASEPATH, current / "mycase")

    fmu.dataio.ExportData.surface_fformat = "roff"

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = (
        current / "mycase" / "realization-0" / "iter-0" / "share" / "results" / "grids"
    )
    exp = fmu.dataio.ExportData(
        config=CFG2,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        verbosity="INFO",
        runfolder=runfolder,
        inside_rms=True,
        workflow="my current workflow",
    )

    grd = xtgeo.create_box_grid(
        dimension=(10, 12, 6),
        origin=(10.0, 20.0, 1000.0),
        oricenter=False,
        increment=(100, 150, 5),
        rotation=30.0,
        flip=1,
    )
    grd.name = "Volantis"

    exp.export(grd, verbosity="INFO")

    metadataout = out / ".volantis--what_descr.roff.yml"
    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as stream2:
        meta = yaml.safe_load(stream2)

    assert (
        meta["file"]["relative_path"]
        == "realization-0/iter-0/share/results/grids/volantis--what_descr.roff"
    )
    assert meta["fmu"]["model"]["name"] == "ff"
    assert meta["fmu"]["iteration"]["name"] == "iter-0"
    assert meta["fmu"]["realization"]["name"] == "realization-0"
    assert meta["data"]["stratigraphic"] is False
    assert meta["data"]["bbox"]["xmin"] == -890.0

    logger.info("\n%s", json.dumps(meta, indent=2))


def test_gridprop_io_larger_case_ertrun(tmp_path):
    """Larger test grid io as ERTRUN, uses global config from Drogon to tmp_path."""

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree(CASEPATH, current / "mycase")

    fmu.dataio.ExportData.surface_fformat = "roff"

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = (
        current / "mycase" / "realization-0" / "iter-0" / "share" / "results" / "grids"
    )

    exp = fmu.dataio.ExportData(
        config=CFG2,
        content={"property": {"attribute": "porosity"}},
        unit="fraction",
        vertical_domain={"depth": "msl"},
        parent={"name": "Geogrid"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="porosity",
        verbosity="INFO",
        runfolder=runfolder.resolve(),
        inside_rms=True,
        workflow="my current workflow",
    )

    grdp = xtgeo.GridProperty(ncol=2, nrow=7, nlay=13, name="Volantis")

    exp.export(grdp, verbosity="INFO")

    metadataout = out / ".geogrid--volantis--porosity.roff.yml"
    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as stream3:
        meta = yaml.safe_load(stream3)

    assert (
        meta["file"]["relative_path"]
        == "realization-0/iter-0/share/results/grids/geogrid--volantis--porosity.roff"
    )
    assert meta["fmu"]["model"]["name"] == "ff"
    assert meta["fmu"]["iteration"]["name"] == "iter-0"
    assert meta["fmu"]["realization"]["name"] == "realization-0"
    assert meta["data"]["stratigraphic"] is False
    assert meta["data"]["spec"]["nlay"] == 13

    logger.info("\n%s", json.dumps(meta, indent=2))
