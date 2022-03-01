"""Test the surface_io module."""
import json
import logging
import shutil
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pytest
import xtgeo
import yaml

import fmu.dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


CFG = OrderedDict()
CFG["model"] = {"name": "Test", "revision": "AUTO"}
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


def test_surface_io(tmp_path):
    """Minimal test surface io, uses tmp_path."""

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=np.ma.ones((20, 30)), name="test"
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(content="depth", runpath=tmp_path, config=CFG)
    exp.export(srf)

    assert (tmp_path / FMUP1 / "maps" / "test.gri").is_file() is True
    assert (tmp_path / FMUP1 / "maps" / ".test.gri.yml").is_file() is True


@pytest.mark.parametrize(
    "dates, expected",
    [
        (
            [[20440109, "monitor"]],
            "test--20440109",
        ),
        (
            [[20440111, "monitor"], None],
            "test--20440111",
        ),
        (
            [[20440101, "monitor"], [20230101, "base"]],
            "test--20440101_20230101",
        ),
        (
            [["20440101", "monitor"], [20230101, "base"]],
            "test--20440101_20230101",
        ),
        (
            [["20440101", "monitor"], ["20230101", "base"]],
            "test--20440101_20230101",
        ),
        (
            [["2044-01-01", "monitor"], ["20230101", "base"]],
            "test--20440101_20230101",
        ),
    ],
)
def test_surface_io_with_timedata(tmp_path, dates, expected):
    """Minimal test surface io with timedata, uses tmp_path."""

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=np.ma.ones((20, 30)), name="test"
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(
        content="depth", timedata=dates, runpath=tmp_path, config=CFG
    )
    out = Path(exp.export(srf)).stem

    assert expected == out


@pytest.mark.parametrize(
    "dates, errmessage",
    [
        (
            [[40440101, "monitor"], [20230101, "base"]],
            "Integer date input seems to be outside reasonable limits",
        ),
        (
            [[20210101, "monitor"], [17220101, "base"]],
            "Integer date input seems to be outside reasonable limits",
        ),
        (
            [["20210101", "monitor"], ["17220101", "base"]],
            "Date input outside reasonable limits",
        ),
        (
            [["2021-01-01", "monitor"], ["1722-01-01", "base"]],
            "Date input outside reasonable limits",
        ),
        (
            [["666", "monitor"], ["1722-01-01", "base"]],
            "Date input outside reasonable limits",
        ),
    ],
)
def test_surface_io_with_timedata_shall_fail(tmp_path, dates, errmessage):
    """Minimal test surface io with timedata, uses tmp_path, with invalid input."""

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=np.ma.ones((20, 30)), name="test"
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(
        content="depth", timedata=dates, runpath=tmp_path, config=CFG
    )
    with pytest.raises(ValueError) as err:
        exp.export(srf)
    assert errmessage in str(err.value)


def test_surface_io_export_subfolder(tmp_path):
    """Minimal test surface io with export_subfolder set, uses tmp_path."""

    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=np.ma.ones((20, 30)), name="test"
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(content="depth", runpath=tmp_path, config=CFG)
    with pytest.warns(UserWarning):
        exp.export(srf, subfolder="mysubfolder")

    assert (tmp_path / FMUP1 / "maps" / "mysubfolder" / "test.gri").is_file() is True
    assert (
        tmp_path / FMUP1 / "maps" / "mysubfolder" / ".test.gri.yml"
    ).is_file() is True


def test_surface_io_export_subfolder_w_path_warn(tmp_path):
    """Minimal test surface io with sufolder, using illegal path."""

    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=np.ma.ones((20, 30)), name="test"
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(content="depth", runpath=tmp_path, config=CFG)
    # with pytest.warns(UserWarning):
    exp.export(srf, subfolder="../mysubfolder")


def test_surface_io_export_forcefolder_absolute(tmp_path):
    """Minimal test surface io with forcefolder set, uses tmp_path."""

    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=np.ma.ones((20, 30)), name="test234"
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(content="depth", runpath=tmp_path, config=CFG)
    with pytest.warns(UserWarning):
        exp.export(srf, forcefolder=str(tmp_path))

    assert (tmp_path / "test234.gri").is_file() is True


def test_surface_io_export_forcefolder_relative(tmp_path):
    """Minimal test surface io with forcefolder set as relative to runpath"""

    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=np.ma.ones((20, 30)), name="test235"
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(content="depth", runpath=tmp_path, config=CFG)
    with pytest.warns(UserWarning):
        exp.export(srf, forcefolder="share/results/myfolder")

    assert (tmp_path / "share/results/myfolder" / "test235.gri").is_file() is True


def test_surface_io_export_forcefolder_illegal_folder_create(tmp_path):
    """Test with forcefolder set as absolute to a path with only admin rights."""

    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=np.ma.ones((20, 30)), name="test235"
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(
        content="depth", runpath=tmp_path, config=CFG, verbosity="INFO"
    )

    # try to make a folder under /usr/bin which is illegal unless root rights
    with pytest.raises(PermissionError):
        exp.export(srf, forcefolder="/usr/bin/whatever")


def test_surface_io_export_forcefolder_illegal_folder_store(tmp_path):
    """Test with forcefolder store in folder with admin rights."""

    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, xinc=20, yinc=20, values=np.ma.ones((20, 30)), name="test235"
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(
        content="depth", runpath=tmp_path, config=CFG, verbosity="INFO"
    )

    # legal path, but still not allowed to write a file, which returns different
    # exceptions dependent if xtgeo or Pandas, or ...
    with pytest.raises((IOError, Exception)):
        exp.export(srf, forcefolder="/usr/bin")


def test_surface_io_larger_case(tmp_path):
    """Larger test surface io, uses global config from Drogon to tmp_path."""

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20,
        nrow=30,
        xinc=20,
        yinc=20,
        values=np.ma.ones((20, 30)),
        name="TopVolantis",
    )
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
        runpath=tmp_path,
    )
    exp.export(srf, verbosity="DEBUG")

    metadataout = tmp_path / FMUP1 / "maps" / ".topvolantis--what_descr.gri.yml"
    assert metadataout.is_file() is True
    print(metadataout)


def test_surface_io_larger_case_ertrun(tmp_path):
    """Larger test surface io as ERTRUN, uses global config from Drogon to tmp_path.

    Need some file acrobatics here to make the tmp_path area look like an ERTRUN first.
    """

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree(CASEPATH, current / "mycase")

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
        inside_rms=True,
    )

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20,
        nrow=30,
        xinc=20,
        yinc=20,
        values=np.ma.ones((20, 30)),
        name="TopVolantis",
    )
    exp.export(srf, verbosity="INFO")

    metadataout = out / ".topvolantis--what_descr.gri.yml"
    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as stream:
        meta = yaml.safe_load(stream)

    assert (
        meta["file"]["relative_path"]
        == "realization-0/iter-0/share/results/maps/topvolantis--what_descr.gri"
    )
    assert meta["class"] == "surface", meta["class"]
    assert meta["fmu"]["model"]["name"] == "ff"
    assert meta["fmu"]["iteration"]["name"] == "iter-0"
    assert meta["fmu"]["realization"]["name"] == "realization-0"
    assert meta["data"]["stratigraphic"] is True

    # display_name is not set, checking that 'name' was used
    assert meta["display"]["name"] == "TopVolantis"

    logger.debug("\n%s", json.dumps(meta, indent=2))


def test_surface_io_larger_case_ertrun_missing_casemetadata(tmp_path):
    """As above but case metadata will be missing, and this shall issue a warning."""

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)

    shutil.copytree(CASEPATH, current / "mycase")
    shutil.rmtree(current / "mycase" / "share" / "metadata")

    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = current / "mycase" / "realization-0" / "iter-0" / "share" / "results" / "maps"

    with pytest.warns(FutureWarning, match="Cannot find the case metadata"):
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
            inside_rms=True,
        )

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20,
        nrow=30,
        xinc=20,
        yinc=20,
        values=np.ma.ones((20, 30)),
        name="TopVolantis",
    )

    exp.export(srf, verbosity="INFO")

    metadataout = out / ".topvolantis--what_descr.gri.yml"
    assert metadataout.is_file() is True

    # now read the metadata file and test some key entries:
    with open(metadataout, "r") as astream:
        meta = yaml.safe_load(astream)

    assert (
        meta["file"]["relative_path"]
        == "realization-0/iter-0/share/results/maps/topvolantis--what_descr.gri"
    )
    assert meta["class"] == "surface", meta["class"]
    assert meta["fmu"]["case"]["name"] == "MISSING!"
    assert meta["fmu"]["model"]["name"] == "ff"
