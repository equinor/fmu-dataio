"""Test the surface_io module."""
from collections import OrderedDict
import shutil
import logging
import json
import numpy as np
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


def test_surface_io(tmp_path):
    """Minimal test surface io, uses tmp_path."""

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, values=np.ma.ones((20, 30)), name="test"
    )
    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData()
    exp._pwd = tmp_path
    exp.to_file(srf)

    assert (tmp_path / "maps" / ".test.yml").is_file() is True


def test_surface_io_larger_case(tmp_path):
    """Larger test surface io, uses global config from Drogon to tmp_path."""

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, values=np.ma.ones((20, 30)), name="TopVolantis"
    )
    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

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
    )
    exp._pwd = tmp_path
    exp.to_file(srf, verbosity="DEBUG")

    metadataout = tmp_path / "maps" / ".topvolantis--what_descr.yml"
    assert metadataout.is_file() is True
    print(metadataout)


def test_surface_io_larger_case_ertrun(tmp_path):
    """Larger test surface io as ERTRUN, uses global config from Drogon to tmp_path.

    Need some file acrobatics here to make the tmp_path area look like an ERTRUN first.
    """

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree(CASEPATH, current / "mycase")

    fmu.dataio.ExportData.export_root = "../../share/results"
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = current / "mycase" / "realization-0" / "iter-0" / "share" / "results" / "maps"

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
        runfolder=runfolder.resolve(),
        workflow="my current workflow",
    )

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, values=np.ma.ones((20, 30)), name="TopVolantis"
    )
    exp.to_file(srf, verbosity="INFO")

    metadataout = out / ".topvolantis--what_descr.yml"
    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as stream:
        meta = yaml.safe_load(stream)

    assert (
        meta["file"]["relative_path"]
        == "realization-0/iter-0/share/results/maps/topvolantis--what_descr.gri"
    )
    assert meta["fmu"]["model"]["name"] == "ff"
    assert meta["fmu"]["iteration"]["name"] == "iter-0"
    assert meta["fmu"]["realization"]["name"] == "realization-0"
    assert meta["data"]["stratigraphic"] is True

    logger.debug("\n%s", json.dumps(meta, indent=2))
